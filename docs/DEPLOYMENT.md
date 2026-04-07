# 新闻分析系统云部署指南

## 一、部署前准备

### 1. 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.9+ (本地开发环境)
- Git

### 2. 配置文件准备

#### 2.1 环境变量配置
复制 `.env.example` 为 `.env` 并配置以下变量：

```bash
# AI 模型配置
AI_ANALYSIS_PROVIDER=deepseek
AI_ANALYSIS_MODEL=deepseek-reasoner
AI_ANALYSIS_KEY=your-api-key
AI_ANALYSIS_BASE_URL=https://api.deepseek.com/v1

AI_FILTER_PROVIDER=doubao
AI_FILTER_MODEL=doubao-seed-2-0-lite-260215
AI_FILTER_KEY=your-doubao-api-key
AI_FILTER_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 邮件配置（可选）
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_auth_code
EMAIL_TO=recipient@example.com

# 代理配置（可选）
HTTP_PROXY=http://127.0.0.1:port
HTTPS_PROXY=http://127.0.0.1:port
```

#### 2.2 新闻源配置
确保 `sources.yaml` 文件存在并配置正确。

### 3. 数据备份
部署前建议备份现有数据：

```bash
python -c "from storage.database import get_db; get_db().backup_database()"
```

## 二、本地测试

### 1. 持久化测试
```bash
python scripts/test_persistence.py
```

### 2. 健康检查
```bash
python scripts/health_check.py
```

### 3. 功能测试
```bash
# 测试采集
python run_collect.py

# 测试报告生成
python run_report.py

# 测试邮件发送
python send_email.py
```

## 三、Docker 部署

### 1. 构建镜像
```bash
docker-compose build
```

### 2. 启动服务
```bash
docker-compose up -d
```

### 3. 查看日志
```bash
docker-compose logs -f
```

### 4. 停止服务
```bash
docker-compose down
```

## 四、云平台部署

### GitHub Actions 部署

项目已配置 GitHub Actions 工作流，支持自动部署：

1. **采集任务** (`.github/workflows/collect.yml`)
   - 每天早上 7:00、下午 3:00、晚上 11:00 执行
   - 手动触发：`workflow_dispatch`

2. **报告生成** (`.github/workflows/report.yml`)
   - 采集完成后自动执行
   - 手动触发：`workflow_dispatch`

3. **邮件发送** (`.github/workflows/send_email.yml`)
   - 报告生成后自动执行
   - 手动触发：`workflow_dispatch`

### GitHub Secrets 配置

在 GitHub 仓库设置中配置以下 Secrets：

```
AI_ANALYSIS_KEY
AI_FILTER_KEY
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
EMAIL_TO
```

### 部署步骤

1. **推送代码到 GitHub**
   ```bash
   git add .
   git commit -m "准备云部署"
   git push origin main
   ```

2. **配置 GitHub Secrets**
   - 进入仓库 Settings → Secrets and variables → Actions
   - 添加所有必需的环境变量

3. **手动触发工作流**
   - 进入 Actions 页面
   - 选择对应的工作流
   - 点击 "Run workflow"

4. **查看执行日志**
   - 点击正在运行的工作流
   - 查看详细日志输出

## 五、数据持久化

### 1. 本地持久化
- 数据库：`data/news.db`
- 日志：`logs/`
- 备份：`data/backups/`
- 报告：`reports/`

### 2. Docker 卷持久化
```yaml
volumes:
  - news_db:/app/data
  - news_logs:/app/logs
  - news_backups:/app/backups
  - news_reports:/app/reports
```

### 3. GitHub Actions 持久化
- 使用 `actions/upload-artifact` 保存数据
- 使用 `actions/cache` 缓存依赖

## 六、备份与恢复

### 1. 自动备份
```bash
# 启动备份服务
python scripts/auto_backup.py
```

### 2. 手动备份
```bash
python -c "from storage.database import get_db; get_db().backup_database()"
```

### 3. 查看备份列表
```bash
python scripts/restore_backup.py --list
```

### 4. 恢复数据
```bash
# 使用最新备份
python scripts/restore_backup.py --latest --force

# 使用指定备份
python scripts/restore_backup.py --file news.db.backup_20260313_120000 --force
```

## 七、监控与维护

### 1. 健康检查
```bash
python scripts/health_check.py
```

### 2. 日志查看
```bash
# Docker 日志
docker-compose logs -f

# 应用日志
tail -f logs/news_analyzer.log
```

### 3. 性能监控
```bash
# 容器资源使用
docker stats news_analyzer

# 磁盘使用
du -sh data/ logs/ backups/ reports/
```

## 八、故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 查看详细日志
docker-compose logs news_analyzer

# 检查配置文件
docker-compose config
```

#### 2. 数据库连接失败
```bash
# 检查数据库文件
ls -la data/news.db

# 测试数据库连接
python -c "import sqlite3; sqlite3.connect('data/news.db')"
```

#### 3. 环境变量未加载
```bash
# 检查 .env 文件
cat .env

# 验证环境变量
python scripts/check_env.py
```

#### 4. 备份恢复失败
```bash
# 检查备份文件
python scripts/restore_backup.py --list

# 强制恢复
python scripts/restore_backup.py --latest --force
```

## 九、安全建议

### 1. 敏感信息保护
- 不要将 `.env` 文件提交到 Git
- 使用 GitHub Secrets 存储敏感信息
- 定期更换 API 密钥

### 2. 访问控制
- 限制 Docker 容器网络访问
- 使用防火墙规则限制端口访问
- 启用日志审计

### 3. 数据安全
- 定期备份数据库
- 加密敏感数据传输
- 监控异常访问

## 十、性能优化

### 1. 数据库优化
- 定期清理过期数据
- 重建索引
- 优化查询语句

### 2. 容器优化
- 限制容器资源使用
- 使用多阶段构建
- 优化镜像大小

### 3. 缓存策略
- 缓存依赖包
- 缓存中间结果
- 使用 CDN 加速

## 十一、升级与迁移

### 1. 版本升级
```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```

### 2. 数据迁移
```bash
# 导出数据
python scripts/export_and_rebuild.py

# 导入数据
python scripts/import_sql.py
```

## 十二、联系与支持

如遇到问题，请：
1. 查看日志文件
2. 运行健康检查
3. 参考故障排除指南
4. 提交 Issue 到 GitHub

---

**部署完成后，请运行以下命令验证系统状态：**

```bash
# 健康检查
python scripts/health_check.py

# 持久化测试
python scripts/test_persistence.py

# 功能测试
python run_now.py
```
