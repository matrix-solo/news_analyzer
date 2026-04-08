# 项目文档

## 结构说明

| 目录 | 用途 | 生命周期 |
|------|------|----------|
| `reference/` | 系统参考文档——"怎么做" | 持久，随代码更新 |
| `design/` | 设计决策记录——"为什么这样做" | 持久，写完不再改 |
| `archive/` | 历史工作笔记——诊断、修复、分析过程 | 只读归档 |

## reference/ 参考文档

| 文件 | 内容 |
|------|------|
| [deployment.md](reference/deployment.md) | Docker / 云部署快速指南 |
| [cloud-deployment-tutorial.md](reference/cloud-deployment-tutorial.md) | 云部署完整教程 |
| [cloud-migration-checklist.md](reference/cloud-migration-checklist.md) | 云迁移检查清单 |
| [workflow.md](reference/workflow.md) | V3 工作流架构参考 |
| [report-style-guide.md](reference/report-style-guide.md) | 深度报告样式规范 |
| [dev-guide.md](reference/dev-guide.md) | Phase B 开发指南（DB 迁移、import 路径） |

## design/ 设计文档

| 文件 | 内容 |
|------|------|
| [web-feedback-system.md](design/web-feedback-system.md) | Web 展示与反馈系统设计 |

## archive/ 归档

| 目录 | 内容 | 日期 |
|------|------|------|
| `2026-04-08-optimization/` | 代码审计、优化分析/计划、报告迭代分析、修复记录 | 2026-04-08 |
| `2026-04-07-evaluation/` | 项目整体评估 | 2026-04-07 |
| `cache-diagnosis/` | CI 缓存持久化诊断与改进方案 | 2026-04-08 |
| `system-review/` | 系统审查（数据流、模块依赖、force_stored 分析） | 2026-03 |

## 文档维护规则

1. **参考文档每人一个主题**，不按日期拆分（如 deployment.md 永远只有一份）
2. **工作笔记按日期归档**：`archive/YYYY-MM-DD-topic/`
3. **工作笔记的结论提炼到参考文档**后，原文留在 archive 不再更新
4. **不建空目录**
5. 新增文档时更新本索引
