# 测试文档

## 测试架构

```
tests/
├── conftest.py              # 全局配置和fixtures
├── unit/                    # 单元测试（快速、隔离）
│   ├── test_database.py     # 数据库模块测试
│   ├── test_config.py      # 配置模块测试
│   └── test_utils.py       # 工具模块测试
├── integration/             # 集成测试（需要外部资源）
│   ├── test_ai_processor.py           # AI处理器测试
│   ├── test_bge3_engine.py           # BGE-M3引擎测试
│   ├── test_bge3_threshold_analysis.py # BGE-M3阈值分析测试
│   ├── test_data_validator.py         # Step 9 数据校验测试
│   ├── test_embedding.py              # Step 7 向量化生成测试
│   ├── test_filters.py                # 过滤器测试
│   ├── test_heat_processor.py         # Step 8 热度评分测试
│   ├── test_history_relation.py       # 历史关联测试
│   ├── test_report.py                 # 报告生成测试
│   ├── test_rss.py                    # RSS采集测试
│   └── test_task2_reporter.py         # Task2 报告生成测试
├── e2e/                     # 端到端测试（完整流程）
│   └── __init__.py
├── fixtures/                # 测试数据和fixtures
│   ├── __init__.py
│   └── sample_data.py      # 示例数据工厂
└── README.md               # 本文档
```

## 测试分类

### 单元测试 (unit/)
- **特点**：快速执行、完全隔离、无外部依赖
- **运行**：`pytest tests/unit/ -v`
- **测试数量**：32 tests

### 集成测试 (integration/)
- **特点**：需要外部资源或服务、执行时间较长
- **运行**：`pytest tests/integration/ -v`
- **测试数量**：~150 tests

### 端到端测试 (e2e/)
- **特点**：完整流程测试、模拟真实使用场景
- **运行**：`pytest tests/e2e/ -v`
- **当前状态**：目录存在，待实现

## 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行特定测试文件
pytest tests/unit/test_database.py -v

# 运行特定测试类
pytest tests/unit/test_database.py::TestNewsDatabase -v

# 运行特定测试方法
pytest tests/unit/test_database.py::TestNewsDatabase::test_insert_news -v

# 排除慢速测试
pytest -m "not slow"

# 只运行单元测试
pytest -m unit

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

## 测试标记

| 标记 | 说明 | 使用场景 |
|------|------|----------|
| `@pytest.mark.unit` | 单元测试 | 快速、隔离的测试 |
| `@pytest.mark.integration` | 集成测试 | 需要外部资源的测试 |
| `@pytest.mark.e2e` | 端到端测试 | 完整流程测试 |
| `@pytest.mark.slow` | 慢速测试 | 执行时间 > 5秒 |
| `@pytest.mark.requires_api` | 需要API密钥 | 需要 API 调用的测试 |

## 测试覆盖

### Task1 采集入库流程 (10步)

| Step | 流程 | 测试覆盖 | 测试文件 |
|------|------|----------|----------|
| Step 1 | 全信源新闻采集 | ✅ | test_rss.py |
| Step 2 | 字段规范化 | ✅ | test_utils.py |
| Step 3 | 存储原始数据 | ✅ | test_database.py |
| Step 4 | 轻量级初筛 | ✅ | test_filters.py |
| Step 5 | 基础三层过滤 | ✅ | test_filters.py |
| Step 6 | 三阶段合并处理 | ✅ | test_ai_processor.py |
| **Step 7** | **向量化生成** | **✅ 完整** | **test_embedding.py** |
| **Step 8** | **热度评分** | **✅ 完整** | **test_heat_processor.py** |
| **Step 9** | **数据完整性校验** | **✅ 完整** | **test_data_validator.py** |
| Step 10 | 批量存入数据库 | ✅ | test_database.py |

### Task2 报告生成流程

| 阶段 | 流程 | 测试覆盖 | 测试文件 |
|------|------|----------|----------|
| 阶段1 | 从DB读取近24小时新闻 | ✅ | test_task2_reporter.py |
| 阶段2 | 获取新闻列表 | ✅ | test_task2_reporter.py |
| 阶段3 | 生成简要摘要报告 | ✅ | test_task2_reporter.py |
| 阶段4 | 生成深度分析报告 | ✅ | test_task2_reporter.py |
| 阶段5 | 选择TOP N | ✅ | test_task2_reporter.py |
| 阶段6 | 发送邮件 | ✅ | test_task2_reporter.py |

## 集成测试详情

### test_embedding.py (Step 7 向量化生成)

| 测试类 | 测试数 | 测试项 |
|--------|--------|--------|
| TestEmbeddingDetection | 3 | 检测无/有 embedding 的新闻、过滤需要生成向量的新闻 |
| TestEmbeddingGeneration | 4 | 编码返回 numpy 数组、归一化、空字符串、模型失败 |
| TestBatchEmbeddingGeneration | 2 | 批量编码、跳过已有 embedding |
| TestEmbeddingStorage | 3 | 向量序列化/反序列化、维度 |
| TestEmbeddingIntegration | 1 | 完整 embedding 工作流 |

### test_heat_processor.py (Step 8 热度评分)

| 测试类 | 测试数 | 测试项 |
|--------|--------|--------|
| TestScoreCalculation | 7 | 无匹配、单平台、多平台评分计算 |
| TestKeywordHeat | 3 | 关键词热度计算 |
| TestSimThreshold | 1 | 相似度阈值配置 |
| TestCalculateHeatScore | 3 | 热度评分方法测试 |
| TestBatchProcessing | 3 | 批量处理测试 |
| TestProcessorBuild | 2 | 处理器构建测试 |
| TestNewsWithEmbedding | 1 | 带 embedding 的新闻测试 |
| TestFallback | 2 | 降级策略测试 |

### test_data_validator.py (Step 9 数据校验)

| 测试类 | 测试数 | 测试项 |
|--------|--------|--------|
| TestValidationRules | 12 | 翻译/摘要/分析/评分/领域验证 |
| TestCombinedValidation | 3 | 组合验证测试 |
| TestAIRemediation | 4 | AI补救机制测试 |
| TestDefaultValues | 1 | 默认值填充测试 |
| TestValidDomains | 2 | 有效领域测试 |

### test_task2_reporter.py (Task2 报告生成)

| 测试类 | 测试数 | 测试项 |
|--------|--------|--------|
| TestSelectTopN | 4 | TOP N 选择逻辑 |
| TestChinaNewsClassification | 2 | 中外国新闻分类 |
| TestReportScoring | 3 | 评分计算 |
| TestReportDateHandling | 2 | 日期处理 |
| TestNotificationLogic | 2 | 通知逻辑 |
| TestReportGeneratorIntegration | 2 | 报告生成器集成 |
| TestReportFilePaths | 3 | 文件路径测试 |

### 其他集成测试

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|----------|
| test_ai_processor.py | 17 | Provider配置、AI处理器、重试机制 |
| test_filters.py | 15 | 去重过滤、相似度计算、标题标准化 |
| test_rss.py | 12 | RSS解析、源管理、采集 |
| test_history_relation.py | 14 | 实体提取、历史关联、相似度匹配 |
| test_report.py | 9 | 报告生成器、简要报告、报告格式 |
| test_bge3_threshold_analysis.py | 9 | BGE-M3阈值分析 |
| test_bge3_engine.py | 1 | BGE-M3引擎（当前跳过） |

### 单元测试

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|----------|
| test_database.py | 9 | 数据库初始化、插入、去重、批量操作 |
| test_config.py | 12 | 环境配置、Provider配置、配置验证 |
| test_utils.py | 11 | 文本处理、标签格式、JSON解析 |

## 测试数据

使用 `tests/fixtures/sample_data.py` 提供的数据工厂：

```python
from tests.fixtures.sample_data import (
    create_news_item,
    create_news_list,
    create_ai_response,
    SAMPLE_NEWS_POLITICAL,
    SAMPLE_NEWS_ECONOMIC,
    SAMPLE_NEWS_TECH
)

# 创建单个新闻条目
news = create_news_item(title="测试标题", domain="政治")

# 创建新闻列表
news_list = create_news_list(count=10)

# 使用预设数据
news = SAMPLE_NEWS_POLITICAL
```

## 编写测试

### 测试命名规范

- 文件名：`test_<模块名>.py`
- 类名：`Test<功能名>`
- 方法名：`test_<具体功能>_<场景>`

### 示例

```python
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestMyModule:
    """模块测试"""

    @pytest.fixture
    def sample_data(self):
        """测试数据"""
        return {"key": "value"}

    def test_function_success(self, sample_data):
        """测试成功场景"""
        assert sample_data["key"] == "value"

    def test_function_failure(self):
        """测试失败场景"""
        with pytest.raises(ValueError):
            raise ValueError("expected error")
```

## 常见问题

### Q: 数据库测试失败怎么办？

A: 确保使用 `isolated_db` fixture，它会为每个测试创建独立的临时数据库。

### Q: 如何跳过需要API的测试？

A: 使用 `@pytest.mark.skipif` 或运行时排除：
```bash
pytest -m "not requires_api"
```

### Q: 如何查看测试覆盖率？

A: 安装 pytest-cov 并运行：
```bash
pip install pytest-cov
pytest --cov=. --cov-report=html
```

### Q: 测试总数是多少？

A: 当前共 **206** 个测试（排除 bge3_engine 跳过1个）

| 类别 | 测试数 |
|------|--------|
| 单元测试 | 32 |
| 集成测试 | ~150 |
| 其他测试 | 19 |
| **总计** | **206** |
