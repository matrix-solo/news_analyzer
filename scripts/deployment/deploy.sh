#!/bin/bash
set -e

echo "========================================"
echo "🚀 新闻分析系统部署脚本"
echo "========================================"

echo ""
echo "📋 部署前检查..."

if [ ! -f ".env" ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "请复制 .env.example 为 .env 并配置环境变量"
    exit 1
fi

if [ ! -f "sources.yaml" ]; then
    echo "❌ 错误: sources.yaml 配置文件不存在"
    exit 1
fi

echo "✅ 配置文件检查通过"

echo ""
echo "🔄 停止现有容器..."
docker-compose down || true

echo ""
echo "🏗️  构建 Docker 镜像..."
docker-compose build

echo ""
echo "🚀 启动服务..."
docker-compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 10

echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "🏥 健康检查..."
docker-compose exec news_analyzer python scripts/health_check.py || true

echo ""
echo "========================================"
echo "✅ 部署完成！"
echo "========================================"
echo ""
echo "📌 常用命令:"
echo "  查看日志:   docker-compose logs -f"
echo "  停止服务:   docker-compose down"
echo "  重启服务:   docker-compose restart"
echo "  健康检查:   docker-compose exec news_analyzer python scripts/health_check.py"
echo ""
