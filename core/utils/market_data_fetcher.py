#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据获取模块 - 每日一次，免费公开数据源

设计原则：
- 数据仅用于简报仪表盘展示（不经 LLM 推断）
- 深度报告中仅当新闻与数据存在明确关联时，作为背景锚点注入
- 所有来源均为公开免费接口，零 API 成本
- 任何单项失败均静默降级，不阻断报告生成
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "market_cache"
_CACHE_TTL_HOURS = 20  # 日内有效，次日重新获取


@dataclass
class MarketSnapshot:
    """当日市场数据快照"""
    date: str                       # YYYY-MM-DD

    # 主要指数（涨跌幅 %）
    sh_index: Optional[float] = None        # 上证指数
    sh_index_chg: Optional[float] = None    # 涨跌幅
    nasdaq: Optional[float] = None          # 纳斯达克
    nasdaq_chg: Optional[float] = None
    sp500: Optional[float] = None           # 标普500
    sp500_chg: Optional[float] = None
    hsi: Optional[float] = None             # 恒生指数
    hsi_chg: Optional[float] = None

    # 汇率（相对人民币）
    usd_cny: Optional[float] = None         # 美元/人民币
    eur_cny: Optional[float] = None         # 欧元/人民币
    jpy_cny: Optional[float] = None         # 日元/人民币（100日元）

    # 大宗商品
    oil_wti: Optional[float] = None         # WTI 原油（美元/桶）
    oil_brent: Optional[float] = None       # 布伦特原油
    gold: Optional[float] = None            # 黄金（美元/盎司）

    # 利率背景
    us_fed_rate: Optional[float] = None     # 美联储基准利率
    cn_lpr_1y: Optional[float] = None       # 中国 LPR 1年期

    fetched_at: str = ""

    def to_display_lines(self) -> list[str]:
        """格式化为简报仪表盘行，仅展示有数据的字段"""
        def _fmt_idx(val, chg):
            if val is None:
                return "N/A"
            arrow = ("+" if chg >= 0 else "") + f"{chg:.2f}%" if chg is not None else ""
            return f"{val:,.0f} ({arrow})" if chg is not None else f"{val:,.0f}"

        def _fmt(val, unit="", precision=2):
            if val is None:
                return "N/A"
            return f"{val:.{precision}f}{unit}"

        lines = []
        # 指数
        idx_parts = []
        if self.sh_index is not None:
            idx_parts.append(f"上证 {_fmt_idx(self.sh_index, self.sh_index_chg)}")
        if self.nasdaq is not None:
            idx_parts.append(f"纳指 {_fmt_idx(self.nasdaq, self.nasdaq_chg)}")
        if self.sp500 is not None:
            idx_parts.append(f"标普 {_fmt_idx(self.sp500, self.sp500_chg)}")
        if self.hsi is not None:
            idx_parts.append(f"恒生 {_fmt_idx(self.hsi, self.hsi_chg)}")
        if idx_parts:
            lines.append("**主要指数**：" + " | ".join(idx_parts))

        # 汇率
        fx_parts = []
        if self.usd_cny is not None:
            fx_parts.append(f"USD/CNY {_fmt(self.usd_cny, precision=4)}")
        if self.eur_cny is not None:
            fx_parts.append(f"EUR/CNY {_fmt(self.eur_cny, precision=4)}")
        if self.jpy_cny is not None:
            fx_parts.append(f"JPY/CNY(×100) {_fmt(self.jpy_cny, precision=4)}")
        if fx_parts:
            lines.append("**主要汇率**：" + " | ".join(fx_parts))

        # 大宗
        cmdy_parts = []
        if self.oil_wti is not None:
            cmdy_parts.append(f"WTI {_fmt(self.oil_wti, '$/桶')}")
        if self.oil_brent is not None:
            cmdy_parts.append(f"布伦特 {_fmt(self.oil_brent, '$/桶')}")
        if self.gold is not None:
            cmdy_parts.append(f"黄金 {_fmt(self.gold, '$/oz', 0)}")
        if cmdy_parts:
            lines.append("**大宗商品**：" + " | ".join(cmdy_parts))

        # 利率
        rate_parts = []
        if self.us_fed_rate is not None:
            rate_parts.append(f"美联储利率 {_fmt(self.us_fed_rate, '%')}")
        if self.cn_lpr_1y is not None:
            rate_parts.append(f"LPR1Y {_fmt(self.cn_lpr_1y, '%')}")
        if rate_parts:
            lines.append("**关键利率**：" + " | ".join(rate_parts))

        return lines

    def as_anchor_text(self) -> str:
        """生成用于 LLM 上下文的背景锚点文本（仅在新闻与之直接相关时注入）"""
        lines = self.to_display_lines()
        if not lines:
            return ""
        return "【当日市场背景（仅作参考锚点，请勿强行关联）】\n" + "\n".join(lines)


class MarketDataFetcher:
    """市场数据获取器（单例，带日级缓存）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def get_snapshot(self, force_refresh: bool = False) -> MarketSnapshot:
        """获取今日市场快照，优先返回缓存"""
        today = date.today().isoformat()
        cache_file = _CACHE_DIR / f"market_{today}.json"

        if not force_refresh and cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                snap = MarketSnapshot(**data)
                logger.debug(f"市场数据从缓存读取: {today}")
                return snap
            except Exception:
                pass  # 缓存损坏，重新获取

        snap = self._fetch_all(today)
        try:
            cache_file.write_text(
                json.dumps(asdict(snap), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"市场数据缓存写入失败: {e}")
        return snap

    def _fetch_all(self, today: str) -> MarketSnapshot:
        snap = MarketSnapshot(date=today, fetched_at=datetime.now().isoformat())

        # 各项独立获取，单项失败不影响其他
        self._fetch_exchange_rates(snap)
        self._fetch_indices_eastmoney(snap)
        self._fetch_commodities(snap)
        self._fetch_rates_fred(snap)

        return snap

    def _fetch_exchange_rates(self, snap: MarketSnapshot) -> None:
        """汇率 - ExchangeRate-API 免费层（无需 key，每日1500次）"""
        try:
            import urllib.request
            url = "https://open.er-api.com/v6/latest/USD"
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read())
            rates = data.get("rates", {})
            cny_per_usd = rates.get("CNY")
            if cny_per_usd:
                snap.usd_cny = round(cny_per_usd, 4)
                eur_per_usd = rates.get("EUR")
                jpy_per_usd = rates.get("JPY")
                if eur_per_usd and eur_per_usd > 0:
                    snap.eur_cny = round(cny_per_usd / eur_per_usd, 4)
                if jpy_per_usd and jpy_per_usd > 0:
                    snap.jpy_cny = round(cny_per_usd / jpy_per_usd * 100, 4)
        except Exception as e:
            logger.debug(f"汇率获取失败（降级）: {e}")

    def _fetch_indices_eastmoney(self, snap: MarketSnapshot) -> None:
        """A股指数 - 东方财富公开行情接口"""
        try:
            import urllib.request
            # 上证指数: secid=1.000001
            url = (
                "https://push2.eastmoney.com/api/qt/stock/get"
                "?secid=1.000001&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b"
            )
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.eastmoney.com/"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            d = data.get("data", {}) or {}
            price = d.get("f43")   # 当前价 × 100
            chg = d.get("f170")    # 涨跌幅 × 100
            if price:
                snap.sh_index = round(price / 100, 2)
            if chg:
                snap.sh_index_chg = round(chg / 100, 2)
        except Exception as e:
            logger.debug(f"上证指数获取失败（降级）: {e}")

    def _fetch_commodities(self, snap: MarketSnapshot) -> None:
        """大宗商品 - 使用公开数据聚合接口"""
        try:
            import urllib.request
            # 使用 metals-api 免费替代方案：commodities via Yahoo Finance CSV
            # WTI 原油: CL=F, 布伦特: BZ=F, 黄金: GC=F
            symbols = {"CL=F": "wti", "BZ=F": "brent", "GC=F": "gold"}
            for symbol, key in symbols.items():
                try:
                    url = (
                        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                        f"?interval=1d&range=1d"
                    )
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        data = json.loads(resp.read())
                    result = data["chart"]["result"][0]
                    price = result["meta"].get("regularMarketPrice")
                    if price:
                        if key == "wti":
                            snap.oil_wti = round(float(price), 2)
                        elif key == "brent":
                            snap.oil_brent = round(float(price), 2)
                        elif key == "gold":
                            snap.gold = round(float(price), 0)
                    time.sleep(0.3)  # 避免频率限制
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"大宗商品获取失败（降级）: {e}")

    def _fetch_rates_fred(self, snap: MarketSnapshot) -> None:
        """关键利率 - FRED 公开 API（免费，无需注册）"""
        try:
            import urllib.request
            api_key = "DEMO_KEY"  # FRED 演示 key，限流 1000次/天，足够

            def _fred_latest(series_id: str) -> Optional[float]:
                url = (
                    f"https://api.stlouisfed.org/fred/series/observations"
                    f"?series_id={series_id}&api_key={api_key}&file_type=json"
                    f"&sort_order=desc&limit=1"
                )
                try:
                    with urllib.request.urlopen(url, timeout=8) as resp:
                        data = json.loads(resp.read())
                    obs = data.get("observations", [])
                    val = obs[0].get("value", ".") if obs else "."
                    return float(val) if val != "." else None
                except Exception:
                    return None

            fed = _fred_latest("FEDFUNDS")  # 联邦基金利率（月度）
            if fed is not None:
                snap.us_fed_rate = round(fed, 2)

            lpr = _fred_latest("INTDSRCNM193N")  # 中国贷款利率（月度近似）
            if lpr is not None:
                snap.cn_lpr_1y = round(lpr, 2)

        except Exception as e:
            logger.debug(f"利率数据获取失败（降级）: {e}")


def get_market_snapshot(force_refresh: bool = False) -> MarketSnapshot:
    """模块级入口"""
    return MarketDataFetcher().get_snapshot(force_refresh=force_refresh)
