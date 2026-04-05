#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

运行数据库迁移,添加所有缺失的列

"""

import sys

import os

# 添加项目根目录到路径

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage.database import NewsDatabase

def main():

    print("开始数据库迁移...")

    # 初始化数据库,这会触发迁移

    db = NewsDatabase()

    print("数据库迁移完成!")

    print("检查数据库状态...")

    # 获取数据库统计信息

    stats = db.get_stats()

    print(f"总新闻数: {stats['total_news']}")

    print(f"最近24小时新闻数: {stats['recent_24h']}")

    print(f"按领域统计: {stats['by_domain']}")

    print("\n数据库迁移成功完成!")

if __name__ == "__main__":

    main()
