#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据评分修复脚本

修复范围（1539 条历史记录）：
  source_score    ← sources.yaml tier 配置，程序化计算，无 LLM
  heat_score      ← 领域+信源启发式估分（历史热榜数据不可追溯）
  influence_score ← 批量 LLM 评估，FILTER tier，15 条/批
  value_score     ← 与 influence 同批输出
  final_score     ← 公式计算 = (source×25% + influence×25% + heat×25% + value×25%) × 10
  tags            ← 从 who/what/domain 规则合并，无 LLM
  domain (B类)    ← 16 条缺失记录，LLM 分类补全

用法：
  python scripts/database/repair_scores.py [--dry-run] [--batch-size 15] [--only source|heat|tags|llm|domain|final]

--dry-run    仅打印统计，不写入数据库
--only X     只修复指定步骤（调试用）
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 确保项目根目录在 sys.path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("repair_scores")

# ─── 常量 ────────────────────────────────────────────────────────────────────

# 从 core_config.yaml 统一读取 Tier 分值
from core.utils.source_scorer import get_scoring_config as _get_scoring_cfg
_scoring_cfg = _get_scoring_cfg()
_tier_scores = _scoring_cfg.get('tier_scores', {1: 9.5, 2: 7.5, 3: 5.5})
_default_score = _scoring_cfg.get('default_source_score', 5.0)

TIER_TO_SOURCE_SCORE: Dict[Optional[int], float] = {
    1: _tier_scores.get(1, 9.5),
    2: _tier_scores.get(2, 7.5),
    3: _tier_scores.get(3, 5.5),
    None: _default_score,
}

# 历史 heat_score 启发式基准（无法追溯历史热榜）
DOMAIN_HEAT_BASE: Dict[str, float] = {
    '政治':   5.0,
    '经济':   4.5,
    '科技':   4.0,
    '社会':   4.0,
    '娱乐':   5.0,
    '体育':   4.5,
    '环境':   3.0,
    '文化':   3.0,
    '健康':   3.5,
    '其他':   3.0,
}
TIER_HEAT_BONUS: Dict[Optional[int], float] = {1: 1.5, 2: 0.8, 3: 0.2, None: 0.0}

# 最大 heat_score 上限（为实时热榜检测留空间）
HEAT_HISTORICAL_CAP = 7.5

# LLM 批次大小
DEFAULT_BATCH_SIZE = 15


# ─── sources.yaml 信源→tier 映射 ────────────────────────────────────────────

def build_source_lookup() -> Dict[str, Optional[int]]:
    """从 sources.yaml 构建 source_name → tier 映射（精确匹配 + 子串匹配）。"""
    yaml_path = ROOT / 'sources.yaml'
    if not yaml_path.exists():
        logger.warning("sources.yaml 不存在，source_score 将使用默认值 5")
        return {}

    with open(yaml_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)

    lookup: Dict[str, Optional[int]] = {}

    def walk(node):
        if isinstance(node, list):
            for item in node:
                if isinstance(item, dict) and 'name' in item:
                    lookup[item['name']] = item.get('tier')
                walk(item)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(data)
    logger.info(f"sources.yaml 加载完成，共 {len(lookup)} 个信源")
    return lookup


def get_source_score(source_name: str, lookup: Dict[str, Optional[int]]) -> float:
    """精确匹配优先，然后子串匹配，最后默认 5 分。"""
    if not source_name:
        return TIER_TO_SOURCE_SCORE[None]
    # 精确匹配
    if source_name in lookup:
        return TIER_TO_SOURCE_SCORE.get(lookup[source_name], 5.0)
    # 子串匹配（处理 "CNBC International" 等变体）
    for name, tier in lookup.items():
        if name in source_name or source_name in name:
            return TIER_TO_SOURCE_SCORE.get(tier, 5.0)
    return TIER_TO_SOURCE_SCORE[None]


# ─── heat_score 历史启发式 ────────────────────────────────────────────────────

def get_historical_heat_score(domain: str, source_score: float) -> float:
    """
    历史 heat_score 启发式估算。
    无法追溯历史热榜，基于领域基准 + 信源权威性调整。
    """
    base = DOMAIN_HEAT_BASE.get(domain, 3.0)
    # 从 source_score 反推 tier bonus
    if source_score >= 10.0:
        bonus = TIER_HEAT_BONUS[1]
    elif source_score >= 8.0:
        bonus = TIER_HEAT_BONUS[2]
    elif source_score >= 6.0:
        bonus = TIER_HEAT_BONUS[3]
    else:
        bonus = TIER_HEAT_BONUS[None]
    return round(min(base + bonus, HEAT_HISTORICAL_CAP), 1)


# ─── tags 规则生成 ────────────────────────────────────────────────────────────

def generate_tags(domain: str, who: str, what: str, existing_tags: str) -> str:
    """
    从已有字段合并生成 tags（JSON 字符串格式，与 DB 存储一致）。
    优先保留已有 tags，补充 domain + who + what 中的关键词。
    """
    tag_set: List[str] = []

    # 1. 已有 tags（JSON 数组或逗号分隔字符串）
    if existing_tags:
        try:
            existing = json.loads(existing_tags)
            if isinstance(existing, list):
                tag_set.extend([str(t).strip() for t in existing if t])
        except (json.JSONDecodeError, TypeError):
            tag_set.extend([t.strip() for t in existing_tags.split(',') if t.strip()])

    # 2. domain
    if domain and domain not in tag_set and len(domain) <= 8:
        tag_set.append(domain)

    # 3. who（取第一个实体，去掉标点）
    if who:
        for w in re.split(r'[,，、；;]', who)[:2]:
            w = w.strip()
            if w and 2 <= len(w) <= 15 and w not in tag_set:
                tag_set.append(w)

    # 4. what（取前 10 字的名词短语）
    if what:
        snippet = what.strip()[:20]
        if snippet and snippet not in tag_set:
            tag_set.append(snippet)

    # 去重、限制 6 个
    seen: set = set()
    deduped: List[str] = []
    for t in tag_set:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    return json.dumps(deduped[:6], ensure_ascii=False)


# ─── 规则打分（influence + value，无 LLM）────────────────────────────────────

# 领域 → 初始影响力基准（0-10）
_DOMAIN_INFLUENCE_BASE: Dict[str, float] = {
    '政治': 7.0, '经济': 6.5, '科技': 6.0, '社会': 5.5,
    '健康': 5.5, '环境': 5.0, '文化': 4.5, '体育': 4.5,
    '娱乐': 4.0, '其他': 5.0,
}

# 领域 → 初始投资价值基准（0-10）
_DOMAIN_VALUE_BASE: Dict[str, float] = {
    '经济': 7.5, '科技': 7.0, '政治': 6.5, '社会': 5.0,
    '健康': 5.5, '环境': 5.0, '文化': 4.0, '体育': 3.5,
    '娱乐': 3.0, '其他': 4.5,
}

# 高影响力词：出现在标题→+1
_HIGH_INFLUENCE_KEYWORDS = (
    '战争', '制裁', '危机', '崩盘', 'GDP', '降息', '加息', '违约', '破产',
    '核', '军', '冲突', '峰会', '条约', '协议', '联合国', 'G7', 'G20',
    'IPO', '并购', '重组', '上市', '退市', '造假', '调查', '逮捕', '起诉',
    '突破', '发布', 'AI', '芯片', '量子', '大模型',
)

# 高价值词：对投资决策有意义→+1
_HIGH_VALUE_KEYWORDS = (
    '利率', '通胀', '汇率', '贸易', '关税', '供应链', '半导体', '能源',
    '石油', '天然气', '黄金', '比特币', '股市', '债券', '基金', 'ETF',
    '业绩', '营收', '利润', '分红', '回购', '融资', '投资', '并购', '破产',
    '政策', '监管', '补贴', '税', '出口', '进口',
)


def rule_score_influence_value(row: Dict) -> tuple:
    """
    基于规则的 influence_score + value_score 估算（替代 LLM，0-10）。
    利用 domain / source_score / translated_title / who / what 字段。
    """
    domain = row.get('domain', '') or ''
    src_score = row.get('source_score') or 5.0
    title = (row.get('translated_title') or row.get('title') or '').lower()
    content_snippet = (
        (row.get('who') or '') + ' ' +
        (row.get('what') or '') + ' ' +
        (row.get('tags') or '')
    )
    text = title + ' ' + content_snippet

    # 影响力：领域基准 + 信源加成 + 关键词
    inf_base = _DOMAIN_INFLUENCE_BASE.get(domain, 5.0)
    src_bonus = (src_score - 5.0) * 0.3   # src=10→+1.5, src=5→0, src=6→+0.3
    kw_bonus = sum(1 for kw in _HIGH_INFLUENCE_KEYWORDS if kw in text)
    kw_bonus = min(kw_bonus, 2)            # 关键词最多加 2 分
    influence = round(min(10.0, max(1.0, inf_base + src_bonus + kw_bonus)), 1)

    # 投资价值：领域基准 + 信源加成 + 关键词
    val_base = _DOMAIN_VALUE_BASE.get(domain, 4.5)
    val_kw_bonus = sum(1 for kw in _HIGH_VALUE_KEYWORDS if kw in text)
    val_kw_bonus = min(val_kw_bonus, 2)
    value = round(min(10.0, max(1.0, val_base + src_bonus + val_kw_bonus)), 1)

    return influence, value


# ─── LLM 批量评分 ─────────────────────────────────────────────────────────────

_SCORE_SYSTEM = (
    "你是新闻评分专家，对新闻事件进行结构化打分。"
    "严格按照用户要求的 JSON 格式输出，不输出任何 JSON 以外的内容。"
)

_SCORE_RULES = """评分标准：
influence_score（事件影响力 0-10）：
  9-10：全球性重大事件（战争/重大外交/全球经济危机/颠覆性技术）
  7-8：国家级重大政策/重要人事/大型企业重大事件
  5-6：行业级重要事件/区域性政策
  3-4：地方性/小规模商业/企业日常
  1-2：微小影响/例行公告

value_score（信息价值 0-10）：
  9-10：独家首发/重磅数据/高信息密度
  7-8：有明确数据支撑/多维度信息完整
  5-6：一般报道/信息基本完整
  3-4：信息较少/跟进报道/重复性
  1-2：低密度/纯公告/无实质内容"""


def build_batch_prompt(batch: List[Dict]) -> str:
    items = []
    for i, row in enumerate(batch, 1):
        domain  = row.get('domain', '未知')
        source  = row.get('source_name', '未知')
        title   = row.get('translated_title') or row.get('title', '')
        who     = (row.get('who') or '')[:30]
        what    = (row.get('what') or '')[:40]
        items.append(f"{i}|{domain}|{source}|{title[:60]}|{who}/{what}")

    items_text = "\n".join(items)
    return (
        f"{_SCORE_RULES}\n\n"
        f"新闻列表（格式：序号|领域|信源|标题|关键人物/事件）：\n{items_text}\n\n"
        f"请输出 JSON 数组（仅数组，无其他内容）：\n"
        f'[{{"id":1,"influence":X,"value":Y}},{{"id":2,"influence":X,"value":Y}},...]'
    )


def parse_llm_score_response(response: str, batch_size: int) -> List[Tuple[float, float]]:
    """
    解析 LLM 返回的 JSON 数组。
    返回 [(influence, value), ...] 与 batch 顺序对应；解析失败则用默认值 (5.0, 5.0)。
    """
    default = [(5.0, 5.0)] * batch_size
    m = re.search(r'\[[\s\S]*\]', response)
    if not m:
        return default
    try:
        arr = json.loads(m.group(0))
        result = [(5.0, 5.0)] * batch_size
        for item in arr:
            idx = int(item.get('id', 0)) - 1
            if 0 <= idx < batch_size:
                inf = max(0.0, min(10.0, float(item.get('influence', 5))))
                val = max(0.0, min(10.0, float(item.get('value', 5))))
                result[idx] = (inf, val)
        return result
    except Exception:
        return default


def llm_score_batch(
    provider,
    batch: List[Dict],
) -> List[Tuple[float, float]]:
    """对一批新闻调用 LLM，返回 (influence, value) 对列表。"""
    prompt = build_batch_prompt(batch)
    try:
        response = provider.chat(
            [
                {"role": "system", "content": _SCORE_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=len(batch) * 30 + 50,
        )
        return parse_llm_score_response(response, len(batch))
    except Exception as e:
        logger.warning(f"LLM 批次评分失败（使用默认值）: {e}")
        return [(5.0, 5.0)] * len(batch)


# ─── domain 补全（B类：16条缺失） ────────────────────────────────────────────

_DOMAIN_CLASSIFY_SYSTEM = (
    "你是新闻分类专家。根据标题和来源，将新闻归类到：政治/经济/科技/社会/娱乐/体育/环境/文化/健康/其他。"
    "严格按 JSON 输出，不输出任何其他内容。"
)

_DOMAIN_OPTIONS = ['政治', '经济', '科技', '社会', '娱乐', '体育', '环境', '文化', '健康', '其他']


def classify_domains(provider, rows: List[Dict]) -> List[str]:
    """批量给无 domain 的记录分类。"""
    if not rows:
        return []
    items = []
    for i, r in enumerate(rows, 1):
        title = (r.get('translated_title') or r.get('title', ''))[:60]
        source = r.get('source_name', '')
        items.append(f"{i}. [{source}] {title}")

    prompt = (
        f"请对以下新闻进行领域分类（选项：{'、'.join(_DOMAIN_OPTIONS)}）：\n\n"
        + "\n".join(items)
        + f'\n\n输出 JSON 数组：[{{"id":1,"domain":"科技"}},{{"id":2,"domain":"经济"}},...]\n（仅数组，无其他内容）'
    )
    try:
        resp = provider.chat(
            [
                {"role": "system", "content": _DOMAIN_CLASSIFY_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=len(rows) * 15 + 30,
        )
        m = re.search(r'\[[\s\S]*\]', resp)
        arr = json.loads(m.group(0)) if m else []
        result = ['其他'] * len(rows)
        for item in arr:
            idx = int(item.get('id', 0)) - 1
            d = item.get('domain', '其他')
            if 0 <= idx < len(rows) and d in _DOMAIN_OPTIONS:
                result[idx] = d
        return result
    except Exception as e:
        logger.warning(f"domain 分类失败（默认'其他'）: {e}")
        return ['其他'] * len(rows)


# ─── final_score 计算 ─────────────────────────────────────────────────────────

def compute_final_score(
    source_score: float,
    influence_score: float,
    heat_score: float,
    value_score: float,
    compliance_deduction: float = 0.0,
) -> float:
    """使用统一评分函数，兼容 repair 脚本的 compliance_deduction"""
    from core.utils.source_scorer import calc_final_score
    base = calc_final_score(source_score, influence_score, value_score, heat_score)
    return round(max(0.0, min(100.0, base - compliance_deduction)), 1)


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def run_repair(args):
    from core.storage.database import NewsDatabase
    db_path = ROOT / "data" / "news.db"
    db = NewsDatabase(db_path=str(db_path))

    only = args.only
    dry_run = args.dry_run
    batch_size = args.batch_size

    if dry_run:
        logger.info("【DRY-RUN 模式】仅统计，不写入数据库")

    # ── 加载信源映射 ──────────────────────────────────────────────────────────
    source_lookup = build_source_lookup()

    # ── 读取全部记录 ──────────────────────────────────────────────────────────
    with db.get_connection() as conn:
        conn.row_factory = __import__('sqlite3').Row
        all_rows = conn.execute(
            "SELECT id, title, translated_title, source_name, domain, "
            "       who, what, tags, heat_score, source_score "
            "FROM news ORDER BY id"
        ).fetchall()
    all_rows = [dict(r) for r in all_rows]
    logger.info(f"总记录数: {len(all_rows)}")

    # 分类
    rows_need_score = [r for r in all_rows if r['domain']]
    rows_no_domain  = [r for r in all_rows if not r['domain']]
    logger.info(f"需要评分（有 domain）: {len(rows_need_score)} 条")
    logger.info(f"需要分类（无 domain）: {len(rows_no_domain)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: source_score（程序化）
    # ─────────────────────────────────────────────────────────────────────────
    if only in (None, 'source'):
        logger.info("── Step 1: 计算 source_score ──")
        updates: List[Tuple[float, int]] = []
        for row in rows_need_score:
            s = get_source_score(row['source_name'] or '', source_lookup)
            updates.append((s, row['id']))

        logger.info(f"  source_score 分布: 10分={sum(1 for u in updates if u[0]==10)} / "
                    f"8分={sum(1 for u in updates if u[0]==8)} / "
                    f"6分={sum(1 for u in updates if u[0]==6)} / "
                    f"5分={sum(1 for u in updates if u[0]==5)}")

        if not dry_run:
            with db.get_connection() as conn:
                conn.executemany("UPDATE news SET source_score=? WHERE id=?", updates)
                conn.commit()
            logger.info(f"  ✓ source_score 写入 {len(updates)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: heat_score（启发式）
    # ─────────────────────────────────────────────────────────────────────────
    if only in (None, 'heat'):
        logger.info("── Step 2: 计算历史 heat_score（启发式）──")
        updates = []
        # 重新取 source_score（可能刚写入）
        with db.get_connection() as conn:
            score_map = {r[0]: r[1] for r in conn.execute(
                "SELECT id, source_score FROM news WHERE domain IS NOT NULL AND domain!=''"
            ).fetchall()}

        for row in rows_need_score:
            s_score = score_map.get(row['id']) or get_source_score(row['source_name'] or '', source_lookup)
            h = get_historical_heat_score(row['domain'] or '', s_score or 5.0)
            updates.append((h, row['id']))

        if not dry_run:
            with db.get_connection() as conn:
                conn.executemany("UPDATE news SET heat_score=? WHERE id=?", updates)
                conn.commit()
            logger.info(f"  ✓ heat_score 写入 {len(updates)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: tags 规则生成
    # ─────────────────────────────────────────────────────────────────────────
    if only in (None, 'tags'):
        logger.info("── Step 3: 生成缺失 tags ──")
        rows_no_tags = [r for r in all_rows if not r.get('tags') and r.get('domain')]
        logger.info(f"  需要生成 tags: {len(rows_no_tags)} 条")

        updates = []
        for row in rows_no_tags:
            t = generate_tags(
                row.get('domain', ''),
                row.get('who', '') or '',
                row.get('what', '') or '',
                row.get('tags', '') or '',
            )
            updates.append((t, row['id']))

        if not dry_run:
            with db.get_connection() as conn:
                conn.executemany("UPDATE news SET tags=? WHERE id=?", updates)
                conn.commit()
            logger.info(f"  ✓ tags 写入 {len(updates)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3b: 规则打分（influence + value，无需 LLM）
    # ─────────────────────────────────────────────────────────────────────────
    if only in (None, 'rule_score'):
        logger.info("-- Step 3b: 规则打分 (influence_score + value_score) --")
        # 读取最新 source_score（已写入）
        with db.get_connection() as conn:
            fresh_scores = {r[0]: r[1] for r in conn.execute(
                "SELECT id, source_score FROM news"
            ).fetchall()}

        updates_rule: List[Tuple[float, float, int]] = []
        for row in all_rows:
            row_with_src = dict(row)
            row_with_src['source_score'] = fresh_scores.get(row['id']) or row.get('source_score') or 5.0
            inf, val = rule_score_influence_value(row_with_src)
            updates_rule.append((inf, val, row['id']))

        if not dry_run:
            with db.get_connection() as conn:
                conn.executemany(
                    "UPDATE news SET influence_score=?, value_score=? WHERE id=?",
                    updates_rule,
                )
                conn.commit()
            logger.info(f"  rule_score: influence/value 写入 {len(updates_rule)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: LLM 批量评分（influence + value）
    # ─────────────────────────────────────────────────────────────────────────
    if only in ('llm',):
        logger.info("── Step 4: LLM 批量评分（influence_score + value_score）──")

        from core.processor.ai_processor import AIProcessor
        ai = AIProcessor()
        provider = ai.get_provider("FILTER")
        if not provider:
            logger.error("FILTER provider 不可用，跳过 LLM 评分")
        else:
            total_batches = (len(rows_need_score) + batch_size - 1) // batch_size
            logger.info(f"  共 {len(rows_need_score)} 条，{total_batches} 批（每批 {batch_size} 条）")

            all_llm_updates: List[Tuple[float, float, int]] = []

            for batch_idx in range(total_batches):
                batch = rows_need_score[batch_idx * batch_size: (batch_idx + 1) * batch_size]
                scores = llm_score_batch(provider, batch)

                for row, (inf, val) in zip(batch, scores):
                    all_llm_updates.append((inf, val, row['id']))

                if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
                    logger.info(f"  进度: {batch_idx + 1}/{total_batches} 批完成")

                # 避免触发 rate limit
                time.sleep(0.3)

            if not dry_run:
                with db.get_connection() as conn:
                    conn.executemany(
                        "UPDATE news SET influence_score=?, value_score=? WHERE id=?",
                        all_llm_updates,
                    )
                    conn.commit()
                logger.info(f"  ✓ influence_score/value_score 写入 {len(all_llm_updates)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: domain 补全（B类，16条）
    # ─────────────────────────────────────────────────────────────────────────
    if only in (None, 'domain') and rows_no_domain:
        logger.info(f"── Step 5: domain 补全（{len(rows_no_domain)} 条）──")

        from core.processor.ai_processor import AIProcessor
        ai = AIProcessor()
        provider = ai.get_provider("FILTER")
        if not provider:
            logger.warning("FILTER provider 不可用，跳过 domain 分类")
        else:
            domains = classify_domains(provider, rows_no_domain)
            updates = [(d, r['id']) for d, r in zip(domains, rows_no_domain)]
            for domain, row in zip(domains, rows_no_domain):
                title = row.get('translated_title') or row.get('title', '')
                logger.info(f"  [{domain}] {title[:50]}")

            if not dry_run:
                with db.get_connection() as conn:
                    conn.executemany("UPDATE news SET domain=? WHERE id=?", updates)
                    conn.commit()
                logger.info(f"  ✓ domain 写入 {len(updates)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 6: final_score 计算
    # ─────────────────────────────────────────────────────────────────────────
    if only in (None, 'final'):
        logger.info("── Step 6: 计算 final_score ──")

        with db.get_connection() as conn:
            score_rows = conn.execute(
                "SELECT id, source_score, influence_score, heat_score, value_score "
                "FROM news WHERE domain IS NOT NULL AND domain!=''"
            ).fetchall()

        updates = []
        skipped = 0
        for r in score_rows:
            sid, src, inf, heat, val = r
            if any(x is None for x in [src, inf, heat, val]):
                skipped += 1
                continue
            final = compute_final_score(src, inf, heat, val)
            updates.append((final, sid))

        logger.info(f"  可计算: {len(updates)} 条，缺分数跳过: {skipped} 条")

        if updates:
            # 分布统计
            scores = [u[0] for u in updates]
            logger.info(f"  分数分布: min={min(scores):.1f}, max={max(scores):.1f}, "
                        f"avg={sum(scores)/len(scores):.1f}")
            buckets = {f"{i*10}-{i*10+10}": sum(1 for s in scores if i*10<=s<(i+1)*10)
                       for i in range(10)}
            logger.info(f"  区间分布: {buckets}")

        if not dry_run and updates:
            with db.get_connection() as conn:
                conn.executemany("UPDATE news SET final_score=? WHERE id=?", updates)
                conn.commit()
            logger.info(f"  ✓ final_score 写入 {len(updates)} 条")

    # ─────────────────────────────────────────────────────────────────────────
    # 最终统计
    # ─────────────────────────────────────────────────────────────────────────
    logger.info("── 修复完成，最终统计 ──")
    with db.get_connection() as conn:
        stats = conn.execute("""
            SELECT
              COUNT(*) as total,
              SUM(CASE WHEN final_score IS NOT NULL THEN 1 ELSE 0 END) as with_final,
              SUM(CASE WHEN tags IS NOT NULL AND tags!='' THEN 1 ELSE 0 END) as with_tags,
              SUM(CASE WHEN domain IS NOT NULL AND domain!='' THEN 1 ELSE 0 END) as with_domain,
              ROUND(AVG(final_score),1) as avg_score,
              MAX(final_score) as max_score
            FROM news
        """).fetchone()
    logger.info(
        f"  总计: {stats[0]} | 有final_score: {stats[1]} | 有tags: {stats[2]} | "
        f"有domain: {stats[3]} | 平均分: {stats[4]} | 最高分: {stats[5]}"
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="历史数据评分修复脚本")
    parser.add_argument('--dry-run', action='store_true',
                        help='仅统计，不写入数据库')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                        help=f'LLM 批次大小（默认 {DEFAULT_BATCH_SIZE}）')
    parser.add_argument('--only', choices=['source', 'heat', 'tags', 'rule_score', 'llm', 'domain', 'final'],
                        default=None, help='只运行指定步骤（调试用）')
    args = parser.parse_args()
    run_repair(args)


if __name__ == '__main__':
    main()
