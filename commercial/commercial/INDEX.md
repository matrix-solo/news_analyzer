# 商业化方案文档

本目录包含 Insight Hub 商业化项目的完整文档。

---

## 文档结构

```
commercial/
├── INDEX.md                       # 本文件（目录索引）
│
├── MVP方案（推荐）                 # 最小可行产品方案
│   ├── MVP_SRS.md                 # 需求规格说明书
│   ├── MVP_VALIDATION_PLAN.md     # 验证计划
│   ├── MVP_TECHNICAL_DESIGN.md    # 技术设计文档
│   └── MVP_IMPLEMENTATION_PLAN.md # 实施计划
│
└── 完整方案（参考）                 # 完整商业化方案（备用）
    ├── COMMERCIAL_DESIGN.md            # 技术设计文档
    ├── COMMERCIAL_CODE_CHANGES.md      # 代码改造清单
    └── COMMERCIAL_IMPLEMENTATION_PLAN.md # 实施计划
```

---

## 方案对比

| 维度 | MVP方案 | 完整方案 |
|------|---------|----------|
| **目标** | 验证付费意愿 | 完整商业化系统 |
| **时间** | 4天 | 6周 |
| **代码量** | 约275行 | 约2000行 |
| **风险** | 低 | 高 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## 推荐阅读顺序

### MVP方案

1. [MVP_SRS.md](./MVP_SRS.md) - 了解业务需求和用户需求
2. [MVP_VALIDATION_PLAN.md](./MVP_VALIDATION_PLAN.md) - 了解验证目标和方法
3. [MVP_TECHNICAL_DESIGN.md](./MVP_TECHNICAL_DESIGN.md) - 了解技术实现
4. [MVP_IMPLEMENTATION_PLAN.md](./MVP_IMPLEMENTATION_PLAN.md) - 开始实施

### 完整方案（MVP验证成功后参考）

1. [COMMERCIAL_DESIGN.md](./COMMERCIAL_DESIGN.md) - 完整技术设计
2. [COMMERCIAL_CODE_CHANGES.md](./COMMERCIAL_CODE_CHANGES.md) - 详细代码改造清单
3. [COMMERCIAL_IMPLEMENTATION_PLAN.md](./COMMERCIAL_IMPLEMENTATION_PLAN.md) - 完整实施计划

---

## 核心决策

### 为什么选择MVP方案？

1. **第一性原理**：从本质需求出发，验证付费意愿是核心目标
2. **YAGNI原则**：不做暂时不需要的功能
3. **风险控制**：最小投入验证假设，失败成本低
4. **快速迭代**：4天可完成，快速获得反馈

### MVP方案的核心内容

- **信源过滤**：仅保留国内合规信源
- **敏感词检测**：过滤政治敏感内容
- **领域映射**：政治 → 宏观动态
- **邮件订阅**：收集用户邮箱
- **付费入口**：爱发电/面包多链接

---

## 实施建议

1. **先执行MVP方案**：4天内完成核心功能
2. **验证付费意愿**：观察1个月，收集数据
3. **根据结果决策**：
   - 成功 → 参考完整方案进行产品化
   - 失败 → 分析原因，调整策略或放弃

---

## 更新记录

| 日期 | 变更内容 |
|------|----------|
| 2026-03-13 | 创建目录，整理文档 |
