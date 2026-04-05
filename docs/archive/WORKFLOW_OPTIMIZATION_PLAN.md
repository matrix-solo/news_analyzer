# 工作流优化方案 - 基于第一性原理

## 一、当前工作流分析

### 当前Task1采集工作流
1. **阶段1：全信源新闻采集**
   - 从RSS源获取新闻数据
   - 规则解析（领域/标签）
   - 增量采集过滤

2. **阶段2：基础三层过滤**
   - 白名单校验
   - 可信度校验
   - 历史去重
   - 垃圾内容清理

3. **阶段3：AI内容属性校验**
   - 5W1H检测
   - 翻译（所有新闻）
   - 摘要生成
   - 领域/标签分类
   - 评分

4. **阶段4：批量存入数据库**
   - 事务安全存储
   - 实体抽取

5. **阶段5：重新判断"待分类"新闻**
   - 使用高级模型重新判断

### 问题分析
1. **高成本操作前置**：翻译、AI分析等高成本操作在过滤后立即执行，未进行进一步筛选
2. **规则解析覆盖率低**：规则解析仅覆盖约40%的新闻，大量新闻需要AI兜底
3. **翻译成本浪费**：所有新闻都可能被翻译，即使最终被过滤
4. **领域/标签定义与深度分析耦合**：无法前置低成本筛选
5. **字段不一致处理**：不同信源的字段接口名称不一致
6. **评分体系未充分整合**：热榜提取和信源自动赋分未在工作流中明确体现
7. **数据完整性校验不足**：缺乏系统性的数据完整性校验机制
8. **热榜匹配问题**：中文热榜无法与未翻译的外文新闻匹配

## 二、优化方案设计

### 核心原则
- **低成本操作前置，高成本操作后置**
- **最小化昂贵资源（LLM）的使用**
- **多语言支持**：利用多语言模型直接处理原文
- **模块解耦**：每一步可独立优化
- **数据完整性**：确保所有字段正确填写，无空值

### 优化后工作流

1. **阶段1：采集新闻**
   - 从RSS/API获取原始数据
   - 成本：极低

2. **阶段2：接口解析**
   - 解析原始数据，提取结构化字段
   - 处理HTML标签、编码问题
   - **字段不一致处理**：创建字段映射表，统一字段格式，设置默认值
   - 成本：低（纯规则/解析库操作）

3. **阶段3：存储原始数据**
   - **临时表存储**：创建专门的临时表（如`news_raw`）作为数据源时表库
   - **全量保存**：所有采集的原始数据都存入临时表，不做过滤
   - **数据清理策略**：初期不做定期清理，全量保存数据，观察数据增长情况；当数据量达到一定规模时，再考虑实现自动清理机制
   - 尽早持久化，防止数据丢失
   - 成本：低

4. **阶段4：轻量级初筛**
   - **信源自动赋分**：基于信源可信度和历史表现自动赋分
   - **快速领域分类**：使用多语言轻量级模型（XLM-R）进行快速领域分类和标签预测
   - **分类类别**：采用8分类体系（政治、经济、科技、体育、娱乐、文化、教育、其他）
   - **置信度计算**：由程序语言设计实现，使用模型输出的概率分布计算置信度（取最高概率值作为置信度），设置动态阈值（默认为0.7），低置信度标记为"待AI确认"
   - **置信度检验**：系统会自动记录并评估分类置信度，定期分析置信度分布，调整阈值以优化筛选效果
   - 成本：中（模型推理远低于LLM）

5. **阶段5：三阶段合并处理**
   - **核心优化**：将翻译、摘要、深度分析合并为一次LLM调用
   - 仅对通过初筛且非中文的新闻进行翻译
   - **摘要处理**：必选步骤，保留原始摘要（original_summary），生成系统摘要（system_summary）
   - **深度分析**：5W1H提取、评分、领域标签验证（LLM可更新轻量级分类器的标签）
   - **评分体系**：信源可信度（自动）、影响力评分（AI）、价值评分（AI）、合规评分（AI）
   - 成本：高（但处理量已大幅减少）

6. **阶段6：热榜提取与热度评分**
   - **热榜提取**：获取热榜数据，为评分提供基础
   - **热度评分**：使用翻译后的标题和内容（非中文新闻）或原文（中文新闻）与热榜匹配，计算热度评分
   - 成本：低

7. **阶段7：数据完整性校验**
   - **校验范围**：原始数据完整性、领域标签填写、5W1H字段完整性、评分体系完整性
   - **校验规则**：原始字段不得被覆盖，新增字段必须有值（可填"暂无信息"），综合评分必须由程序计算
   - **异常处理**：
     - **详细记录**：记录具体的校验失败原因，包括字段名称、校验规则及失败详情
     - **AI补救**：对于加工数据类型字段，调用AI补救接口进行自动修复尝试
     - **默认值填充**：若AI补救后数据仍不符合要求，填充预设默认值，并添加"AI补救失败"标记
     - **日志记录**：完整记录处理过程（校验失败原因、AI补救结果、默认值填充操作）到系统运行健康日志
   - **校验报告**：生成详细的校验报告，跟踪校验失败趋势，提供改进建议
   - 成本：低

8. **阶段8：批量存入数据库**
   - **事务安全存储**：使用数据库事务确保数据一致性，支持批量插入和更新
   - **实体抽取**：
     - **命名实体识别**：使用NLP模型（如BERT-based模型）从新闻标题和内容中提取人名、地名、组织机构名等实体
     - **实体分类**：对提取的实体进行分类（人物、地点、组织、事件等）
     - **实体关联**：建立实体之间的关联关系，形成知识图谱
     - **实体存储**：将提取的实体存入专门的实体表，与新闻表建立关联
   - 成本：低

## 三、具体实现方案

### 1. 创建轻量级分类器模块

**文件**：`processors/lightweight_classifier.py`

**核心功能**：
- 加载多语言轻量级模型（XLM-R-tiny/base）
- 对原文进行领域分类和标签预测
- 设置置信度阈值（如0.7）
- 支持批处理，提高效率
- 提供分类置信度评估机制

**实现细节**：
```python
class LightweightClassifier:
    def __init__(self):
        # 加载轻量级多语言模型
        self.model = self._load_model()
        self.tokenizer = self._load_tokenizer()
        self.domain_labels = ['政治', '经济', '科技', '体育', '娱乐', '文化', '教育', '其他']
        self.confidence_threshold = 0.7
        
    def classify_batch(self, news_list):
        # 批量分类新闻
        texts = [news['title'] + ' ' + (news.get('content', '')[:500] or '') for news in news_list]
        # 模型推理
        # 返回分类结果和置信度
        pass
    
    def evaluate_confidence(self, predictions):
        # 计算每个样本的最高概率作为置信度
        confidences = []
        for pred in predictions:
            max_prob = max(pred)
            confidences.append(max_prob)
        return confidences
```

### 2. 创建字段标准化模块

**文件**：`processors/field_normalizer.py`

**核心功能**：
- 统一不同信源的字段格式
- 处理字段缺失情况
- 标准化日期、链接等字段格式
- 基于实际信源字段建立映射关系

**标准化字段**：
- `title`：新闻标题
- `link`：新闻链接
- `description`：新闻描述/摘要
- `pub_date`：发布日期
- `author`：作者
- `category`：分类
- `guid`：唯一标识符
- `source`：信源名称
- `content`：新闻正文

**实现细节**：
```python
class FieldNormalizer:
    def normalize_fields(self, item):
        # 基于实际信源字段建立映射
        field_mapping = {
            'title': ['title', 'headline', 'subject'],
            'link': ['link', 'url'],
            'description': ['description', 'summary'],
            'pub_date': ['pub_date', 'published', 'date', 'pubdate'],
            'author': ['author', 'creator', 'by'],
            'category': ['category', 'tags', 'topic'],
            'guid': ['guid', 'id'],
            'source': ['source', 'from', 'origin'],
            'content': ['content', 'fulltext', 'body']
        }
        
        normalized = {}
        for standard_field, source_fields in field_mapping.items():
            for source_field in source_fields:
                if source_field in item and item[source_field]:
                    normalized[standard_field] = item[source_field]
                    break
            if standard_field not in normalized:
                normalized[standard_field] = None
        
        # 标准化日期格式
        if normalized.get('pub_date'):
            normalized['pub_date'] = self._normalize_date(normalized['pub_date'])
        
        # 处理特殊情况：部分信源使用guid作为链接
        if not normalized.get('link') and normalized.get('guid'):
            normalized['link'] = normalized['guid']
        
        return normalized
```

### 3. 创建三阶段合并处理器

**文件**：`processors/combined_processor.py`

**核心功能**：
- 设计优化的合并处理提示词
- 支持一次调用完成翻译、摘要、深度分析
- 实现准确率评估机制
- 提供兜底处理逻辑
- 支持领域标签更新

**实现细节**：
```python
class CombinedProcessor:
    def __init__(self):
        self.ai_processor = AIProcessor()
        self.analysis_provider = self.ai_processor.get_provider("ANALYSIS")
    
    def process_news(self, news):
        # 构建合并处理提示词
        prompt = self._build_combined_prompt(news)
        # 调用LLM
        response = self.analysis_provider.chat([{"role": "user", "content": prompt}])
        # 解析结果
        result = self._parse_response(response)
        # 评估准确率
        accuracy = self._evaluate_accuracy(result)
        return result, accuracy
    
    def _build_combined_prompt(self, news):
        # 构建包含翻译、摘要、深度分析的提示词
        # 确保包含原始摘要和系统摘要的处理
        pass
    
    def _evaluate_accuracy(self, result):
        """
        评估处理结果的准确率
        1. 完整性评估：检查所有必填字段是否都有值
        2. 一致性评估：检查翻译与原文的一致性
        3. 合理性评估：检查5W1H等分析结果的合理性
        4. 领域标签一致性：检查轻量级分类器和LLM分类结果的一致性
        
        返回0-1之间的准确率分数
        """
        # 完整性评分
        required_fields = ['translation', 'summary', 'analysis', 'scoring']
        completeness_score = sum(1 for field in required_fields if field in result and result[field]) / len(required_fields)
        
        # 一致性评分
        if 'translation' in result and result['translation']:
            # 简单的长度和关键词匹配评估
            consistency_score = 0.8  # 实际实现中需要更复杂的评估
        else:
            consistency_score = 1.0
        
        # 合理性评分
        if 'analysis' in result and result['analysis']:
            # 检查5W1H字段的完整性和合理性
            analysis = result['analysis']
            w5h1_fields = ['who', 'what', 'when', 'where', 'why', 'how']
            w5h1_score = sum(1 for field in w5h1_fields if field in analysis and analysis[field]) / len(w5h1_fields)
        else:
            w5h1_score = 0
        
        # 综合评分
        accuracy = (completeness_score * 0.4 + consistency_score * 0.3 + w5h1_score * 0.3)
        return accuracy
```

### 4. 创建热榜处理器

**文件**：`processors/heat_processor.py`

**核心功能**：
- 获取热榜数据
- 计算新闻热度评分
- 支持多语言新闻与中文热榜的匹配

**实现细节**：
```python
class HeatProcessor:
    def __init__(self):
        self.hotboard_fetcher = get_hotboard_fetcher()
        self.heat_scorer = get_heat_scorer()
    
    def calculate_heat_score(self, news):
        # 获取热榜数据
        hotboard_data = self.hotboard_fetcher.get_all_titles()
        
        # 准备匹配文本
        if news.get('translated_title'):
            match_text = news['translated_title'] + ' ' + (news.get('translated_content', '')[:200] or '')
        else:
            match_text = news['title'] + ' ' + (news.get('content', '')[:200] or '')
        
        # 计算热度评分
        heat_result = self.heat_scorer.calculate_heat_score_for_text(match_text)
        return heat_result.heat_score
```

### 5. 数据完整性校验模块

**文件**：`processors/data_validator.py`

**核心功能**：
- 实现各阶段的校验规则
- 处理校验失败的异常情况
- 记录校验结果和失败原因
- 提供数据补全策略
- 生成校验报告

**实现细节**：
```python
class DataValidator:
    def validate_combined_result(self, news, result):
        # 校验合并处理结果的完整性
        validation_rules = {
            'translation': self._validate_translation,
            'summary': self._validate_summary,
            'analysis': self._validate_analysis,
            'scoring': self._validate_scoring
        }
        # 执行校验
        # 处理校验失败
        # 返回校验结果
        pass
    
    def _validate_analysis(self, result):
        # 校验5W1H字段完整性
        # 对缺失字段填充"暂无信息"
        pass
```

### 6. 调整Task1Collector工作流

**修改文件**：`task1_collector.py`

**关键修改**：
- 在阶段3（存储原始数据）后添加阶段4（轻量级初筛）
- 添加阶段5（三阶段合并处理）
- 添加阶段6（热榜提取与热度评分）
- 添加阶段7（数据完整性校验）
- 调整AI批处理逻辑，仅处理通过初筛的新闻
- 整合信源自动赋分

**工作流调整**：
1. 采集 → 2. 解析（字段标准化） → 3. 存储（临时表全量保存） → 4. 轻量级初筛（信源赋分、快速分类） → 5. 三阶段合并处理 → 6. 热榜提取与热度评分 → 7. 数据完整性校验 → 8. 批量存入数据库

### 7. 数据库结构优化

**修改文件**：`storage/database.py`

**核心功能**：
- 创建临时表（news_raw）用于全量存储原始数据
- 增加初筛状态字段
- 增加合并处理状态字段
- 增加校验状态字段
- 增加摘要相关字段
- 支持批处理和状态跟踪

**数据库字段添加**：
- `initial_domain`：初筛领域
- `initial_tags`：初筛标签
- `classification_confidence`：分类置信度
- `combined_processing_status`：合并处理状态
- `validation_status`：校验状态
- `accuracy_score`：准确率评分
- `original_summary`：原始摘要
- `system_summary`：系统生成摘要
- `source_score`：信源评分
- `heat_score`：热度评分
- `influence_score`：影响力评分
- `value_score`：价值评分
- `compliance_score`：合规评分
- `final_score`：综合评分

## 四、架构图与模块交互

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  阶段1：采集新闻  │────>│  阶段2：接口解析  │────>│  阶段3：存储原始数据 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  阶段8：批量存入  │<────│  阶段7：数据完整性  │<────│  阶段6：热榜提取  │<────│  阶段5：三阶段合并  │
└─────────────────┘     │      校验       │     │  与热度评分     │     │      处理       │
                        └─────────────────┘     └─────────────────┘     └─────────────────┘
                                ^                     │                     │
                                │                     │                     │
                                └─────────────────────┘─────────────────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │  阶段4：轻量级  │
                                             │      初筛       │
                                             └─────────────────┘
```

### 模块交互说明

1. **轻量级分类器** ↔ **Task1Collector**：
   - 输入：原始新闻数据
   - 输出：分类结果和置信度

2. **FieldNormalizer** ↔ **Task1Collector**：
   - 输入：原始字段数据
   - 输出：标准化后的字段数据

3. **CombinedProcessor** ↔ **Task1Collector**：
   - 输入：通过初筛的新闻
   - 输出：翻译、摘要、深度分析结果

4. **HeatProcessor** ↔ **Task1Collector**：
   - 输入：翻译后的新闻
   - 输出：热度评分

5. **DataValidator** ↔ **Task1Collector**：
   - 输入：合并处理和热度评分结果
   - 输出：校验结果和异常处理建议

6. **Task1Collector** ↔ **NewsDatabase**：
   - 输入：校验通过的新闻
   - 输出：存储结果

## 五、性能优化策略

### 1. 批量处理优化
- **轻量级分类器**：批量处理新闻，减少模型加载次数
- **CombinedProcessor**：批量调用LLM，提高处理效率
- **数据库操作**：批量插入和更新，减少数据库连接次数

### 2. 缓存策略
- 缓存轻量级模型的分类结果
- 缓存翻译结果，避免重复翻译
- 缓存LLM调用结果，避免重复处理
- 缓存热榜数据，减少API调用

### 3. 并发处理
- 多线程处理不同源的新闻
- 并行执行轻量级分类和数据存储
- 异步处理LLM调用，提高吞吐量

### 4. 降级策略
- 轻量级分类器失败时，使用关键词匹配作为兜底
- LLM调用失败时，使用备用模型或简化处理
- 系统负载高时，自动调整处理策略，优先处理重要新闻

## 六、预期收益

| 指标 | 预期改善 | 计算依据 |
|------|---------|----------|
| LLM调用量 | 减少67% | 从150次/50条减少到50次/50条 |
| 翻译成本 | 减少67% | 仅翻译通过初筛的新闻，且合并处理 |
| 处理速度 | 提升33% | 从15秒减少到10秒（50条新闻） |
| 准确率 | 保持在0.85以上 | 通过优化提示词和兜底机制 |
| 数据完整性 | 显著提升 | 系统性校验机制确保所有字段正确填写 |
| 热度评分准确性 | 显著提升 | 所有新闻（包括外文）都能与热榜匹配 |
| 可维护性 | 显著提升 | 模块解耦，便于独立优化 |

## 七、实施步骤

### 阶段1：准备工作
1. 安装轻量级多语言模型依赖
2. 创建字段标准化模块
3. 创建轻量级分类器模块
4. 创建三阶段合并处理器模块
5. 创建热榜处理器模块
6. 创建数据完整性校验模块
7. 更新数据库结构（创建临时表）

### 阶段2：核心修改
1. 调整Task1Collector工作流顺序
2. 实现字段标准化功能
3. 实现轻量级初筛功能（信源赋分、快速分类）
4. 实现三阶段合并处理功能
5. 实现热榜提取与热度评分功能
6. 实现数据完整性校验功能
7. 优化AI批处理逻辑

### 阶段3：测试与验证
1. 测试字段标准化处理效果
2. 测试轻量级分类器性能
3. 验证三阶段合并处理效果
4. 测试热榜匹配效果（包括外文新闻）
5. 测试数据完整性校验机制
6. 对比优化前后的成本和准确性

### 阶段4：部署与监控
1. 部署优化后的工作流
2. 监控系统性能和成本
3. 持续优化模型和参数
4. 定期评估准确率和处理效率
5. 分析校验失败趋势，持续改进
6. 监控临时表数据增长情况，适时调整清理策略

## 八、方案变更说明

### 与原方案的主要调整

1. **处理策略变更**：
   - 原方案：翻译、摘要、深度分析三阶段分开处理
   - 新方案：三阶段合并为一次LLM调用
   - 改进：减少67%的API调用，降低33%的成本和时间

2. **热榜提取位置调整**：
   - 原方案：热榜提取在轻量级初筛阶段
   - 新方案：热榜提取在翻译之后
   - 改进：确保所有新闻（包括外文）都能与热榜匹配，提高热度评分准确性

3. **数据存储策略调整**：
   - 原方案：直接存入主表
   - 新方案：先存入临时表全量保存，再处理后存入主表
   - 改进：提高数据完整性，便于后续分析和回溯

4. **模块新增**：
   - 新增 `field_normalizer.py`：字段标准化模块
   - 新增 `lightweight_classifier.py`：轻量级多语言分类器
   - 新增 `combined_processor.py`：三阶段合并处理器
   - 新增 `heat_processor.py`：热榜处理器
   - 新增 `data_validator.py`：数据完整性校验器

5. **工作流调整**：
   - 新增轻量级初筛阶段（包含信源赋分）
   - 新增热榜提取与热度评分阶段
   - 新增数据完整性校验阶段
   - 调整处理顺序，将低成本操作前置

6. **功能增强**：
   - 字段标准化处理
   - 双摘要存储（原始摘要和系统摘要）
   - 完整的五维评分体系
   - 系统性的数据完整性校验
   - 热榜匹配优化

7. **数据库优化**：
   - 创建临时表用于全量存储
   - 增加初筛状态字段
   - 增加合并处理状态字段
   - 增加校验状态字段
   - 增加摘要相关字段
   - 增加评分相关字段

8. **性能优化**：
   - 批量处理优化
   - 缓存策略
   - 并发处理
   - 降级策略

## 九、潜在风险与应对

| 风险 | 应对方案 |
|------|----------|
| 轻量级模型分类准确率不足 | 设置合理的置信度阈值，低置信度样本进入深度分析 |
| 合并处理准确率下降 | 优化提示词设计，添加示例输出，设置准确率阈值 |
| 系统负载增加 | 实现并发处理和降级策略，优先处理重要新闻 |
| 数据库性能瓶颈 | 实现批量操作和连接池管理，监控临时表数据增长 |
| 模型推理资源消耗 | 选择轻量级模型，采用批处理、量化等技术 |
| 字段标准化失败 | 增加异常处理，记录失败原因，使用默认值 |
| 数据完整性校验失败 | 自动尝试补救，标记待人工处理，生成详细报告 |
| 热榜匹配效果不佳 | 优化匹配算法，使用更全面的热榜数据 |

## 十、结论

基于第一性原理的工作流优化方案，通过将低成本操作前置、高成本操作合并处理，显著降低了系统运行成本，同时提高了处理效率和数据完整性。此方案在保证准确率的同时，最大限度地减少了昂贵资源的使用，是当前最合适的改进方向。

**推荐立即开始实施此优化方案，预计可在2周内完成核心修改并投入使用。**