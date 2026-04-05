# 新闻分析自动化工作流 (News Analyzer)

基于 AI 的新闻采集与分析系统，支持 RSS 多信源采集、AI 智能过滤（5W1H检测 + 五大维度评分）、多维度报告生成与邮件推送。

**最后更新**: 2026-03-13 | **版本**: 3.13.0 | **架构状态**: 与代码完全一致 | **云部署**: ✅ 就绪

---

## 目录

- [功能概览](#功能概览)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [运行方式](#运行方式)
- [云部署](#云部署)
- [输出说明](#输出说明)
- [常见问题](#常见问题)
- [项目结构](#项目结构)
- [数据架构](#数据架构)
- [安全说明](#安全说明)
- [许可证](#许可证)

---

## 功能概览

### 核心功能

| 功能 | 说明 |
|------|------|
| **多信源采集** | RSS 官媒 + 第三方媒体，支持 sources.yaml 配置，多层级兜底机制 |
| **规则优先解析** | YAML规则库驱动的领域/标签抽取，AI兜底补全 |
| **智能回溯** | 根据采集间隔自动计算回溯时间，支持定时/中断/首次采集场景 |
| **遗漏检测** | RSS滚动边界检测，自动识别新闻遗漏并预警 |
| **遗漏补救** | 检测到遗漏时自动触发补救采集，扩大回溯时间，尽最大努力保证数据连贯性 |
| **补救验证** | 补救后重新检测遗漏，验证补救效果（完全补救/部分补救/补救失败） |
| **AI 5W1H 检测** | 自动提取何时、何地、何人、何事、何因、如何 |
| **五大维度评分** | 信源权重、事件影响力、传播热度、新闻价值、合规风险 |
| **多语言翻译** | 自动识别外文新闻并翻译成中文 |
| **事件聚类** | 同一事件的多个报道自动聚合，结果持久化到数据库 |
| **历史关联** | 近90天历史新闻关联分析（含实体维度预留） |
| **图表生成** | 支持 Plotly/Matplotlib 生成趋势图、对比图、饼图等 |
| **报告模板** | 支持 default/minimal/detailed 三种报告模板 |
| **双报告输出** | 简要摘要（邮件正文）+ 深度分析（PDF附件） |
| **跨领域共振** | 自动分析多领域大事件交汇点与底层逻辑关联，推演宏观风险 |
| **异常偏离检测** | RAG结合语义检索，识别与近期历史基线存在显著偏差的异动信息 |
| **PDF 生成** | 自动生成 PDF 格式报告，方便阅读和存档 |
| **邮件推送** | 简要版作为正文 + 深度版作为 PDF 附件 |
| **知识库(RAG)** | ChromaDB向量存储，RAG增强报告生成，解决AI幻觉 |

### 报告类型

1. **简要摘要报告**（邮件正文）
   - 中国 TOP10 新闻 + 国外 TOP10 新闻
   - 简洁排版，适合移动端快速浏览
   - 直接作为邮件正文发送

2. **深度分析报告**（PDF 附件）
   - 政治、经济、科技三大领域独立报告
   - 事件深度洞察（约900字完整文章）
   - 领域整体分析（约1000字完整文章）
   - 历史关联 + 趋势预判
   - PDF 格式，方便阅读和存档

---

## 遗漏驱动的智能回溯架构

### 核心理念

基于**第一性原理**设计，目标是**保证数据连贯性不丢失**：

1. **判断依据**：实际遗漏检测结果，而非猜测中断时长
2. **补救措施**：检测到遗漏时自动触发补救采集
3. **效果验证**：补救后重新检测，确认是否成功
4. **数据保证**：尽最大努力保证数据连贯性

### 工作流程

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         遗漏驱动的智能回溯架构                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

开始采集
  ↓
第一步：正常采集（基于上次最新时间）
  ├─ 获取上次最新发布时间
  ├─ 使用智能回溯计算截止日期（与全局采样频率联动）
  └─ 采集新闻
  ↓
第二步：遗漏检测（RSS滚动边界检测）
  ├─ 获取数据库最新时间
  ├─ 获取RSS最早时间
  └─ 判断是否遗漏
  ↓
第三步：补救措施（如果遗漏）
  ├─ 扩大回溯时间到RSS滚动限制
  ├─ 重新采集
  └─ 合并新闻（去重）
  ↓
第四步：补救效果验证
  ├─ 重新检测遗漏
  ├─ 判断补救效果
  │   ├─ ✅ 完全补救：遗漏分数 = 0
  │   ├─ ⚠️  部分补救：遗漏分数改善 > 0
  │   └─ ❌ 补救失败：遗漏分数未改善
  └─ 记录补救统计
  ↓
完成
```

### 与全局采样频率联动

智能回溯现在基于全局采样频率配置（`interval_hours = 8`）：

| 场景 | 中断时长 | 判断 | 回溯策略 |
|------|---------|------|---------|
| 正常采集 | 6.4小时 | 正常采集间隔内 | 回溯 6.4h + 缓冲 1h |
| 正常采集 | 8小时 | 正常采集间隔 | 回溯 8h + 缓冲 1h |
| 轻微延迟 | 10小时 | 轻微延迟 | 回溯 10h + 缓冲 2h |
| 中等延迟 | 16小时 | 中等延迟 | 回溯 16h × 1.2 |
| 异常中断 | 24小时 | 异常中断 | 回溯 24h + 12h |

### 遗漏分数计算

```
遗漏分数 = min(1.0, 遗漏时长 / 采集间隔)
```

**示例**：
- 遗漏 3.7 小时，采集间隔 8 小时 → 遗漏分数 = min(1.0, 3.7/8) = 0.46
- 遗漏 0 小时 → 遗漏分数 = 0

### 补救效果判断

| 补救效果 | 判断条件 | 遗漏分数变化 | 说明 |
|---------|---------|------------|------|
| **✅ 完全补救** | `has_gap = False` | 1.0 → 0 | 数据库最新 >= RSS最早，无遗漏 |
| **⚠️ 部分补救** | `has_gap = True` 且 `improvement > 0` | 1.0 → 0.3 | 补救了一些，但仍有遗漏 |
| **❌ 补救失败** | `has_gap = True` 且 `improvement <= 0` | 1.0 → 1.0 | 补救无效，可能RSS已滚动 |

### 日志示例

```
智能回溯 路透社: 中断6.4h → 正常采集 [正常采集] → 回溯7.4h

⚠️  遗漏检测 [钛媒体]: 检测到RSS滚动遗漏
数据库最新(03-12 14:33) < RSS最早(03-12 18:13)
遗漏约 3.7 小时内容

🔧 触发补救采集 [钛媒体]
🔧 补救采集 [钛媒体]: 扩大回溯至 48小时
补救采集完成 [钛媒体]: 补救 15 条新闻
🔍 补救效果验证 [钛媒体]: 重新检测遗漏...
✅ 补救成功 [钛媒体]: 遗漏已完全补救
```

### 统计输出

```
📊 任务1执行完成
======================================================================
采集总量: 150 条
白名单通过: 150 条
可信度通过: 150 条
历史去重通过: 148 条
内容校验通过: 148 条
AI校验通过: 145 条
🔧 补救采集: 15 条
   └─ ✅ 补救成功: 1 个源
存入数据库: 145 条
======================================================================
```

### 配置文件

相关配置在 `utils/collection_config.py` 中：

```python
# 全局采集时间表
GLOBAL_SCHEDULE = CollectionSchedule(
    interval_hours=8,      # 每8小时采集一次
    buffer_hours=1,        # 正常采集缓冲时间
    max_lookback_hours=72  # 最大回溯时间
)

# RSS滚动限制（按信源类型）
RSS_ROLLOVER_HOURS = {
    'high_frequency': 24,   # 高频源（如路透社）：24小时
    'medium_frequency': 48, # 中频源（如钛媒体）：48小时
    'low_frequency': 72     # 低频源（如周刊）：72小时
}
```

---

## 环境要求

- **Python**: 3.9 或更高版本
- **网络**: 可访问 RSS 源及 AI API（豆包/DeepSeek/Qwen）
- **操作系统**: Windows / macOS / Linux

---

## 快速开始

### 第一步：克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/news_analyzer.git
cd news_analyzer
```

### 第二步：安装依赖

```bash
pip install -r requirements.txt
```

### 第三步：配置环境变量

1. 复制示例配置：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，配置必要参数：

   ```env
   # ==================== AI 模型配置 ====================
   # 说明：深度分析和快速筛选可能使用不同模型
   # 格式：AI_<用途>_<信息类型> = <值>
   # 用途：ANALYSIS(深度分析) / FILTER(快速筛选) / BACKUP(备用)
   # 信息类型：PROVIDER(厂商) / MODEL(模型名) / KEY(密钥) / BASE_URL(API地址，可选)

   # ---------- 深度分析模型 ----------
   AI_ANALYSIS_PROVIDER=deepseek
   AI_ANALYSIS_MODEL=deepseek-reasoner
   AI_ANALYSIS_KEY=your-deepseek-api-key
   AI_ANALYSIS_BASE_URL=https://api.deepseek.com/v1

   # ---------- 快速筛选模型 ----------
   AI_FILTER_PROVIDER=doubao
   AI_FILTER_MODEL=doubao-seed-2-0-lite-260215
   AI_FILTER_KEY=your-doubao-api-key
   AI_FILTER_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

   # ---------- 备用模型 ----------
   AI_BACKUP_PROVIDER=qwen
   AI_BACKUP_MODEL=qwen-max
   AI_BACKUP_KEY=your-qwen-api-key
   AI_BACKUP_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

   # ---------- OpenRouter（免费模型） ----------
   # OpenRouter提供免费模型：stepfun/step-3.5-flash:free
   # 需要注册获取API Key: https://openrouter.ai
   # AI_FILTER_PROVIDER=openrouter
   # AI_FILTER_MODEL=stepfun/step-3.5-flash:free
   # AI_FILTER_KEY=your-openrouter-api-key
   # AI_FILTER_BASE_URL=https://openrouter.ai/api/v1

   # ==================== 邮件推送（可选）====================
   SMTP_HOST=smtp.qq.com
   SMTP_PORT=587
   SMTP_USER=your_email@qq.com
   SMTP_PASSWORD=your_auth_code
   EMAIL_TO=recipient@example.com

   # ==================== 代理配置（可选）====================
   HTTP_PROXY=http://127.0.0.1:7890
   HTTPS_PROXY=http://127.0.0.1:7890
   ```

### 第四步：运行工作流

```bash
# 一键运行：采集 + 报告生成
python run_now.py
```

---

## 详细配置

### 配置管理系统

系统采用**双配置管理系统**，提供灵活性和向后兼容性：

| 配置模块 | 路径 | 用途 | 状态 |
|----------|------|------|------|
| **config/loader.py** | 基础配置加载器 | Windows适配的环境变量加载、必需配置验证 | ✅ 稳定 |
| **config/manager.py** | 统一配置管理器 | 所有配置的集中管理、YAML文件加载、点号路径访问 | ✅ 推荐 |

**推荐使用 `config/manager.py`**，它提供了统一的配置访问接口：

```python
from config.manager import get_config_manager

config = get_config_manager()
# 获取配置值（支持点号路径）
sources = config.get("sources.domestic.central")
api_key = config.get("env.deepseek_api_key")
```

所有配置文件自动从 `config/` 目录加载，包括：
- `config/ai_providers.yaml` - AI厂商配置
- `config/parsing_rules.yaml` - 解析规则配置（自定义）
- `config/report_templates.yaml` - 报告模板配置
- `config/knowledge.yaml` - 知识库配置

### AI 模型配置说明

系统支持多厂商、多用途的AI模型配置：

| 用途 | 说明 | 推荐模型 |
|------|------|----------|
| **ANALYSIS** | 深度分析报告生成 | DeepSeek-Reasoner、Qwen-Max |
| **FILTER** | 快速筛选、5W1H检测 | 豆包-Lite、DeepSeek-Chat |
| **BACKUP** | 备用模型 | 任意可用模型 |

**支持的厂商**：

| 厂商 | PROVIDER | SDK | 备注 |
|------|----------|-----|------|
| 豆包（火山引擎） | `doubao` | volcenginesdkarkruntime | 快速筛选推荐 |
| DeepSeek | `deepseek` | openai | 深度分析推荐 |
| 通义千问 | `qwen` | openai | 备用模型 |
| OpenRouter | `openrouter` | openai | 免费模型支持 |

**扩展其他厂商**：

编辑 `config/ai_providers.yaml` 添加新厂商：

```yaml
providers:
  openai:
    name: "OpenAI"
    base_url: "https://api.openai.com/v1"
    sdk: "openai"
```

### API 密钥获取

| API | 用途 | 获取地址 |
|-----|------|----------|
| 豆包（火山引擎） | 快速筛选 | https://console.volcengine.com/ark |
| DeepSeek | 深度分析 | https://platform.deepseek.com/ |
| 通义千问 | 备用 | https://dashscope.console.aliyun.com/ |
| OpenRouter | 免费模型 | https://openrouter.ai/ |

### AI 处理配置

```env
# AI 批处理大小（每批发送给 AI 的新闻数量，默认 4）
# 建议值：2-10，内容较长时可减小此值避免超时
AI_BATCH_SIZE=4
```

### 邮件配置说明

以 QQ 邮箱为例：

1. 登录 QQ 邮箱 → 设置 → 账户
2. 开启 POP3/SMTP 服务
3. 生成授权码（不是登录密码）
4. 在 `.env` 中配置：
   ```env
   SMTP_HOST=smtp.qq.com
   SMTP_PORT=587
   SMTP_USER=your_email@qq.com
   SMTP_PASSWORD=生成的授权码
   EMAIL_TO=接收报告的邮箱
   ```

### 解析规则配置

系统采用**规则优先、AI兜底**的解析策略。复制示例文件后按需编辑：

```bash
cp config/parsing_rules.example.yaml config/parsing_rules.yaml
```

规则结构示例：

```yaml
defaults:
  confidence_threshold:
    domain: 0.7   # 低于此值时 AI 可补全
    tags: 0.6
  domain_rules:
    - name: "科技默认规则"
      match:
        keywords_any: ["AI", "芯片", "机器人"]
      set:
        domain: "科技"
        tags_add: ["科技"]

sources:
  "路透社":
    rules:
      - name: "路透-宏观经济"
        match:
          rss_category_contains_any: ["Economy", "Markets"]
        set:
          domain: "经济"
          tags_add: ["国际", "宏观经济"]
```

**领域优先级**：规则命中 > RSS推断 > AI推断

**环境变量控制**：

| 变量 | 默认 | 说明 |
|------|------|------|
| `ENABLE_AI_TAG_FALLBACK` | `false` | 规则无法命中时是否调用AI进行标签补全 |
| `ENABLE_DB_BACKUP` | `true` | 每次采集后是否自动备份数据库 |
| `ENABLE_INVESTMENT_ANALYSIS` | `false` | 是否在深度报告中启用投资分析模块 |

---

### RSS 源配置

编辑 `sources.yaml` 文件添加或修改 RSS 源。系统支持多层级兜底机制：

```yaml
international:
  news_agency:
    - name: 路透社
      type: 通讯社
      region: 英国/全球
      credibility: 高
      tier: 1
      rss_url_official: https://www.reutersagency.com/feed/  # 官方源（优先级最高）
      rss_url_rsshub: https://rsshub.app/reuters/world       # RSSHub源
      rss_url_google: https://news.google.com/rss/search?q=site:reuters.com  # Google News源
      rss_url: https://news.google.com/rss/search?q=site:reuters.com  # 实际使用的RSS源
      rss_url_backup: https://rsshub.app/reuters/world  # 备份源
      enabled: true
      evaluation:
          authority: 高
          content_purity: 100%
          w5h1_completeness: 95%
          update_stability: 30天/日更
          rating: 5
```

**优先级顺序**: 官方源 → RSSHub → Google News → 第三方源 → 兼容旧配置

系统会自动尝试每个源，成功则停止，避免重复采集。50%+ 新闻源已配置官方 RSS。

**信源评估框架**：
- **权威性**：媒体是否具备一手采访能力、事实核查机制、行业声誉
- **内容纯净度**：报道是否主要来自原创/一手采访
- **5W1H完整性**：报道是否以事实信息为核心
- **更新稳定性**：是否持续产出符合标准的新闻

### 报告模板配置

系统支持三种报告模板，通过 `config/report_templates.yaml` 配置：

| 模板 | 说明 | 适用场景 | 主要特性 |
|------|------|----------|----------|
| `default` | 默认模板 | 平衡详细度和可读性 | 简要+深度报告、图表生成、PDF输出 |
| `minimal` | 精简模板 | 快速浏览，减少token消耗 | 仅简要报告、无图表、无PDF |
| `detailed` | 详细模板 | 完整分析，包含投资分析 | 详细报告、投资分析、完整图表 |

**模板切换**：
```yaml
active_template: default  # 可改为 minimal 或 detailed
```

**核心配置选项**：
- `generate_charts`: 是否生成图表（Plotly/Matplotlib）
- `generate_pdf`: 是否生成PDF文件
- `investment_analysis.enabled`: 是否启用投资分析模块
- `history_analysis.enabled`: 是否显示历史关联分析
- `max_items`: 每个领域显示的最大事件数

完整配置请参考 `config/report_templates.yaml`。

---

## 运行方式

### 本地运行

| 命令 | 说明 |
|------|------|
| `python run_collect.py` | 执行采集任务（支持任务锁） |
| `python run_report.py` | 生成报告并发送邮件 |
| `python run_now.py` | 一键运行：采集 + 报告 |
| `python send_email.py` | 发送邮件报告 |
| `python scripts/system_check.py` | 系统自检 |
| `python scripts/check_env.py` | 检查环境变量配置 |
| `python scripts/repair_db.py` | 数据库修复工具 |

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试（快速、隔离）
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行特定测试文件
pytest tests/unit/test_database.py -v

# 生成测试报告
pytest tests/ -v --html=report.html

# 运行系统自检
python scripts/system_check.py
```

**测试覆盖率**: 100% (94/94 通过)

### Windows 本地自动化

如果 GitHub Actions 暂时不可用，可以使用 Windows 任务计划程序实现本地自动化：

**一键设置**：
1. 进入 `scripts/` 文件夹
2. 右键点击 `setup_windows_tasks.bat`
3. 选择 **以管理员身份运行**（必须管理员权限！）

**取消任务**：
1. 进入 `scripts/` 文件夹
2. 右键点击 `remove_windows_tasks.bat`
3. 选择 **以管理员身份运行**

**时间表（北京时间）**：

| 时间 | 任务 | 说明 |
|------|------|------|
| **07:00** | 采集新闻 | 主任务：采集过去24小时全球新闻 |
| **07:05** | 生成报告 | 生成当日分析报告 |
| **08:30** | 发送报告邮件 | 发送最新报告 |
| 15:00 | 采集新闻 | 补充采集 |
| 23:00 | 采集新闻 | 补充采集 |

详细教程请参考 [WINDOWS_AUTOMATION_TUTORIAL.md](WINDOWS_AUTOMATION_TUTORIAL.md)

### GitHub Actions 自动化

项目支持 GitHub Actions 自动运行：

| 工作流 | 触发时间（北京时间） | 说明 |
|--------|----------------------|------|
| `collect.yml` | 早7:00 | 采集 + 生成报告（主任务） |
| `collect.yml` | 下午3:00、晚11:00 | 补充采集 |
| `send_email.yml` | 每日早8:30 | 发送报告邮件 |

**运行时间预算**：
- 每次采集约17分钟（批处理4条新闻）
- 每天采集3次 + 报告1次 ≈ 56分钟
- 每月约1680分钟，在GitHub Actions免费额度（2000分钟/月）内

**重要说明**：
- GitHub Actions 运行在 GitHub 服务器上，可直接访问国际网络
- **无需配置代理**，GitHub 服务器能正常访问 Reuters、BBC 等国际 RSS 源
- 只有本地运行时才需要配置代理

**配置 GitHub Secrets**：

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 必需 | 说明 |
|--------|------|------|
| `AI_ANALYSIS_PROVIDER` | ✅ | 深度分析厂商（如 deepseek） |
| `AI_ANALYSIS_MODEL` | ✅ | 深度分析模型名 |
| `AI_ANALYSIS_KEY` | ✅ | 深度分析API密钥 |
| `AI_FILTER_PROVIDER` | ✅ | 快速筛选厂商（如 doubao） |
| `AI_FILTER_MODEL` | ✅ | 快速筛选模型名 |
| `AI_FILTER_KEY` | ✅ | 快速筛选API密钥 |
| `AI_BACKUP_PROVIDER` | ❌ | 备用厂商 |
| `AI_BACKUP_MODEL` | ❌ | 备用模型名 |
| `AI_BACKUP_KEY` | ❌ | 备用API密钥 |
| `ENABLE_INVESTMENT_ANALYSIS` | ❌ | 是否启用投资分析（true/false） |
| `SMTP_HOST` | ✅ | SMTP 服务器 |
| `SMTP_PORT` | ✅ | SMTP 端口 |
| `SMTP_USER` | ✅ | 发件邮箱 |
| `SMTP_PASSWORD` | ✅ | 邮箱授权码 |
| `EMAIL_TO` | ✅ | 收件人邮箱 |

---

## 云部署

系统已完全支持云部署，提供 Docker 容器化和 GitHub Actions 两种方案。

### 快速云部署检查

```bash
# 持久化测试
python scripts/test_persistence.py

# 健康检查
python scripts/health_check.py

# 备份列表
python scripts/restore_backup.py --list
```

### Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 健康检查
docker-compose exec news_analyzer python scripts/health_check.py
```

### GitHub Actions 部署

项目已配置 GitHub Actions 工作流，支持自动定时运行：

| 工作流 | 触发时间（北京时间） | 说明 |
|--------|----------------------|------|
| `collect.yml` | 早7:00、下午3:00、晚11:00 | 新闻采集 |
| `report.yml` | 采集完成后 | 报告生成 |
| `send_email.yml` | 每日早8:30 | 邮件发送 |

**配置 GitHub Secrets**：

| Secret | 必需 | 说明 |
|--------|------|------|
| `AI_ANALYSIS_KEY` | ✅ | 深度分析API密钥 |
| `AI_FILTER_KEY` | ✅ | 快速筛选API密钥 |
| `SMTP_HOST` | ❌ | SMTP服务器 |
| `SMTP_PORT` | ❌ | SMTP端口 |
| `SMTP_USER` | ❌ | 发件邮箱 |
| `SMTP_PASSWORD` | ❌ | 邮箱授权码 |
| `EMAIL_TO` | ❌ | 收件人邮箱 |

### 云部署文档

详细部署指南请参考：
- [云部署完整教程](docs/CLOUD_DEPLOYMENT_TUTORIAL.md) - 从本地到云端的完整部署指南
- [部署指南](docs/DEPLOYMENT.md) - 详细部署文档
- [云迁移检查清单](docs/CLOUD_MIGRATION_CHECKLIST.md) - 部署前检查项

### 核心特性

| 特性 | 说明 |
|------|------|
| **数据持久化** | Docker 卷确保数据不丢失 |
| **日志轮转** | 自动管理日志文件大小（10MB） |
| **自动备份** | 每天凌晨和中午自动备份 |
| **版本锁定** | 依赖版本固定，确保环境一致 |
| **健康监控** | 完整的系统健康检查机制 |

---

## 输出说明

### 报告文件位置

```
reports/
└── 2026-03-09/                           # 按日期分类
    ├── brief/                            # 简要摘要报告
    │   ├── daily_report_2026-03-09.md    # MD 版本
    │   └── daily_report_2026-03-09.pdf   # PDF 版本
    │
    ├── depth/                            # 深度分析报告
    │   ├── daily_report_depth_政治_2026-03-09.md
    │   ├── daily_report_depth_政治_2026-03-09.pdf
    │   ├── daily_report_depth_经济_2026-03-09.md
    │   ├── daily_report_depth_经济_2026-03-09.pdf
    │   ├── daily_report_depth_科技_2026-03-09.md
    │   └── daily_report_depth_科技_2026-03-09.pdf
    │
    └── charts/                           # 图表文件（与报告同日期）
        ├── trend_ma_*.html               # 趋势图（HTML交互式）
        ├── trend_ma_*.png                # 趋势图（PNG静态）
        └── score_dist_*.png              # 评分分布图
```

### 邮件发送格式

| 报告类型 | 发送方式 | 说明 |
|----------|----------|------|
| **简要摘要报告** | 邮件正文 | 纯文本，手机用户可直接阅读 |
| **深度分析报告** | PDF 附件 | 政治/经济/科技领域详细分析 |

### AI 评分说明

五大维度评分：

| 维度 | 权重 | 说明 |
|------|------|------|
| 信源权重 | 30% | 中央媒体10分、权威通讯社8-9分、普通媒体4-5分 |
| 事件影响力 | 40% | 全球性10分、国家级8-9分、行业级6-7分 |
| 传播热度 | 20% | 全网热搜10分、多平台热搜8-9分 |
| 新闻价值 | 10% | 独家重磅10分、有价值信息6-7分 |
| 合规风险 | 反向扣分 | 0-0.05直接扣减 |

评分公式：
```
最终得分 = (信源/10×30% + 影响力/10×40% + 热度/10×20% + 价值/10×10%) × 100 × (1 - 合规扣分)
```

### 深度分析报告格式

深度分析报告采用**数据严谨 + 可读性强**的设计理念：

**报告结构**：
```
# XX领域深度分析报告（日期）

## 领域数据总览表（当日 vs 近7天 vs 近30天）
## 当日重点事件一览表

## 事件1：标题
### 基础信息
### 评分拆解表
### 5W1H要素表
### 历史关联分析表
### 单事件深度洞察（连贯文章，约900字）

## 事件2...
## 领域当日整体分析（连贯文章，约1000字）
```

**设计特点**：
- **数据表格化**：领域总览、评分拆解、5W1H、历史关联均以表格呈现
- **洞察文章化**：深度洞察为连贯文章形式，但内容隐含结构化逻辑（核心要点→直接影响→趋势预判→风险机遇）
- **投资分析**：可选功能，通过 `ENABLE_INVESTMENT_ANALYSIS=true` 启用

---

## 常见问题

### Q1: 运行时提示 "待分析池为空"

**原因**：采集任务没有成功获取新闻

**解决**：
1. 检查网络连接
2. 检查代理配置（如需访问国际RSS源）
3. 先运行 `python task1_collector.py` 执行采集

### Q2: AI 分析失败

**原因**：API 密钥无效或网络问题

**解决**：
1. 检查 `.env` 中的 API 密钥是否正确
2. 运行 `python check_env.py` 检查环境变量
3. 检查网络是否能访问 API 服务
4. 查看日志文件 `logs/` 目录

### Q3: 邮件发送失败

**原因**：SMTP 配置错误

**解决**：
1. 确认 SMTP 服务器地址和端口正确
2. 使用授权码而非登录密码
3. 检查邮箱是否开启 SMTP 服务

### Q4: 报告没有生成

**原因**：数据库中没有最近24小时的新闻

**解决**：
1. 运行 `python -c "from storage.database import NewsDatabase; print(NewsDatabase().get_stats())"` 检查数据库
2. 先运行 `python task1_collector.py` 执行采集
3. 查看日志文件排查错误

### Q5: 豆包 API 认证失败

**原因**：API Key 格式不正确或模型名称错误

**解决**：
1. 确认 API Key 格式正确
2. 确认模型名称正确（如 `doubao-seed-2-0-lite-260215`）
3. 检查火山引擎控制台是否已创建推理接入点

### Q6: PDF 生成失败

**原因**：reportlab 未安装

**解决**：
```bash
pip install reportlab
```

---

## 项目结构

```
news_analyzer/
├── .github/workflows/       # GitHub Actions 配置
│   ├── collect.yml          # 采集工作流（每天3次，超时60分钟）
│   ├── report.yml           # 报告生成工作流（超时45分钟）
│   └── send_email.yml       # 邮件发送工作流（超时15分钟）
│
├── analysts/                # 深度分析模块
│   ├── depth_analyzer.py    # 深度分析器（900-1200字文章）
│   └── investment_advisor.py # 投资建议模块（可选启用）
│
├── config/                  # 配置模块
│   ├── ai_providers.yaml         # AI厂商配置（知识库）
│   ├── parsing_rules.yaml        # 规则解析配置（自定义，不提交）
│   ├── parsing_rules.example.yaml # 规则配置示例
│   ├── report_templates.yaml     # 报告模板配置
│   ├── report_templates.py       # 报告模板管理器
│   ├── knowledge.yaml            # 知识库配置
│   └── loader.py                 # 环境变量加载
│
├── docs/                    # 项目文档
│   ├── ARCHITECTURE_REVIEW.md    # 架构审查报告（V1）
│   ├── ARCHITECTURE_REVIEW_V2.md # 架构审查报告（V2）
│   ├── ARCHITECTURE_REVIEW_V3.md # 架构审查报告（V3，最新）
│   ├── CLOUD_DEPLOYMENT_TUTORIAL.md # 云部署完整教程
│   ├── DEPLOYMENT.md             # 云部署指南
│   ├── CLOUD_MIGRATION_CHECKLIST.md # 云迁移检查清单
│   └── REPORT_STYLE_GUIDE.md     # 报告风格指南
│
├── filters/                 # 过滤模块
│   ├── ai_filter_agent.py   # AI 5W1H 检测 + 评分
│   ├── content_filter.py    # 内容过滤
│   ├── deduplication.py     # 去重
│   └── source_validator.py  # 来源验证
│
├── generators/              # 报告生成模块
│   └── report_generator.py  # 简要摘要 + 深度分析 + PDF + RAG增强
│
├── knowledge/               # 知识库模块
│   ├── base.py              # 知识库基类
│   ├── chroma_store.py      # ChromaDB存储实现
│   ├── embedding.py         # 向量化服务
│   ├── retriever.py         # RAG检索器
│   ├── pipeline.py          # 向量化Pipeline
│   ├── chunking.py          # 文本分块策略
│   └── cleanup.py           # 过期清理服务
│
├── models/                  # 数据模型
│   └── data_models.py       # 数据结构定义
│
├── processors/              # 处理模块（解析 + AI）
│   ├── ai_processor.py           # 多厂商AI调用（ANALYSIS/FILTER/BACKUP）
│   ├── content_parser.py         # 内容解析器（合并规则解析+实体抽取）
│   ├── history_relation_engine.py # 历史关联分析引擎（TF-IDF+实体加权）
│   └── chart_data_service.py     # 图表数据聚合层
│
│   # 注：content_parser.py 合并了原 rule_based_parser.py、ai_fallback_extractor.py、
│   #     entity_extractor.py 的功能，提供统一的内容解析接口
│
├── rss/                     # RSS 采集模块
│   ├── collector.py         # RSS 收集器
│   ├── sources.py           # RSS 源管理
│   ├── parser.py            # RSS 解析器
│   ├── api_sources.py       # API数据源
│   └── incremental_collector.py # 增量采集收集器
│
├── storage/                 # 存储模块
│   ├── database.py          # SQLite 数据库管理（WAL+连接池+重试+备份）
│   ├── baseline.py          # 历史数据关联
│   ├── file_manager.py      # 文件存储管理
│   └── storage_manager.py   # 存储管理器
│
├── crawlers/                # 爬虫模块
│   ├── base.py              # 爬虫基类
│   ├── factory.py           # 爬虫工厂
│   ├── xinhua.py            # 新华社爬虫
│   └── people.py            # 人民日报爬虫
│
├── scheduler/               # 调度模块
│   └── task_scheduler.py    # 任务调度器
│
├── utils/                   # 工具模块
│   ├── api_optimizer.py     # API调用优化器
│   ├── chart_generator.py   # 图表生成器
│   ├── collection_config.py # 采集参数配置管理
│   ├── email_sender.py      # 邮件发送
│   ├── errors.py            # 错误定义与处理
│   ├── health_monitor.py    # RSS源健康监控
│   ├── heartbeat.py         # 任务心跳监控
│   ├── http_client.py       # HTTP客户端
│   ├── incremental_tracker.py # 增量采集跟踪
│   ├── log_utils.py         # 日志工具
│   ├── logging_config.py    # 日志配置
│   ├── md2pdf.py            # Markdown 转 PDF
│   ├── performance.py       # 性能监控
│   ├── proxy_config.py      # 代理配置
│   ├── security.py          # 安全与密钥管理
│   ├── task_lock.py         # 任务锁
│   └── text_utils.py        # 文本工具
│
├── scripts/                 # 自动化脚本
│   ├── setup_windows_tasks.bat    # 创建 Windows 任务计划
│   ├── remove_windows_tasks.bat   # 删除 Windows 任务计划
│   ├── run_collect_auto.bat       # 自动采集脚本
│   ├── run_report_auto.bat        # 自动报告脚本
│   ├── run_send_email_auto.bat    # 自动邮件脚本
│   ├── run_collect_and_report.bat # 采集+报告一体化
│   ├── setup_windows_tasks.ps1    # PowerShell任务设置
│   ├── system_check.py            # 系统自检脚本
│   ├── check_env.py               # 环境检查工具
│   ├── check_data.py              # 数据检查工具
│   ├── check_news_time.py         # 新闻时间检查工具
│   ├── repair_db.py               # 数据库修复
│   ├── db_manager.py              # 数据库管理
│   ├── import_sql.py              # SQL导入
│   ├── export_and_rebuild.py      # 导出重建
│   ├── migrate_schema.py          # Schema迁移
│   ├── migrate_to_sqlite.py       # SQLite迁移
│   ├── backfill_domain.py         # 领域回填
│   ├── fix_domain_labels.py       # 修复领域标签
│   ├── domain_classifier.py       # 领域分类器
│   ├── recheck_pending_news.py    # 重检待处理新闻
│   ├── generate_daily_stats.py    # 生成每日统计
│   ├── test_persistence.py        # 持久化测试（云部署）
│   ├── health_check.py            # 健康检查（云部署）
│   ├── auto_backup.py             # 自动备份服务（云部署）
│   ├── restore_backup.py          # 备份恢复工具（云部署）
│   └── deploy.sh                  # 部署脚本（云部署）
│
├── tests/                   # 测试模块
│   ├── conftest.py          # 全局测试配置和fixtures
│   ├── unit/                # 单元测试（快速、隔离）
│   │   ├── test_database.py # 数据库模块测试
│   │   ├── test_config.py   # 配置模块测试
│   │   └── test_utils.py    # 工具模块测试
│   ├── integration/         # 集成测试（需要外部资源）
│   │   ├── test_ai_processor.py # AI处理器测试
│   │   ├── test_filters.py  # 过滤器测试
│   │   ├── test_rss.py      # RSS模块测试
│   │   ├── test_report.py   # 报告生成测试
│   │   └── test_history_relation.py # 历史关联测试
│   ├── e2e/                 # 端到端测试（预留）
│   ├── fixtures/            # 测试数据和fixtures
│   │   └── sample_data.py   # 示例数据工厂
│   ├── test_smart_backtrack.py # 智能回溯测试
│   └── README.md            # 测试文档
│
├── data/                    # 数据目录（不提交）
│   ├── news.db              # SQLite 数据库
│   ├── backups/             # 数据库自动备份
│   ├── archive/             # 归档数据
│   ├── locks/               # 任务锁文件
│   └── knowledge_base/      # 知识库数据
│       └── chroma/          # ChromaDB向量存储
│
├── logs/                    # 日志目录（不提交）
├── reports/                 # 报告输出目录（不提交）
│
├── task1_collector.py       # 任务1：新闻采集入口
├── task2_reporter.py        # 任务2：报告生成入口
├── run_collect.py           # 采集入口脚本
├── run_report.py            # 报告生成入口
├── run_now.py               # 一键运行脚本
├── send_email.py            # 邮件发送入口
├── restore_db_simple.py     # 数据库恢复工具
│
├── Dockerfile               # Docker 容器构建配置（云部署）
├── docker-compose.yml       # Docker 编排配置（云部署）
├── .dockerignore            # Docker 构建排除文件（云部署）
├── requirements.lock        # 依赖版本锁定文件（云部署）
│
├── .env                     # 环境变量配置（不提交）
├── .env.example             # 环境变量示例
├── sources.yaml             # RSS 源配置
├── requirements.txt         # Python 依赖
├── pytest.ini               # 测试配置
└── README.md                # 项目说明
```

---

## 数据架构

### SQLite 数据库

项目使用 SQLite 数据库存储所有新闻数据，采用 WAL 模式保障并发安全：

```
data/news.db
├── news 表              # 所有新闻（永久保留）
│   ├── 基本信息：标题、链接、来源、发布时间
│   ├── 5W1H分析：何人、何事、何时、何地、何因、如何
│   ├── 分类标签：领域、标签、关键词
│   ├── 评分：综合评分、各维度评分
│   └── 解析溯源：source_reliability_score / extraction_method / access_time
│
├── processed_news 表    # 已处理新闻ID（去重用）
│
├── entities 表          # 实体库（知识图谱预留）
│                        # 第二阶段填充：人名、机构、地点、技术、事件
│
├── news_entities 表     # 新闻-实体关联（知识图谱预留）
│
├── rejected_news 表     # 被拒绝新闻（AI过滤记录）
│
├── event_clusters 表    # 事件聚类结果
│
└── knowledge_index 表   # 知识库索引跟踪
```

**连接池与健壮性**：
- `ConnectionPool` 单例管理连接复用
- 所有写操作通过 `_execute_with_retry` 自动重试（最多3次，指数退避）
- 每次采集任务结束后自动备份至 `data/backups/`（可通过 `ENABLE_DB_BACKUP=false` 关闭）

### 知识库 (RAG)

项目已实现完整的知识库系统，基于 ChromaDB 构建本地向量存储，支持 RAG（检索增强生成）：

```
data/knowledge_base/
├── chroma/              # ChromaDB 向量存储
│   └── news_articles/   # 新闻向量集合
│
└── 知识库模块 (knowledge/)：
    ├── base.py              # 知识库基类
    ├── chroma_store.py      # ChromaDB存储实现
    ├── embedding.py         # 向量化服务（Sentence-Transformers）
    ├── retriever.py         # RAG检索器
    ├── pipeline.py          # 向量化Pipeline
    ├── chunking.py          # 文本分块策略
    └── cleanup.py           # 过期清理服务
```

**功能特性**：
- ✅ **新闻向量化存储**：自动将新闻全文转换为向量并存储
- ✅ **语义检索**：基于向量相似度检索相关原文
- ✅ **RAG增强报告生成**：检索结果注入AI prompt，解决幻觉问题
- ✅ **分块策略**：智能文本分块，优化检索效果
- ✅ **自动清理**：定期清理过期向量数据

**配置**：通过 `config/knowledge.yaml` 配置知识库参数。

### 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                        任务1：新闻采集                           │
├─────────────────────────────────────────────────────────────────┤
│  RSS采集 → 白名单校验 → 可信度校验 → 历史去重 → 内容清理        │
│     ↓                                                           │
│  规则解析中间层（RuleBasedParser）                               │
│    ├─ YAML规则命中 → 领域/标签（confidence ≥ 阈值）             │
│    └─ 规则不足 → AI兜底（ENABLE_AI_TAG_FALLBACK=true 时启用）   │
│     ↓                                                           │
│  AI批处理（5W1H检测 + 翻译 + 评分）                              │
│    └─ 领域优先级：规则命中 > RSS推断 > AI推断                   │
│     ↓                                                           │
│  存入 SQLite 数据库（含 extraction_method 字段）                 │
│     ↓                                                           │
│  ✅ 向量化存储到知识库（ChromaDB）                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        任务2：报告生成                           │
├─────────────────────────────────────────────────────────────────┤
│  读取待分析池 → 最终去重 → 生成简要摘要报告                      │
│     ↓                                                           │
│  ✅ RAG检索相关原文 → 注入prompt                          │
│     ↓                                                           │
│  加载历史新闻（近90天）→ 历史关联分析（实体/标签/领域）          │
│     ↓                                                           │
│  生成深度分析报告（政治/经济/科技）                              │
│     ↓                                                           │
│  邮件推送（简要版正文 + 深度版PDF附件）                          │
└─────────────────────────────────────────────────────────────────┘
```

### 查询示例

```python
from storage.database import NewsDatabase

db = NewsDatabase()

# 查询最近24小时新闻
recent_news = db.get_recent_news(hours=24)

# 查询最近90天新闻（历史关联分析）
history_news = db.get_history_news(days=90)

# 按领域查询
economy_news = db.search_by_domain('经济', hours=24)

# 数据库统计
stats = db.get_stats()
```

---

## 安全说明

- ⚠️ **切勿将 `.env` 提交到 Git**
- 所有密钥通过环境变量或 GitHub Secrets 配置
- `.env` 已在 `.gitignore` 中排除
- 日志输出已脱敏处理，不输出敏感信息

---

## 许可证

MIT License
