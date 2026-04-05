#!/usr/bin/env python3
"""
下载并保存 BGE-M3 模型到本地
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def main():
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

    from sentence_transformers import SentenceTransformer
    from pathlib import Path

    local_path = Path(__file__).parent.parent.parent / 'models' / 'bge-m3'
    local_path.mkdir(parents=True, exist_ok=True)

    print(f"下载 BGE-M3 模型到: {local_path}")

    model = SentenceTransformer('BAAI/bge-m3')
    model.save(str(local_path))

    print(f"模型已保存到: {local_path}")
    print(f"文件列表:")
    for f in local_path.iterdir():
        print(f"  {f.name}")

if __name__ == '__main__':
    main()