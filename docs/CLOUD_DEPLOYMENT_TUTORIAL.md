# 新闻分析系统云部署完整教程

本教程将指导您完成新闻分析系统从本地到云端的完整部署过程。

---

## 目录

1. [部署前准备](#一部署前准备)
2. [本地环境验证](#二本地环境验证)
3. [GitHub 仓库配置](#三github-仓库配置)
4. [GitHub Actions 配置](#四github-actions-配置)
5. [Docker 部署（可选）](#五docker-部署可选)
6. [验证与监控](#六验证与监控)
7. [故障排除](#七故障排除)
8. [最佳实践](#八最佳实践)

---

## 一、部署前准备

### 1.1 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| Python | 3.9+ | 3.11+ |
| Git | 2.0+ | 最新版 |
| Docker | 20.10+ | 最新版 |
| Docker Compose | 2.0+ | 最新版 |

### 1.2 账号准备

- [ ] GitHub 账号（用于代码托管和 Actions）
- [ ] AI 模型 API 密钥（至少一个）
  - DeepSeek: https://platform.deepseek.com/
  - 豆包（火山引擎）: https://console.volcengine.com/ark
  - 通义千问: https://dashscope.console.aliyun.com/
- [ ] 邮箱账号（用于发送报告，可选）

### 1.3 本地数据备份

部署前务必备份本地数据：

```bash
# 备份数据库
python -c "from storage.database import get_db; get_db().backup_database()"

# 查看备份列表
python scripts/restore_backup.py --list
```

---

## 二、本地环境验证

### 2.1 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/news_analyzer.git
cd news_analyzer
```

### 2.2 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 或使用锁定版本（推荐云部署）
pip install -r requirements.lock
```

### 2.3 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
nano .env  # Linux/macOS
# 或
notepad .env  # Windows
```

**必需配置项**：

```env
# 深度分析模型（必需）
AI_ANALYSIS_PROVIDER=deepseek
AI_ANALYSIS_MODEL=deepseek-reasoner
AI_ANALYSIS_KEY=your-deepseek-api-key
AI_ANALYSIS_BASE_URL=https://api.deepseek.com/v1

# 快速筛选模型（必需）
AI_FILTER_PROVIDER=doubao
AI_FILTER_MODEL=doubao-seed-2-0-lite-260215
AI_FILTER_KEY=your-doubao-api-key
AI_FILTER_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

**可选配置项**：

```env
# 邮件推送（可选）
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_auth_code
EMAIL_TO=recipient@example.com

# 代理配置（本地运行可选）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 2.4 运行验证测试

```bash
# 1. 持久化测试
python scripts/test_persistence.py

# 预期输出：
# ✅ 数据库持久化: 通过
# ✅ 文件系统持久化: 通过
# ✅ 卷挂载测试: 通过
# 🎉 所有持久化测试通过！

# 2. 健康检查
python scripts/health_check.py

# 预期输出：
# ✅ 数据库状态: 正常
# ✅ 环境变量: 配置正常
# ✅ 目录结构: 所有必需目录存在
# ✅ 最近活动: 系统活跃
# ✅ 备份状态: 备份正常
# 总体状态: ✅ 健康

# 3. 功能测试
python run_now.py

# 预期：采集新闻并生成报告
```

---

## 三、GitHub 仓库配置

### 3.1 创建 GitHub 仓库

1. 登录 GitHub
2. 点击右上角 "+" → "New repository"
3. 填写仓库信息：
   - Repository name: `news_analyzer`
   - Description: `AI-powered news analysis workflow`
   - Visibility: Private（推荐）或 Public
4. 点击 "Create repository"

### 3.2 推送代码

```bash
# 初始化 Git（如果尚未初始化）
git init

# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/news_analyzer.git

# 添加所有文件
git add .

# 提交
git commit -m "准备云部署"

# 推送到 GitHub
git push -u origin main
```

### 3.3 配置 .gitignore

确保 `.gitignore` 包含以下内容：

```gitignore
# 环境变量
.env
.env.local

# 数据文件
data/
logs/
reports/
backups/

# Python
__pycache__/
*.py[cod]
venv/

# IDE
.vscode/
.idea/
```

---

## 四、GitHub Actions 配置

### 4.1 配置 GitHub Secrets

1. 进入仓库页面
2. 点击 "Settings" → "Secrets and variables" → "Actions"
3. 点击 "New repository secret" 添加以下密钥：

| Secret 名称 | 必需 | 说明 | 示例值 |
|------------|------|------|--------|
| `AI_ANALYSIS_PROVIDER` | ✅ | 深度分析厂商 | `deepseek` |
| `AI_ANALYSIS_MODEL` | ✅ | 深度分析模型 | `deepseek-reasoner` |
| `AI_ANALYSIS_KEY` | ✅ | 深度分析API密钥 | `sk-xxxxx` |
| `AI_ANALYSIS_BASE_URL` | ❌ | API地址 | `https://api.deepseek.com/v1` |
| `AI_FILTER_PROVIDER` | ✅ | 快速筛选厂商 | `doubao` |
| `AI_FILTER_MODEL` | ✅ | 快速筛选模型 | `doubao-seed-2-0-lite-260215` |
| `AI_FILTER_KEY` | ✅ | 快速筛选API密钥 | `xxxxx` |
| `AI_FILTER_BASE_URL` | ❌ | API地址 | `https://ark.cn-beijing.volces.com/api/v3` |
| `SMTP_HOST` | ❌ | SMTP服务器 | `smtp.qq.com` |
| `SMTP_PORT` | ❌ | SMTP端口 | `587` |
| `SMTP_USER` | ❌ | 发件邮箱 | `your@qq.com` |
| `SMTP_PASSWORD` | ❌ | 邮箱授权码 | `xxxxx` |
| `EMAIL_TO` | ❌ | 收件人邮箱 | `recipient@example.com` |

### 4.2 工作流说明

项目已预配置三个 GitHub Actions 工作流：

#### collect.yml（采集工作流）

```yaml
触发时间（北京时间）:
  - 07:00（主任务）
  - 15:00（补充采集）
  - 23:00（补充采集）

执行内容:
  1. 采集 RSS 新闻
  2. AI 过滤和评分
  3. 存入数据库
  4. 自动备份

超时限制: 60分钟
```

#### report.yml（报告工作流）

```yaml
触发条件:
  - 采集完成后自动触发
  - 手动触发

执行内容:
  1. 读取待分析新闻
  2. 生成简要摘要报告
  3. 生成深度分析报告
  4. 生成 PDF 文件

超时限制: 45分钟
```

#### send_email.yml（邮件工作流）

```yaml
触发时间（北京时间）:
  - 08:30（每日一次）

执行内容:
  1. 查找最新报告
  2. 发送邮件（简要正文 + PDF附件）

超时限制: 15分钟
```

### 4.3 手动触发工作流

1. 进入仓库页面
2. 点击 "Actions" 标签
3. 选择要运行的工作流
4. 点击 "Run workflow"
5. 选择分支（main）
6. 点击绿色的 "Run workflow" 按钮

### 4.4 查看运行日志

1. 进入 "Actions" 页面
2. 点击正在运行或已完成的工作流
3. 展开各个步骤查看详细日志

---

## 五、Docker 部署（可选）

### 5.1 本地 Docker 测试

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 健康检查
docker-compose exec news_analyzer python scripts/health_check.py

# 停止服务
docker-compose down
```

### 5.2 Docker 配置说明

**Dockerfile** 关键配置：

```dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p data logs backups reports

# 持久化卷
VOLUME ["/app/data", "/app/logs", "/app/backups", "/app/reports"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/news.db')"

# 启动命令
CMD ["python", "run_scheduler.py"]
```

**docker-compose.yml** 关键配置：

```yaml
version: '3.8'

volumes:
  news_db:      # 数据库持久化
  news_logs:    # 日志持久化
  news_backups: # 备份持久化
  news_reports: # 报告持久化

services:
  news_analyzer:
    build: .
    volumes:
      - news_db:/app/data
      - news_logs:/app/logs
      - news_backups:/app/backups
      - news_reports:/app/reports
      - ./.env:/app/.env:ro
    environment:
      - TZ=Asia/Shanghai
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

### 5.3 云平台部署

#### 阿里云容器服务

```bash
# 1. 登录阿里云容器镜像服务
docker login --username=your-username registry.cn-hangzhou.aliyuncs.com

# 2. 标记镜像
docker tag news-analyzer:latest registry.cn-hangzhou.aliyuncs.com/your-namespace/news-analyzer:latest

# 3. 推送镜像
docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/news-analyzer:latest

# 4. 在阿里云控制台创建容器实例
```

#### 腾讯云容器服务

```bash
# 类似阿里云流程
docker login ccr.ccs.tencentyun.com
docker tag news-analyzer:latest ccr.ccs.tencentyun.com/your-namespace/news-analyzer:latest
docker push ccr.ccs.tencentyun.com/your-namespace/news-analyzer:latest
```

---

## 六、验证与监控

### 6.1 部署后验证

```bash
# 1. 检查工作流运行状态
# 进入 GitHub Actions 页面查看

# 2. 检查数据库
python -c "from storage.database import get_db; print(get_db().get_stats())"

# 3. 检查报告生成
ls -la reports/

# 4. 检查邮件发送
# 查看邮箱收件箱
```

### 6.2 监控指标

| 指标 | 检查方法 | 正常范围 |
|------|---------|---------|
| 采集成功率 | Actions 日志 | > 90% |
| 报告生成时间 | Actions 日志 | < 30分钟 |
| 数据库大小 | `du -sh data/` | < 100MB/月 |
| 备份文件数量 | `ls data/backups/` | 10-30个 |

### 6.3 定期维护

```bash
# 每周执行一次健康检查
python scripts/health_check.py

# 每月检查备份
python scripts/restore_backup.py --list

# 定期清理旧日志
find logs/ -name "*.log" -mtime +30 -delete
```

---

## 七、故障排除

### 7.1 常见问题

#### 问题1：GitHub Actions 运行失败

**症状**：工作流显示红色 ❌

**排查步骤**：
1. 点击失败的工作流查看详细日志
2. 检查 Secrets 配置是否正确
3. 检查 API 密钥是否有效
4. 检查网络连接

**解决方案**：
```bash
# 验证 API 密钥
curl -H "Authorization: Bearer $AI_ANALYSIS_KEY" \
     https://api.deepseek.com/v1/models

# 重新配置 Secrets
# Settings → Secrets → Update secret
```

#### 问题2：数据库为空

**症状**：报告显示"待分析池为空"

**排查步骤**：
1. 检查采集任务是否成功
2. 检查 RSS 源是否可访问
3. 检查 AI 过滤是否过于严格

**解决方案**：
```bash
# 手动触发采集
python run_collect.py

# 检查数据库
python -c "from storage.database import get_db; db=get_db(); print(db.get_stats())"
```

#### 问题3：邮件发送失败

**症状**：邮件未收到

**排查步骤**：
1. 检查 SMTP 配置
2. 检查授权码是否正确
3. 检查收件箱和垃圾邮件

**解决方案**：
```bash
# 测试邮件配置
python send_email.py --test

# 检查 SMTP 连接
python -c "
import smtplib
s = smtplib.SMTP('smtp.qq.com', 587)
s.starttls()
s.login('your@qq.com', 'auth_code')
print('SMTP 连接成功')
"
```

#### 问题4：备份恢复失败

**症状**：`restore_backup.py` 报错

**排查步骤**：
1. 检查备份文件是否存在
2. 检查磁盘空间
3. 检查文件权限

**解决方案**：
```bash
# 列出备份
python scripts/restore_backup.py --list

# 强制恢复
python scripts/restore_backup.py --latest --force
```

### 7.2 日志分析

```bash
# 查看最近日志
tail -100 logs/news_analyzer.log

# 搜索错误
grep "ERROR" logs/news_analyzer.log

# 查看特定模块日志
grep "AIProcessor" logs/news_analyzer.log
```

### 7.3 紧急恢复

```bash
# 1. 停止所有任务
# GitHub Actions: 取消正在运行的工作流

# 2. 从备份恢复
python scripts/restore_backup.py --latest --force

# 3. 验证数据
python scripts/health_check.py

# 4. 重新启动
python run_now.py
```

---

## 八、最佳实践

### 8.1 安全建议

1. **密钥管理**
   - 使用 GitHub Secrets 存储敏感信息
   - 定期更换 API 密钥
   - 不要在代码中硬编码密钥

2. **访问控制**
   - 使用私有仓库
   - 限制协作者权限
   - 启用两步验证

3. **数据安全**
   - 定期备份数据库
   - 加密敏感数据传输
   - 监控异常访问

### 8.2 性能优化

1. **依赖管理**
   - 使用 `requirements.lock` 锁定版本
   - 定期更新依赖
   - 清理未使用的依赖

2. **资源优化**
   - 调整批处理大小（`AI_BATCH_SIZE`）
   - 优化数据库查询
   - 清理过期数据

3. **成本控制**
   - 监控 API 调用量
   - 选择合适的模型
   - 利用免费额度

### 8.3 运维建议

1. **监控告警**
   - 设置 GitHub Actions 通知
   - 监控工作流运行时间
   - 配置失败告警

2. **文档维护**
   - 更新部署文档
   - 记录配置变更
   - 保存故障处理记录

3. **版本管理**
   - 使用 Git 标签标记版本
   - 保持主分支稳定
   - 使用分支开发新功能

---

## 附录

### A. 环境变量完整列表

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `AI_ANALYSIS_PROVIDER` | ✅ | - | 深度分析厂商 |
| `AI_ANALYSIS_MODEL` | ✅ | - | 深度分析模型 |
| `AI_ANALYSIS_KEY` | ✅ | - | 深度分析API密钥 |
| `AI_ANALYSIS_BASE_URL` | ❌ | - | API地址 |
| `AI_FILTER_PROVIDER` | ✅ | - | 快速筛选厂商 |
| `AI_FILTER_MODEL` | ✅ | - | 快速筛选模型 |
| `AI_FILTER_KEY` | ✅ | - | 快速筛选API密钥 |
| `AI_FILTER_BASE_URL` | ❌ | - | API地址 |
| `AI_BACKUP_*` | ❌ | - | 备用模型配置 |
| `SMTP_HOST` | ❌ | - | SMTP服务器 |
| `SMTP_PORT` | ❌ | 465 | SMTP端口 |
| `SMTP_USER` | ❌ | - | 发件邮箱 |
| `SMTP_PASSWORD` | ❌ | - | 邮箱授权码 |
| `EMAIL_TO` | ❌ | - | 收件人邮箱 |
| `HTTP_PROXY` | ❌ | - | HTTP代理 |
| `HTTPS_PROXY` | ❌ | - | HTTPS代理 |
| `NO_PROXY` | ❌ | - | 不代理的域名 |
| `LOG_LEVEL` | ❌ | INFO | 日志级别 |
| `AI_BATCH_SIZE` | ❌ | 4 | AI批处理大小 |
| `ENABLE_INVESTMENT_ANALYSIS` | ❌ | false | 启用投资分析 |

### B. 常用命令速查

```bash
# 本地运行
python run_now.py                    # 一键运行
python run_collect.py                # 仅采集
python run_report.py                 # 仅生成报告
python send_email.py                 # 发送邮件

# 测试验证
python scripts/test_persistence.py   # 持久化测试
python scripts/health_check.py       # 健康检查
pytest tests/ -v                     # 运行测试

# 备份恢复
python scripts/restore_backup.py --list     # 列出备份
python scripts/restore_backup.py --latest   # 恢复最新
python scripts/auto_backup.py               # 启动备份服务

# Docker
docker-compose up -d                 # 启动服务
docker-compose logs -f               # 查看日志
docker-compose down                  # 停止服务
docker-compose exec news_analyzer python scripts/health_check.py

# Git
git add . && git commit -m "update"  # 提交更改
git push origin main                 # 推送到远程
```

### C. 相关文档

- [部署指南](DEPLOYMENT.md) - 详细部署文档
- [云迁移检查清单](CLOUD_MIGRATION_CHECKLIST.md) - 部署前检查
- [架构审查报告](ARCHITECTURE_REVIEW_V3.md) - 系统架构说明
- [报告风格指南](REPORT_STYLE_GUIDE.md) - 报告格式说明

---

**部署完成后，请运行以下命令验证系统状态：**

```bash
python scripts/health_check.py
python scripts/test_persistence.py
python run_now.py
```

**祝您部署顺利！** 🚀
