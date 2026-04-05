#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

启动Web应用

"""

import sys

from pathlib import Path

base_path = Path(__file__).parent.parent

sys.path.insert(0, str(base_path))

from web.app import app

if __name__ == '__main__':

    print("=" * 60)

    print("Insight Hub Web 服务启动")

    print("=" * 60)

    print("访问地址: http://localhost:5000")

    print("管理后台: http://localhost:5000/adminadmin=true")

    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
