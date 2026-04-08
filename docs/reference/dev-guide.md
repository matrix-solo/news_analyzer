# Phase B 开发指导文档

本文档指导完成三项非核心但必要的收尾工作，对主流程无影响，可按优先级逐步推进。

---

## 1. market_context 数据库迁移

**背景**：`core/storage/database.py` 已在 `_init_db()` 中加入 `market_context` 表的建表语句。
对于**已存在的旧数据库文件**，需手动执行以下迁移 SQL。

### 迁移 SQL

```sql
-- 新增市场数据缓存表（幂等，重复执行安全）
CREATE TABLE IF NOT EXISTS market_context (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL UNIQUE,
    snapshot_json TEXT NOT NULL,
    fetched_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_market_context_date ON market_context(date);
```

### 执行方式

```bash
# 方式一：sqlite3 CLI
sqlite3 data/news.db < migrate_market_context.sql

# 方式二：Python 一行命令
python -c "
import sqlite3
db = sqlite3.connect('data/news.db')
db.execute('''CREATE TABLE IF NOT EXISTS market_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    snapshot_json TEXT NOT NULL,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
db.execute('CREATE INDEX IF NOT EXISTS idx_market_context_date ON market_context(date)')
db.commit(); print('done')
"
```

### 说明

- 该表目前**仅被 `MarketDataFetcher` 以文件缓存方式使用**（`data/market_cache/market_YYYY-MM-DD.json`）
- 数据库表为预留扩展，暂不影响主流程
- 后续可在 `task1_collector.py` 的 Step 8 入库时顺带写入当日快照

---

## 2. tests/ 目录 import 路径修复

**背景**：`tests/` 下的测试文件使用旧架构的 import 路径（`from processors.`, `from utils.` 等），
当前均无法导入。主流程不受影响，但需要修复才能运行测试套件。

### 批量替换命令（在项目根目录执行）

```bash
# 替换 tests/ 下所有旧 import 路径
find tests/ -name "*.py" -exec sed -i \
  -e 's/from processors\./from core.processor./g' \
  -e 's/from utils\./from core.utils./g' \
  -e 's/from storage\./from core.storage./g' \
  -e 's/from filters\./from core.filters./g' \
  -e 's/from analysts\./from core.processor./g' \
  -e 's/from generators\./from core.processor.generators./g' \
  -e 's/from config\.loader/from core.config.loader/g' \
  -e 's/from rss\./from core.collector./g' \
  -e 's/from crawlers\./from core.collector.crawlers./g' \
  -e 's/from models\./from core.models./g' \
  {} \;
```

（Windows Git Bash / WSL 环境可直接运行；PowerShell 需换用 `Get-ChildItem | ForEach-Object { ... }`）

### 需要额外确认的导入

以下测试文件引用了已删除的类，需手动修正：

| 测试文件 | 旧引用 | 新位置 |
|---------|--------|--------|
| `tests/test_gap_driven_architecture.py` | `AIProcessor` | `core.processor.ai_processor` |
| `tests/test_smart_backtrack.py` | `IncrementalCollector` | `core.collector.incremental_collector` |
| `tests/unit/` | 各 processor 类 | 对应 `core.processor.*` |
| `tests/integration/` | `RSSCollector` | `core.collector.collector` |

### conftest.py 更新

`tests/conftest.py` 中的 `sys.path.insert` 应确保项目根目录在路径中：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### 验证

```bash
python -m pytest tests/ --collect-only 2>&1 | grep "ERROR\|error" | head -20
```

---

## 3. commercial/ 目录乱码修复

**背景**：`commercial/` 目录中的 Python 文件使用 GBK 编码写入，在 UTF-8 环境下读取
出现乱码，导致 SyntaxError。该目录不属于主流程，可独立修复。

### 诊断

```bash
# 检测乱码文件
python -c "
import os, ast
for root, dirs, files in os.walk('commercial'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fn in files:
        if not fn.endswith('.py'): continue
        path = os.path.join(root, fn)
        for enc in ['utf-8', 'gbk', 'gb2312']:
            try:
                src = open(path, encoding=enc).read()
                ast.parse(src)
                print(f'OK ({enc}): {path}')
                break
            except (UnicodeDecodeError, SyntaxError):
                continue
        else:
            print(f'FAILED: {path}')
"
```

### 修复步骤

对每个检测出为 GBK 编码的文件：

```bash
# 1. 读取（GBK）→ 重写（UTF-8）
python -c "
import sys
path = sys.argv[1]
content = open(path, encoding='gbk', errors='replace').read()
open(path, 'w', encoding='utf-8').write(content)
print(f'Converted: {path}')
" commercial/your_file.py

# 批量处理（谨慎：会覆盖原文件）
for f in commercial/**/*.py; do
    python -c "
import sys; path=sys.argv[1]
try:
    content = open(path, encoding='gbk').read()
    open(path, 'w', encoding='utf-8').write(content)
    print(f'OK: {path}')
except Exception as e:
    print(f'SKIP: {path}: {e}')
" "$f"
done
```

### 注意事项

- 修复前建议 `git stash` 或手动备份
- GBK→UTF-8 转换会保留原始中文字符，不会丢失内容
- 转换后需重新运行语法检查确认无误

---

## 优先级建议

| 优先级 | 任务 | 影响范围 | 工作量 |
|-------|------|---------|-------|
| 高 | market_context 迁移 | 仅旧数据库，新数据库自动建表 | 5 分钟 |
| 中 | tests/ 路径修复 | 仅测试套件，主流程不受影响 | 1-2 小时 |
| 低 | commercial/ 乱码 | 独立模块，不影响主流程 | 按需 |
