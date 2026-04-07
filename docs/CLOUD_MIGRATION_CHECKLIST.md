# 云迁移检查清单

## ✅ 已完成项目

### 1. 核心配置文件
- [x] Dockerfile - 容器构建配置
- [x] docker-compose.yml - 容器编排配置
- [x] .dockerignore - Docker 构建排除文件
- [x] requirements.lock - 依赖版本锁定文件

### 2. 环境变量管理
- [x] config/loader.py - 统一环境变量加载器
- [x] 支持深度分析模型配置 (AI_ANALYSIS_*)
- [x] 支持快速筛选模型配置 (AI_FILTER_*)
- [x] 支持备用模型配置 (AI_BACKUP_*)
- [x] 支持邮件配置
- [x] 支持代理配置

### 3. 日志管理
- [x] log_utils.py - 日志脱敏工具（logging_config.py 已删除，日志配置内联到各模块）
- [x] 支持按日期分割日志文件
- [x] 支持敏感信息脱敏（SanitizedLogger）
- [x] 支持敏感信息脱敏

### 4. 数据持久化
- [x] Docker 卷配置 (news_db, news_logs, news_backups, news_reports)
- [x] 数据库自动备份机制
- [x] 备份文件清理策略

### 5. 测试脚本
- [x] scripts/test_persistence.py - 持久化测试
- [x] scripts/health_check.py - 健康检查

### 6. 备份恢复
- [x] scripts/auto_backup.py - 自动备份服务
- [x] scripts/restore_backup.py - 备份恢复工具

### 7. 部署文档
- [x] docs/DEPLOYMENT.md - 详细部署指南
- [x] scripts/deploy.sh - 部署脚本

## 📋 部署前检查

### 本地环境检查
```bash
# 1. 持久化测试
python scripts/test_persistence.py
# 预期结果: 所有测试通过

# 2. 健康检查
python scripts/health_check.py
# 预期结果: 总体状态 ✅ 健康

# 3. 备份列表检查
python scripts/restore_backup.py --list
# 预期结果: 显示可用备份列表

# 4. 环境变量验证
python -c "from config.loader import env_loader; print(env_loader.get_ai_analysis_config())"
# 预期结果: 显示正确的配置信息
```

### 配置文件检查
- [ ] .env 文件存在且配置正确
- [ ] sources.yaml 文件存在且配置正确
- [ ] 所有必需的环境变量已设置

### GitHub 配置检查
- [ ] GitHub Secrets 已配置
  - AI_ANALYSIS_KEY
  - AI_FILTER_KEY
  - SMTP_HOST (可选)
  - SMTP_PORT (可选)
  - SMTP_USER (可选)
  - SMTP_PASSWORD (可选)
  - EMAIL_TO (可选)

## 🚀 部署步骤

### 方式一: Docker 本地部署
```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 健康检查
docker-compose exec news_analyzer python scripts/health_check.py
```

### 方式二: GitHub Actions 部署
```bash
# 1. 提交代码
git add .
git commit -m "准备云部署"
git push origin main

# 2. 在 GitHub Actions 页面手动触发工作流
# 或等待定时任务自动执行
```

## 📊 验证清单

### 功能验证
- [ ] 新闻采集功能正常
- [ ] 报告生成功能正常
- [ ] 邮件发送功能正常 (如已配置)
- [ ] 数据库读写正常
- [ ] 日志记录正常

### 数据验证
- [ ] 数据库文件存在
- [ ] 数据库大小正常
- [ ] 最新新闻时间合理
- [ ] 备份文件存在

### 性能验证
- [ ] 采集任务执行时间合理
- [ ] 报告生成时间合理
- [ ] 内存使用正常
- [ ] 磁盘空间充足

## ⚠️ 注意事项

### 安全
- 不要将 .env 文件提交到 Git
- 定期更换 API 密钥
- 监控异常访问

### 备份
- 定期检查备份文件
- 验证备份可恢复性
- 保留足够数量的备份

### 监控
- 定期运行健康检查
- 关注日志输出
- 监控系统资源使用

## 📞 问题排查

### 常见问题
1. **容器启动失败**
   - 检查 Docker 配置
   - 查看详细日志
   - 验证环境变量

2. **数据库连接失败**
   - 检查数据库文件
   - 验证权限设置
   - 检查磁盘空间

3. **环境变量未加载**
   - 检查 .env 文件
   - 验证文件格式
   - 确认文件编码 (UTF-8)

4. **备份恢复失败**
   - 检查备份文件完整性
   - 验证磁盘空间
   - 使用 --force 参数

## ✅ 准备就绪

当以下条件全部满足时，系统已准备好上云：

- [x] 所有配置文件已创建
- [x] 持久化测试通过
- [x] 健康检查通过
- [x] 备份机制正常
- [x] 环境变量配置正确
- [x] 部署文档完整

---

**最后更新时间**: 2026-03-13
**状态**: ✅ 准备就绪
