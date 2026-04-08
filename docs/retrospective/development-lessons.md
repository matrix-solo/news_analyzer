# 新闻分析系统开发经验与教训

> **文档目的**：基于 news_analyzer 项目的完整开发周期，提取可复用的工程经验，指导未来项目开发
> **编写日期**：2026-04-09
> **适用范围**：任何涉及 CI/CD 自动化、AI 调用、数据处理管道的项目

---

## 目录

1. [第一性原理：什么导致了问题积累](#1-第一性原理什么导致了问题积累)
2. [架构设计：哪些决策经住了考验](#2-架构设计哪些决策经住了考验)
3. [架构设计：哪些决策埋下了隐患](#3-架构设计哪些决策埋下了隐患)
4. [CI/CD 工程清单](#4-cicd-工程清单)
5. [代码层面的防御性设计](#5-代码层面的防御性设计)
6. [测试策略反思](#6-测试策略反思)
7. [未来项目开发检查清单](#7-未来项目开发检查清单)

---

## 1. 第一性原理：什么导致了问题积累

### 1.1 根因不是 Bug，是系统性缺失

2026-04-09 一次 CI 日志排查发现了 7 个问题（其中 4 个阻断工作流）。逐个看都是"小 Bug"，但背后是三个系统性缺陷：

**缺陷一：开发环境与运行环境从未对齐**

| 问题 | 开发环境表现 | CI 环境表现 |
|------|-------------|-------------|
| 代理硬编码 `127.0.0.1:7890` | 本地有代理，正常运行 | 无代理，所有原文获取失败 |
| `.gitignore` 包含 `reports/` | 本地不需要 git add | CI 归档步骤 `git add reports/archive/` 失败 |
| 静态缓存 key | 本地数据持久 | CI cache hit 后永不更新，数据丢失 |

**本质**：代码在开发机上能跑 ≠ 代码在目标环境上能跑。项目缺少一个"环境一致性"检查机制。

**缺陷二：诊断工具变成了守门人**

`cache_health_check.py` 的设计目的是"采集后检查数据健康度"。但它以 exit code 1 退出，直接阻断了后续的报告生成和邮件发送。一个诊断工具变成了一票否决。

更深层的问题是：阈值 100 没有数据支撑。随着项目运行，`raw_news` 自然积累到 575 条，触发了这个拍脑袋定的阈值。

**本质**：诊断和执行没有解耦。诊断发现问题应该是"报告"，而不是"停机"。

**缺陷三：守卫只防了前门**

熔断器在 `process_batch()` 中正确实现，但 `process_news()` 没有同样的守卫。批处理阶段熔断器跳闸后，重试阶段从另一个入口绕进来逐条调用 LLM，572 条全部白跑。

**本质**：当系统有多个入口调用同一个关键资源时，守卫必须在资源层统一实现，而不是在每个调用方单独实现。

### 1.2 这三个缺陷的共同模式

```
缺失的不是代码，而是对"边界"的思考：
- 开发环境与目标环境的边界 → 环境一致性
- 诊断与执行的边界 → 职责分离
- 接口入口与资源层的边界 → 统一守卫
```

---

## 2. 架构设计：哪些决策经住了考验

### 2.1 多 Provider AI 调用体系

```
环境变量命名：AI_<PURPOSE>_<TYPE>
  例：AI_FILTER_PROVIDER=doubao, AI_ANALYSIS_PROVIDER=deepseek

调用链：请求目的 → 主 Provider → BACKUP Provider → 默认值兜底
```

**为什么好**：
- 用途驱动（FILTER/ANALYSIS/BACKUP）而非 Provider 驱动，切换模型只改环境变量
- `TokenLimitExceeded` 不触发熔断器（预算问题 ≠ 服务故障），而是走 BACKUP
- `TokenCounter` 持久化到磁盘，CI 缓存可共享用量状态

### 2.2 合并处理（CombinedProcessor）设计

将翻译、摘要、5W1H 提取、评分合并为**一次 LLM 调用**，而非 4 次独立调用。

**为什么好**：
- API 调用量降为 1/4，成本和延迟同步降低
- 结果在同一个上下文中生成，字段间一致性更好
- 失败时整体回退到默认值，不会出现"翻译成功但评分缺失"的中间态

### 2.3 降级策略的清晰分层

```
主 Provider 失败 → BACKUP Provider → _default_result() 返回安全默认值 → 数据标记为 force_stored
```

每一层都有明确的职责和退出条件，不存在无限重试。`_default_result()` 提供完整但保守的结果结构，保证下游不会因为字段缺失而崩溃。

### 2.4 配置的三层分离

| 层级 | 内容 | 变更频率 |
|------|------|---------|
| `.env` | 密钥、API Key、模型选择 | 每次部署 |
| `*.yaml` | RSS 信源、评分权重、解析规则 | 迭代时调整 |
| `DefaultValues` 类 | 代码中的默认常量 | 极少变更 |

这种分离让敏感信息不进版本控制，结构配置可版本追踪，代码默认值有据可查。

### 2.5 可观测性设计

- `HeartbeatMonitor`：任务级心跳，可检测"采集卡住"
- `WorkflowTimer`：每个阶段的精确耗时，JSON 持久化
- `CombinedProcessor` JSONL 日志：每次 LLM 调用的输入摘要、输出、耗时、token 数
- `task_lock`：跨平台文件锁，防止 Windows 定时任务和 CI 同时运行

这些不是"锦上添花"，是排查问题时唯一的线索来源。本次 CI 问题排查能快速定位，就是靠 `WorkflowTimer` 的阶段耗时和 `CombinedProcessor` 的 CRITICAL 日志。

---

## 3. 架构设计：哪些决策埋下了隐患

### 3.1 入口文件过于庞大

`task1_collector.py` 1737 行，单个 `Task1NewsCollector` 类承担了 12 个阶段的编排。

**问题**：
- `_collect_from_sources()` 290 行，嵌套 4 层 try/except
- `_store_batch_to_database()` 185 行，大量字段映射逻辑
- 任何阶段的小改动都需要理解整个类的上下文

**教训**：每个阶段应该是一个独立的策略对象，由一个轻量编排器调度。当前架构已经按职责拆分了模块（FieldNormalizer、HeatProcessor 等），但编排逻辑仍然耦合在入口类中。

### 3.2 单例过多且无统一重置机制

项目中有 5+ 个单例（ConfigManager、ConnectionPool、HeartbeatMonitor、TokenCounter、AIProcessor），但没有统一的单例管理器或测试重置协议。

**后果**：
- 测试之间可能共享状态（数据库连接未关闭、配置未重置）
- `reset_database_singleton()` 等重置函数散落在各处
- 新增单例时容易忘记写重置逻辑

**教训**：如果项目需要单例，应该用依赖注入容器或注册表模式统一管理，而不是每个单例自己实现。

### 3.3 自定义异常体系存在但未被使用

`error_handling.py` 定义了 `NewsAnalyzerError`、`ConfigurationError`、`NetworkError` 等异常层级，但实际代码中 90% 的地方用的是 `except Exception`。

**后果**：
- 无法按异常类型做差异化处理（比如只对 NetworkError 重试）
- 熔断器只能靠 HTTP 状态码判断是否致命，而非异常类型
- 日志中丢失了结构化的错误分类

**教训**：定义了异常体系就要在入口层统一转换。可以在 LLM 调用的最低层把 HTTP 错误包装为 `AIServiceError`、`AIRateLimitError`、`AIBillingError`，让上层用异常类型而非字符串匹配做决策。

### 3.4 两种 HTTP 客户端并存

`requests`（同步）和 `httpx`（异步）同时出现在项目中。`article_fetcher.py` 用 `requests`，`unified_collector.py` 也用 `requests`，但 `http_client.py` 同时封装了两者。

**后果**：
- `article_fetcher.py` 自己处理代理逻辑，不走 `http_client.py` 的智能分流
- 这次代理硬编码的 Bug 就是因为 `article_fetcher.py` 绕过了统一的 HTTP 客户端

**教训**：对外 HTTP 调用应该统一走一个客户端模块。如果性能需要异步，可以在统一客户端中同时提供同步和异步接口。

---

## 4. CI/CD 工程清单

### 4.1 本次修复的 8 个问题总览

| # | 问题 | 根因分类 | 严重程度 | 影响 |
|---|------|---------|---------|------|
| 1 | 代理硬编码 127.0.0.1:7890 | 环境泄漏 | 严重 | CI 原文获取 100% 失败 |
| 2 | 静态缓存 key 导致数据不持久 | 缓存设计 | 严重 | CI 每次从旧数据开始 |
| 3 | .gitignore 阻止报告归档 | 配置冲突 | 中等 | 归档步骤失败 |
| 4 | send_email.yml 缺少权限 | 权限配置 | 中等 | 备用邮件无法发送 |
| 5 | 健康检查阻断主流程 | 职责混淆 | 严重 | 报告和邮件全部跳过 |
| 6 | recipients=[] 阻止通知邮件 | 代码笔误 | 低 | 无新闻时无法通知 |
| 7 | process_news 缺少熔断器守卫 | 接口一致 | 严重 | 572 次无效 LLM 调用 |
| 8 | Cron 时区偏差 1 小时 | 文档未校验 | 中等 | 主任务在 8:00 而非 7:00 运行 |

### 4.2 CI 防护规则

以下规则应在任何新项目的 CI 配置中强制执行：

```
规则 1：代码中的网络默认值必须为空
  - 代理、超时、重试等参数，默认值应为 None 或空字符串
  - 仅通过环境变量启用，CI 通过 workflow 注入
  
规则 2：诊断步骤不能阻断主流程
  - 所有健康检查、诊断脚本必须设置 continue-on-error: true
  - 阈值必须有数据支撑，不能拍脑袋定
  
规则 3：缓存 key 必须动态
  - 含可变数据的缓存用 ${{ github.run_id }} 后缀
  - restore-keys 用前缀匹配确保恢复最新数据
  
规则 4：代码与文档必须交叉校验
  - 改 cron / 配置时，必须同步校验 README 和所有文档
  - CI 注释中的时间转换必须二次确认（UTC + 8 = 北京时间）
  
规则 5：工作流权限必须显式声明
  - 每个 workflow 必须有 permissions 块
  - 只授予最小权限（contents: write, actions: read 等）
  
规则 6：.gitignore 不能与工作流操作冲突
  - 如果 CI 需要 git add 某个目录，该目录不能被 .gitignore 完全排除
  - 用 path/* + !path/subdir/ 模式做精确控制
```

---

## 5. 代码层面的防御性设计

### 5.1 统一守卫原则

**反面案例**（本项目）：
```python
# process_batch() 有熔断器检查
def process_batch(self, news_list):
    if self._circuit_open:  # ← 守卫在这里
        return [(news, None, 0.0) for news in news_list]
    ...

# process_news() 没有熔断器检查
def process_news(self, news):  # ← 守卫缺失
    raw = self._provider.chat(...)  # 直接调用，熔断器无效
```

**正确模式**：守卫在资源层，不在调用方
```python
def _call_llm(self, messages, **kwargs):
    """所有 LLM 调用的统一入口"""
    if self._circuit_open:
        raise CircuitOpenError()
    try:
        result = self._provider.chat(messages, **kwargs)
        self._on_success()
        return result
    except FatalError as e:
        self._on_failure(e)
        raise
```

**原则**：如果一个保护机制需要在 N 个入口分别实现，那它一定会被遗漏。把守卫放在最底层。

### 5.2 环境变量的默认值策略

**反面案例**：
```python
PROXY_URL = os.getenv('RSS_HTTP_PROXY', 'http://127.0.0.1:7890')
```

开发机上有这个代理所以没问题，但 CI 上没有。硬编码的默认值意味着"所有环境都应该有这个代理"，这是不成立的假设。

**正确策略**：
```python
# 环境相关配置：默认关闭，通过环境变量开启
PROXY_URL = os.getenv('RSS_HTTP_PROXY', '')  # 默认直连
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')    # 默认合理值

# 业务逻辑配置：可以在代码中有合理默认值
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '4'))  # 默认 4 条/批
```

**原则**：
- **环境相关**（代理、密钥、路径）：默认关闭/空值
- **业务逻辑**（批次大小、阈值）：可以有合理默认值
- **密钥类**：无默认值，缺失时明确报错

### 5.3 降级路径的完整性

本项目的降级设计是一个好的参考模型：

```
主 Provider → BACKUP Provider → 安全默认值 → 数据标记（force_stored）
```

每一步都保证下游不崩溃。但有一个隐含要求：**安全默认值必须是一个完整的结构**，不能是 None。

```python
# 正确：返回完整的默认结构
def _default_result(self, news):
    return {
        'translation': news.get('title', ''),
        'summary': news.get('description', ''),
        'domain': '社会',
        'score': DefaultValues.SCORE_DEFAULT,
        ...  # 所有下游需要的字段都有值
    }
```

---

## 6. 测试策略反思

### 6.1 当前状态

项目有完善的测试基础设施（conftest.py、pytest markers、fixture），但实际测试覆盖率很低：

- 单元测试只有 4 个基础配置测试
- 没有针对 `Task1NewsCollector` 或 `Task2DailyReporter` 的单元测试
- 集成测试依赖外部服务，CI 中不运行
- 本次发现的 8 个 CI 问题，**没有任何一个能被现有测试捕获**

### 6.2 哪些测试最有价值

按"防止本次问题再次发生"的价值排序：

**P0：CI 集成测试（防止环境差异）**
- 一个轻量的端到端测试脚本，验证：数据库创建 → 1 条新闻处理 → 报告生成
- 不调用真实 API，用 mock，但验证完整链路
- 在 CI 中作为独立步骤运行

**P1：配置一致性测试（防止文档与代码不同步）**
```python
def test_cron_matches_documentation():
    """CI cron 时间必须与 README 中声明的一致"""
    import yaml
    workflow = yaml.safe_load(open('.github/workflows/collect.yml'))
    crons = [s['cron'] for s in workflow['on']['schedule']]
    # 北京时间 07:00 = UTC 23:00
    assert '0 23 * * *' in crons
```

**P2：模块接口契约测试（防止守卫遗漏）**
```python
def test_circuit_breaker_guards_all_entry_points():
    """所有公开处理方法必须在熔断器开启时返回安全默认值"""
    processor = CombinedProcessor()
    processor._circuit_open = True
    
    result, score = processor.process_news({'title': 'test'})
    assert score == 0.0  # 不应抛异常
    
    results = processor.process_batch([{'title': 'test'}])
    assert len(results) == 1
    assert results[0][2] == 0.0  # 不应抛异常
```

### 6.3 测试策略原则

```
1. 测试"集成点"而非"实现细节"
   - 不测 CombinedProcessor 内部的 JSON 解析
   - 测"熔断器开时，所有公开方法都安全返回"

2. 测试"环境假设"而非"功能逻辑"
   - 不测"数据库能插入数据"
   - 测".env 缺失密钥时系统能优雅降级"

3. 测试"文档与代码的一致性"
   - 不测"cron 语法是否正确"
   - 测"cron 时间是否与 README 声明的一致"
```

---

## 7. 未来项目开发检查清单

### 7.1 项目启动时

- [ ] 明确目标运行环境列表（本地开发、CI、生产服务器）
- [ ] 为每个环境准备 `.env.example` 模板，注释中标注哪些是必须的
- [ ] 设计配置的三层分离策略（密钥 / 结构配置 / 代码默认值）

### 7.2 架构设计时

- [ ] 关键资源（LLM、数据库、网络）的调用是否有统一入口？
- [ ] 守卫机制（熔断器、限流、锁）是否在最底层实现？
- [ ] 降级路径的每一步是否都能提供完整的数据结构？
- [ ] 是否有"诊断 vs 执行"的职责分离？

### 7.3 编码时

- [ ] 环境相关的默认值是否为空/None（代理、密钥、路径）？
- [ ] 新增的 HTTP 调用是否走统一的客户端模块？
- [ ] 异常是否使用了自定义异常类型而非裸 `Exception`？
- [ ] 单例是否有对应的测试重置机制？

### 7.4 CI/CD 配置时

- [ ] 工作流权限是否显式声明了 `permissions` 块？
- [ ] 缓存 key 是否动态（不会因为 cache hit 导致数据丢失）？
- [ ] `.gitignore` 是否与 CI 操作（git add/push）冲突？
- [ ] 诊断/检查步骤是否设置了 `continue-on-error: true`？
- [ ] Cron 时间是否与项目文档交叉校验过？

### 7.5 发布前

- [ ] 是否在目标环境（CI）做过端到端验证？
- [ ] 代码中的阈值是否有数据支撑？
- [ ] 新增模块的 import 路径是否在 CI 环境中可用？

---

## 附录 A：关于提示词工程的思考

本项目开发过程中积累了一条提升 AI 开发助手输出质量的系统性提示词：

> 你是一个顶尖产品开发与代码设计专家，第一性原理思考者，擅长从万物基本原理和常识出发，推演做事思路...

这条提示词解决的问题是"提高 AI 对任务的注意力"，但它只覆盖了单次交互的质量。

从本次复盘可以看出，真正需要系统化思考的是**项目层面**的问题：

1. **环境一致性**：AI 助手默认在"开发环境"假设下工作，不会主动思考"CI 上会怎样"
2. **边界识别**：AI 助手擅长修复点状问题，但不擅长识别"三个 Bug 共享同一个根因"
3. **文档校验**：AI 助手改了代码后不会主动检查"文档是不是也要同步更新"

**建议**：在项目的 CLAUDE.md 或类似文件中加入以下指令，让 AI 助手在每次修改代码时自动检查：

```markdown
## 代码修改检查规则

1. 修改涉及网络/代理/路径时：检查默认值是否为空，是否通过环境变量配置
2. 修改涉及 CI workflow 时：同步校验 README 和所有文档中的时间/配置描述
3. 修改涉及 .gitignore 时：检查是否与 CI 的 git add/push 操作冲突
4. 新增调用 LLM/数据库的入口时：检查是否通过统一守卫（熔断器/重试/连接池）
5. 修改涉及阈值时：确认阈值有数据支撑，并评估对 CI 的影响
```

这种"把检查规则固化到项目上下文中"的思路，比在每次对话中重复提醒更可靠。它让 AI 助手的注意力从"单次回答的质量"扩展到了"项目级的一致性维护"。
