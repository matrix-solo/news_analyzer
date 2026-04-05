# 项目工作流架构说明 - 第二批：扩展模块

> 本文档为中间交付物，覆盖阶段7-9：知识库模块、工具与配置模块、模型与数据结构

---

## 7. 知识库模块 (knowledge/)

### 7.1 概述
知识库模块提供RAG（检索增强生成）能力，支持深度分析时的历史新闻检索和关联分析。

**核心组件**:
- RAGRetriever: RAG检索器
- ChromaKnowledgeBase: ChromaDB向量存储
- EmbeddingService: 向量化服务
- KnowledgePipeline: 向量化Pipeline
- SemanticChunkingStrategy: 语义分块策略
- CleanupService: 过期清理服务

### 7.2 RAGRetriever (knowledge/retriever.py)

#### 7.2.1 核心职责
- 向量检索
- 时间衰减应用
- 上下文构建

#### 7.2.2 检索流程

```python
def retrieve(self, query: str, domain_filter: Optional[str] = None, 
             use_time_decay: bool = True) -> RAGContext:
    # 1. 生成查询向量
    query_embedding = self.embedding_service.get_single_embedding(query)
    
    # 2. 向量检索
    results = self.knowledge_base.search_by_embedding(
        embedding=query_embedding,
        top_k=self.top_k * 2,
        where_filter=where_filter
    )
    
    # 3. 应用时间衰减
    if use_time_decay:
        results = self._apply_time_decay(results)
    
    # 4. 过滤低分结果
    results = [r for r in results if r.score >= self.min_score]
    results = results[:self.top_k]
    
    # 5. 构建上下文
    return self._build_context(query, results)
```

#### 7.2.3 时间衰减公式

```python
def _calculate_time_decay(self, pub_date: str) -> float:
    days_diff = (datetime.now() - news_date).days
    
    if days_diff <= 0:
        return 1.0
    elif days_diff >= self.time_decay_days * 3:
        return 0.3
    else:
        return math.exp(-days_diff / self.time_decay_days)
```

**时间衰减配置**:
- `time_decay_days`: 30天（半衰期）
- 超过90天的新闻得分衰减至0.3

#### 7.2.4 异常检测检索

```python
def retrieve_anomaly_for_event(self, event_summary: str, 
                               event_entities: Optional[List[str]] = None) -> RAGContext:
    """
    检索出近期聚类库中'余弦相似度极低但实体相同'的新闻，作为突变的素材
    """
    # 1. 扩检索相似文档（top_k * 5）
    results = self.knowledge_base.search_by_embedding(
        embedding=query_embedding,
        top_k=self.top_k * 5
    )
    
    # 2. 过滤：内容相似度低（<0.7）但实体存在重叠
    anomaly_results = []
    for result in results:
        content = result.document.content
        has_entity = any(entity in content for entity in event_entities)
        
        if has_entity and result.score < 0.7:
            anomaly_results.append(result)
    
    # 3. 按相似度升序排序（越低越异常）
    anomaly_results.sort(key=lambda x: x.score)
    
    return self._build_context(enhanced_query, anomaly_results[:self.top_k])
```

### 7.3 ChromaKnowledgeBase (knowledge/chroma_store.py)

#### 7.3.1 核心职责
- ChromaDB客户端管理
- 文档增删改查
- 向量检索

#### 7.3.2 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `persist_dir` | data/knowledge_base/chroma | 持久化目录 |
| `collection_name` | news_articles | 集合名称 |
| `embedding_dimension` | 1024 | 向量维度 |
| `hnsw:space` | cosine | 相似度度量 |

#### 7.3.3 核心方法

```python
def add_documents(self, documents: List[Document]) -> int:
    """添加文档（支持预计算向量）"""
    if embeddings:
        self.collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
            embeddings=embeddings  # 预计算向量
        )

def search_by_embedding(self, embedding: List[float], 
                       top_k: int = 5) -> List[SearchResult]:
    """基于向量的相似度搜索"""
    results = self.collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )
    return self._parse_results(results)
```

### 7.4 EmbeddingService (knowledge/embedding.py)

#### 7.4.1 核心职责
- 文本向量化
- 本地模型管理
- 支持双模型（主模型+快速模型）

#### 7.4.2 模型配置

| 模型 | 名称 | 维度 | 用途 |
|------|------|------|------|
| 主模型 | BAAI/bge-m3 | 1024 | 高精度检索 |
| 快速模型 | all-MiniLM-L6-v2 | 384 | 快速检索 |

#### 7.4.3 使用方法

```python
# 获取单条文本向量
embedding = embedding_service.get_single_embedding(text)

# 批量获取向量
embeddings = embedding_service.get_embeddings(texts, use_fast=False)

# 使用快速模型
fast_embedding = embedding_service.get_single_embedding(text, use_fast=True)
```

### 7.5 KnowledgePipeline (knowledge/pipeline.py)

#### 7.5.1 核心职责
- 新闻向量化Pipeline
- 增量索引
- 批量处理

#### 7.5.2 索引流程

```python
def _process_and_index_news(self, news: Dict) -> int:
    # 1. 文本分块
    chunks = self.chunking_strategy.create_chunks(news)
    
    # 2. 创建文档对象
    documents = self._create_documents(chunks)
    
    # 3. 生成向量
    texts = [doc.content for doc in documents]
    embeddings = self.embedding_service.get_embeddings(texts)
    
    # 4. 写入ChromaDB
    added = self.knowledge_base.add_documents(documents)
    
    # 5. 标记已索引
    if added > 0:
        self._mark_indexed(news_id)
    
    return 1 if added > 0 else 0
```

#### 7.5.3 增量索引策略

```python
def _get_unindexed_news(self, limit: int = 100) -> List[Dict]:
    """获取未索引的新闻（LEFT JOIN knowledge_index）"""
    cursor.execute("""
        SELECT n.id, n.title, n.content, n.summary, n.url, n.domain, n.pub_date
        FROM news n
        LEFT JOIN knowledge_index ki ON n.id = ki.news_id
        WHERE ki.news_id IS NULL
        ORDER BY n.pub_date DESC
        LIMIT ?
    """, (limit,))
```

### 7.6 SemanticChunkingStrategy (knowledge/chunking.py)

#### 7.6.1 核心职责
- 语义分块
- 保持段落完整性
- 标题/摘要/内容分别处理

#### 7.6.2 分块策略

```python
def create_chunks(self, news: Dict) -> List[Chunk]:
    chunks = []
    
    # 1. 标题块（单独一块）
    if title:
        chunks.append(Chunk(
            id=f"{news_id}_title",
            content=f"【标题】{title}",
            chunk_type="title"
        ))
    
    # 2. 摘要块（不超过chunk_size）
    if summary:
        if token_count <= self.chunk_size:
            chunks.append(Chunk(
                id=f"{news_id}_summary",
                content=f"【摘要】{summary}",
                chunk_type="summary"
            ))
        else:
            # 长摘要分块
            chunks.extend(self._split_long_text(summary))
    
    # 3. 内容块（语义分块）
    if content:
        content_chunks = self._split_content_semantic(content)
        chunks.extend(content_chunks)
    
    return chunks
```

#### 7.6.3 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 512 | 分块大小（token数） |
| `overlap` | 50 | 重叠token数 |
| `max_content_length` | 8000 | 最大内容长度 |
| `respect_paragraphs` | True | 保持段落完整性 |

### 7.7 CleanupService (knowledge/cleanup.py)

#### 7.7.1 核心职责
- 过期新闻清理
- 向量数据同步删除

#### 7.7.2 清理流程

```python
def cleanup_expired(self) -> int:
    # 1. 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=self.retention_days)
    
    # 2. 获取过期新闻ID
    expired_ids = self._get_expired_news_ids(cutoff_date)
    
    # 3. 删除对应的向量块
    deleted_chunks = self._delete_chunks_by_news_ids(expired_ids)
    
    # 4. 清理索引表
    self._cleanup_index_table(expired_ids)
    
    return len(expired_ids)
```

**保留时间**: 90天（config/knowledge.yaml中配置）

### 7.8 知识库配置 (config/knowledge.yaml)

```yaml
knowledge_base:
  type: chroma
  persist_dir: data/knowledge_base/chroma
  collection_name: news_articles
  embedding_dimension: 1024

embedding:
  provider: local
  model: BAAI/bge-m3
  fast_model: all-MiniLM-L6-v2
  batch_size: 32
  max_length: 8192

retrieval:
  top_k: 10
  min_score: 0.5
  time_decay_days: 30
  max_context_length: 4000

indexing:
  strategy: incremental
  chunk_size: 512
  chunk_overlap: 50
  content_max_length: 8000

cleanup:
  retention_days: 90
  schedule: "0 3 * * *"  # 每天3点执行
```

---

## 8. 工具与配置模块 (utils/)

### 8.1 IncrementalTracker (utils/incremental_tracker.py)

#### 8.1.1 核心职责
- 增量采集状态跟踪
- 智能回溯计算
- 源级别统计

#### 8.1.2 状态数据结构

```python
@dataclass
class SourceCollectionState:
    name: str                          # 源名称
    last_pub_date: Optional[str]       # 最后发布日期
    last_collection_time: Optional[str]  # 最后采集时间
    total_collected: int = 0           # 总采集数
    collection_count: int = 0          # 采集次数
    avg_news_per_collection: float = 0.0  # 平均每次采集数
    high_frequency: bool = False       # 是否高频源
    frequency_score: float = 0.0       # 频率评分
```

#### 8.1.3 智能回溯策略

| 中断时长 | 策略 | 回溯计算 |
|----------|------|----------|
| ≤1小时 | 保守回溯 | 1小时 |
| 1-6小时 | 线性回溯 | 中断时长 + 1小时 |
| 6-24小时 | 激进回溯 | min(中断时长 × 1.5, 36小时) |
| 24-72小时 | 深度回溯 | min(中断时长 + 12, 96小时) |
| >72小时 | 保守深度 | 72小时（受RSS滚动限制） |

#### 8.1.4 RSS滚动限制

| 源类型 | 滚动限制 | 说明 |
|--------|----------|------|
| 通讯社 | 24小时 | 新闻滚动最快 |
| 中央媒体 | 96小时 | 滚动最慢 |
| 财经媒体 | 48小时 | 中等滚动 |
| 综合媒体 | 48小时 | 默认值 |

### 8.2 CollectionConfigManager (utils/collection_config.py)

#### 8.2.1 核心职责
- 采集配置管理
- 遗漏检测
- 智能回溯计算

#### 8.2.2 遗漏检测逻辑（基于RSS滚动边界）

```python
def detect_gap(self, source_name, db_latest, rss_earliest, rss_latest):
    """
    核心原理：
    RSS源会滚动，旧新闻会被"挤出"。
    RSS feed中最后一条（最早发布的）新闻，就是RSS源当前能提供的最早新闻。
    
    如果 db_latest >= rss_earliest：无遗漏
    如果 db_latest < rss_earliest：存在遗漏
    """
    if db_latest >= rss_earliest:
        return {'has_gap': False, 'gap_type': 'none'}
    else:
        time_gap = (rss_earliest - db_latest).hours
        return {
            'has_gap': True,
            'gap_type': 'rss_rollover',
            'time_gap_hours': time_gap
        }
```

### 8.3 TaskLock (utils/task_lock.py)

#### 8.3.1 核心职责
- 任务锁机制
- 防止定时任务冲突
- 跨平台支持

#### 8.3.2 跨平台实现

**Unix/Linux**:
```python
import fcntl

# 使用fcntl文件锁
fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
```

**Windows**:
```python
# 使用文件存在性检查 + 进程检测
if self.lock_file.exists():
    if self._is_lock_expired():
        self._force_release()
    else:
        # 检查PID是否存在
        if not self._is_process_alive(pid):
            self._force_release()
```

#### 8.3.3 锁文件格式

```
PID: 12345
Time: 2026-03-15T07:00:00
Timeout: 3600
```

#### 8.3.4 使用方式

```python
# 方式1: 上下文管理器
with TaskLock('collect', timeout=3600):
    run_collection()

# 方式2: 手动控制
lock = TaskLock('collect', timeout=3600)
if lock.acquire(blocking=False):
    try:
        run_collection()
    finally:
        lock.release()
```

### 8.4 HeartbeatMonitor (utils/heartbeat.py)

#### 8.4.1 核心职责
- 任务执行状态监控
- 超时检测
- 进度跟踪

#### 8.4.2 心跳状态

```python
@dataclass
class HeartbeatStatus:
    task_name: str          # 任务名称
    status: str             # running/success/failed/timeout
    start_time: str         # 开始时间
    end_time: Optional[str] # 结束时间
    duration_seconds: float # 执行时长
    progress: int           # 进度0-100
    message: str            # 状态消息
    error: Optional[str]    # 错误信息
```

#### 8.4.3 使用方式

```python
monitor = HeartbeatMonitor()

# 开始任务
monitor.start('collect', '开始采集')

# 更新进度
monitor.update(50, 'AI内容属性校验')

# 标记成功
monitor.success('采集完成')

# 或标记失败
monitor.fail('AI API错误')
```

### 8.5 APIOptimizer (utils/api_optimizer.py)

#### 8.5.1 核心职责
- 响应缓存
- 智能批处理
- 速率限制

#### 8.5.2 响应缓存

```python
class ResponseCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size      # 最大缓存条目数
        self.default_ttl = default_ttl  # 默认缓存时间（秒）
    
    def get(self, func, *args, **kwargs) -> Optional[Any]:
        # 生成缓存键（基于函数名和参数哈希）
        key = self._generate_key(func, *args, **kwargs)
        return self._cache.get(key)
```

### 8.6 ConfigManager (config/manager.py)

#### 8.6.1 核心职责
- 统一配置管理
- 多源配置加载
- 配置访问接口

#### 8.6.2 配置加载顺序

```
1. 代码默认值（最低优先级）
      ↓
2. 环境变量（.env文件）
      ↓
3. YAML配置文件
      ↓
4. 运行时参数（最高优先级）
```

#### 8.6.3 配置访问方式

```python
config = ConfigManager()

# 点号路径访问
api_key = config.get('env.deepseek_api_key')
sources = config.get('sources.domestic.central')

# 专用方法
sources = config.get_sources()
ai_providers = config.get_ai_providers()
```

---

## 9. 模型与数据结构 (models/)

### 9.1 NewsItem (models/data_models.py)

#### 9.1.1 数据模型

```python
@dataclass
class NewsItem:
    """新闻条目模型"""
    title: str                          # 标题
    date: str                           # 日期
    official_source: str                # 官方来源
    official_url: Optional[str]         # 官方URL
    official_content: Optional[str]     # 官方内容
    domain: str = "general"             # 领域
    summary: Optional[str]              # 摘要
    tags: List[str] = field(default_factory=list)  # 标签
    third_party_contents: List[ThirdPartyContent] = field(default_factory=list)  # 第三方内容
    is_official: bool = True            # 是否官方
    core_tags: List[str] = field(default_factory=list)  # 核心标签
    conclusion: Optional[str]           # 结论
```

#### 9.1.2 序列化方法

```python
def to_dict(self) -> Dict[str, Any]:
    """转换为字典"""
    return {
        'id': self.id,
        'title': self.title,
        'date': self.date,
        'domain': self.domain,
        'tags': self.tags,
        'core_tags': self.core_tags,
        # ...
    }

@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'NewsItem':
    """从字典创建"""
    return cls(
        id=data.get('id'),
        title=data.get('title', ''),
        # ...
    )
```

### 9.2 ThirdPartyContent

```python
@dataclass
class ThirdPartyContent:
    """第三方内容模型"""
    source: str                         # 来源
    news_id: Optional[int]              # 新闻ID
    title: Optional[str]                # 标题
    url: Optional[str]                  # URL
    content: Optional[str]              # 内容
    added_value: Optional[str]          # 增值内容
    similarity_score: float = 0.0       # 相似度评分
```

### 9.3 Event

```python
@dataclass
class Event:
    """事件追踪模型"""
    name: str                           # 事件名称
    description: Optional[str]          # 描述
    start_date: Optional[str]           # 开始日期
    end_date: Optional[str]             # 结束日期
    status: str = "ongoing"             # 状态
    news_ids: List[int] = field(default_factory=list)  # 关联新闻ID
```

### 9.4 NewsReport

```python
@dataclass
class NewsReport:
    """新闻报告模型"""
    title: str                          # 标题
    date: str                           # 日期
    domain: str                         # 领域
    core_tags: List[str]                # 核心标签
    official_content: str               # 官方内容
    official_source: str                # 官方来源
    third_party_contents: List[Dict]    # 第三方内容
    conclusion: Optional[str]           # 结论
    
    def to_markdown(self) -> str:
        """生成Markdown格式报告"""
        # ...
```

---

## 附录C：知识库数据流转

### C.1 向量化Pipeline

```
新闻入库 (news表)
    ↓
触发向量化 (KnowledgePipeline.index_news)
    ↓
文本分块 (SemanticChunkingStrategy.create_chunks)
    ├─ 标题块
    ├─ 摘要块
    └─ 内容块（语义分块）
    ↓
生成向量 (EmbeddingService.get_embeddings)
    ├─ BAAI/bge-m3 (1024维)
    └─ all-MiniLM-L6-v2 (384维，快速)
    ↓
写入ChromaDB (ChromaKnowledgeBase.add_documents)
    ↓
标记已索引 (knowledge_index表)
```

### C.2 RAG检索流程

```
查询请求
    ↓
生成查询向量 (EmbeddingService.get_single_embedding)
    ↓
向量检索 (ChromaKnowledgeBase.search_by_embedding)
    ├─ top_k=20（初始检索更多）
    └─ 余弦相似度排序
    ↓
应用时间衰减 (RAGRetriever._apply_time_decay)
    ├─ 30天半衰期
    └─ 超过90天衰减至0.3
    ↓
过滤低分结果 (score >= 0.5)
    ↓
取top_k=10
    ↓
构建上下文 (RAGRetriever._build_context)
    └─ 最大4000字符
```

---

## 附录D：增量采集状态流转

### D.1 状态文件结构

```json
{
  "updated_at": "2026-03-15T07:00:00",
  "sources": {
    "新华社": {
      "name": "新华社",
      "last_pub_date": "2026-03-15T06:30:00",
      "last_collection_time": "2026-03-15T07:00:00",
      "total_collected": 1000,
      "collection_count": 100,
      "avg_news_per_collection": 10.0,
      "high_frequency": true,
      "frequency_score": 0.8
    }
  }
}
```

### D.2 智能回溯计算流程

```
获取最后采集时间
    ↓
计算中断时长 (当前时间 - 最后采集时间)
    ↓
根据中断时长选择策略
    ├─ ≤1小时 → 回溯1小时
    ├─ 1-6小时 → 回溯(时长+1)小时
    ├─ 6-24小时 → 回溯min(时长×1.5, 36)小时
    ├─ 24-72小时 → 回溯min(时长+12, 96)小时
    └─ >72小时 → 回溯72小时
    ↓
受RSS滚动限制约束
    ├─ 通讯社: 24小时
    ├─ 中央媒体: 96小时
    ├─ 财经媒体: 48小时
    └─ 综合媒体: 48小时
    ↓
返回最终回溯时间
```

---

**文档版本**: 第二批中间交付物
**覆盖范围**: 阶段7-9（知识库模块、工具与配置模块、模型与数据结构）
**创建时间**: 2026-03-15
**状态**: 待整合到完整文档
