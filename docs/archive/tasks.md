# 项目工作流架构文档编写 Tasks

## 第一批：核心工作流（阶段1-6）

### 阶段1：入口与核心工作流
- [ ] 1.1 审阅 task1_collector.py - 采集工作流6阶段、兜底重判逻辑
- [ ] 1.2 审阅 task2_reporter.py - 报告生成工作流7阶段、邮件发送
- [ ] 1.3 审阅 run_collect.py - 采集入口封装
- [ ] 1.4 审阅 run_report.py - 报告入口封装
- [ ] 1.5 审阅 run_now.py - 一键运行逻辑
- [ ] 1.6 审阅 send_email.py - 邮件发送入口
- [ ] 1.7 编写：核心工作流章节（Task1/Task2流程图）

### 阶段2：RSS采集模块
- [ ] 2.1 审阅 rss/collector.py - 多级fallback机制、超时重试
- [ ] 2.2 审阅 rss/sources.py - RSSSource数据结构、源管理
- [ ] 2.3 审阅 rss/parser.py - RSS解析逻辑
- [ ] 2.4 审阅 rss/incremental_collector.py - 增量采集逻辑
- [ ] 2.5 审阅 rss/api_sources.py - API数据源
- [ ] 2.6 审阅 sources.yaml - 源配置结构
- [ ] 2.7 编写：RSS采集工作流章节

### 阶段3：过滤与校验模块
- [ ] 3.1 审阅 filters/ai_filter_agent.py - 5W1H检测、五维评分、批处理重试
- [ ] 3.2 审阅 filters/source_validator.py - 白名单校验
- [ ] 3.3 审阅 filters/content_filter.py - 内容过滤
- [ ] 3.4 审阅 filters/deduplication.py - 去重逻辑
- [ ] 3.5 编写：过滤与校验工作流章节

### 阶段4：处理与解析模块
- [ ] 4.1 审阅 processors/ai_processor.py - 多provider支持、用途分类
- [ ] 4.2 审阅 processors/content_parser.py - 规则解析、AI兜底
- [ ] 4.3 审阅 processors/history_relation_engine.py - 历史关联分析
- [ ] 4.4 审阅 processors/history_relation_engine_bge3.py - BGE3版本关联分析
- [ ] 4.5 审阅 processors/chart_data_service.py - 图表数据服务
- [ ] 4.6 审阅 config/parsing_rules.example.yaml - 解析规则配置
- [ ] 4.7 编写：处理与解析工作流章节

### 阶段5：存储模块
- [ ] 5.1 审阅 storage/database.py - 事务安全、连接池、WAL模式、重试机制
- [ ] 5.2 审阅 storage/baseline.py - 历史数据基线
- [ ] 5.3 审阅 storage/file_manager.py - 文件管理
- [ ] 5.4 审阅 storage/storage_manager.py - 存储管理器
- [ ] 5.5 编写：存储工作流章节

### 阶段6：报告生成模块
- [ ] 6.1 审阅 generators/report_generator.py - 报告生成、模板渲染、PDF导出
- [ ] 6.2 审阅 analysts/depth_analyzer.py - 深度分析、洞察生成
- [ ] 6.3 审阅 analysts/investment_advisor.py - 投资分析（可选）
- [ ] 6.4 审阅 config/report_templates.yaml - 报告模板配置
- [ ] 6.5 编写：报告生成工作流章节

### 第一批交付物
- [ ] 保存中间文档：docs/workflow_architecture_part1.md

---

## 第二批：扩展模块（阶段7-9）

### 阶段7：知识库模块
- [ ] 7.1 审阅 knowledge/rag_manager.py - RAG检索管理
- [ ] 7.2 审阅 knowledge/retriever.py - 向量检索、时间衰减
- [ ] 7.3 审阅 knowledge/chroma_store.py - ChromaDB存储
- [ ] 7.4 审阅 knowledge/embedding.py - 向量化服务
- [ ] 7.5 审阅 knowledge/pipeline.py - 向量化Pipeline
- [ ] 7.6 审阅 knowledge/chunking.py - 文本分块
- [ ] 7.7 审阅 knowledge/cleanup.py - 过期清理
- [ ] 7.8 审阅 config/knowledge.yaml - 知识库配置
- [ ] 7.9 编写：知识库工作流章节

### 阶段8：工具与配置模块
- [ ] 8.1 审阅 utils/incremental_tracker.py - 增量跟踪、智能回溯
- [ ] 8.2 审阅 utils/collection_config.py - 采集配置、遗漏检测
- [ ] 8.3 审阅 utils/task_lock.py - 任务锁机制
- [ ] 8.4 审阅 utils/heartbeat.py - 心跳检测
- [ ] 8.5 审阅 utils/api_optimizer.py - API调用优化
- [ ] 8.6 审阅 utils/email_sender.py - 邮件发送
- [ ] 8.7 审阅 utils/chart_generator.py - 图表生成
- [ ] 8.8 审阅 utils/errors.py - 错误定义
- [ ] 8.9 审阅 utils/http_client.py - HTTP客户端
- [ ] 8.10 审阅 utils/proxy_config.py - 代理配置
- [ ] 8.11 审阅 utils/text_utils.py - 文本工具
- [ ] 8.12 审阅 utils/md2pdf.py - PDF生成
- [ ] 8.13 审阅 utils/logging_config.py - 日志配置
- [ ] 8.14 审阅 utils/log_utils.py - 日志工具
- [ ] 8.15 审阅 utils/performance.py - 性能监控
- [ ] 8.16 审阅 utils/security.py - 安全工具
- [ ] 8.17 审阅 utils/health_monitor.py - 健康监控
- [ ] 8.18 审阅 config/manager.py - 配置管理器
- [ ] 8.19 审阅 config/loader.py - 配置加载
- [ ] 8.20 审阅 config/ai_providers.yaml - AI厂商配置
- [ ] 8.21 编写：工具与配置章节

### 阶段9：模型与数据结构
- [ ] 9.1 审阅 models/data_models.py - 数据模型定义
- [ ] 9.2 编写：数据模型章节

### 第二批交付物
- [ ] 保存中间文档：docs/workflow_architecture_part2.md

---

## 第三批：其他模块（阶段10-17）

### 阶段10：爬虫模块
- [ ] 10.1 审阅 crawlers/base.py - 爬虫基类
- [ ] 10.2 审阅 crawlers/factory.py - 爬虫工厂
- [ ] 10.3 审阅 crawlers/xinhua.py - 新华社爬虫
- [ ] 10.4 审阅 crawlers/people.py - 人民日报爬虫
- [ ] 10.5 编写：爬虫模块章节

### 阶段11：调度与CI/CD
- [ ] 11.1 审阅 scheduler/task_scheduler.py - 任务调度器
- [ ] 11.2 审阅 .github/workflows/collect.yml - 采集工作流
- [ ] 11.3 审阅 .github/workflows/report.yml - 报告工作流
- [ ] 11.4 审阅 .github/workflows/send_email.yml - 邮件工作流
- [ ] 11.5 编写：定时任务调度章节

### 阶段12：脚本工具
- [ ] 12.1 审阅 scripts/automation/*.bat/ps1 - 自动化脚本
- [ ] 12.2 审阅 scripts/database/*.py - 数据库脚本
- [ ] 12.3 审阅 scripts/maintenance/*.py - 维护脚本
- [ ] 12.4 审阅 scripts/deployment/*.py - 部署脚本
- [ ] 12.5 审阅 scripts/tools/*.py - 工具脚本
- [ ] 12.6 编写：脚本工具章节

### 阶段13：商业化模块
- [ ] 13.1 审阅 commercial/web/app.py - Web应用
- [ ] 13.2 审阅 commercial/subscription/subscriber_manager.py - 订阅管理
- [ ] 13.3 审阅 commercial/compliance/content_filter.py - 合规过滤
- [ ] 13.4 审阅 commercial/services/email_service.py - 邮件服务
- [ ] 13.5 编写：商业化模块章节

### 阶段14：测试模块
- [ ] 14.1 审阅 tests/conftest.py - 测试配置
- [ ] 14.2 审阅 tests/unit/*.py - 单元测试
- [ ] 14.3 审阅 tests/integration/*.py - 集成测试
- [ ] 14.4 审阅 tests/test_gap_driven_architecture.py - 遗漏驱动架构测试
- [ ] 14.5 审阅 tests/test_smart_backtrack.py - 智能回溯测试
- [ ] 14.6 审阅 tests/fixtures/sample_data.py - 测试数据
- [ ] 14.7 编写：测试与调试章节

### 阶段15：基础设施与配置
- [ ] 15.1 审阅 requirements.txt - Python依赖
- [ ] 15.2 审阅 requirements.lock - 锁定版本
- [ ] 15.3 审阅 pyproject.toml - 项目配置
- [ ] 15.4 审阅 pytest.ini - 测试配置
- [ ] 15.5 审阅 .pre-commit-config.yaml - 预提交钩子
- [ ] 15.6 审阅 docker-compose.yml - Docker编排
- [ ] 15.7 审阅 Dockerfile - Docker镜像
- [ ] 15.8 审阅 .env.example - 环境变量示例
- [ ] 15.9 审阅 .gitignore - Git忽略规则
- [ ] 15.10 审阅 README.md - 项目说明
- [ ] 15.11 编写：配置体系章节

### 阶段16：根目录工具脚本
- [ ] 16.1 审阅 check_entity_fields.py - 实体字段检查

### 阶段17：数据库脚本补充
- [ ] 17.1 审阅 scripts/database/backfill_embeddings.py - 嵌入向量回填
- [ ] 17.2 审阅 scripts/database/migrate_add_embedding.py - 嵌入迁移

### 第三批交付物
- [ ] 保存中间文档：docs/workflow_architecture_part3.md

---

## 第四批：整合编写

### 整合任务
- [ ] 18.1 整合所有中间文档
- [ ] 18.2 编写系统架构概览章节
- [ ] 18.3 编写兜底与容错机制章节
- [ ] 18.4 编写数据流转章节
- [ ] 18.5 编写数据库设计章节
- [ ] 18.6 编写API与接口章节
- [ ] 18.7 统一格式和术语
- [ ] 18.8 添加目录和交叉引用
- [ ] 18.9 最终校对和验证

### 最终交付物
- [ ] 生成完整文档：docs/WORKFLOW_ARCHITECTURE_V2.md

---

## 进度追踪

| 批次 | 总任务数 | 已完成 | 进度 |
|------|----------|--------|------|
| 第一批 | 38 | 0 | 0% |
| 第二批 | 24 | 0 | 0% |
| 第三批 | 47 | 0 | 0% |
| 第四批 | 10 | 0 | 0% |
| **总计** | **119** | **0** | **0%** |

---

**状态**: 待开始
**开始时间**: -
**预计完成时间**: -
