#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存工具模块
提供内存缓存、文件缓存等功能，减少重复计算和IO操作
"""

import time
import hashlib
import json
from typing import Any, Dict, Optional, Union, Callable
from functools import wraps
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MemoryCache:
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        初始化内存缓存

        Args:
            max_size: 缓存最大容量
            ttl: 缓存过期时间（秒）
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._lock = {}  # 简单的线程安全锁

    def _get_key(self, key: Union[str, Any]) -> str:
        """
        获取缓存键

        Args:
            key: 缓存键，可以是字符串或其他可序列化对象

        Returns:
            标准化的缓存键
        """
        if isinstance(key, str):
            return key
        try:
            return hashlib.md5(json.dumps(key, sort_keys=True).encode()).hexdigest()
        except:
            return str(key)

    def get(self, key: Union[str, Any]) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期则返回None
        """
        cache_key = self._get_key(key)

        if cache_key not in self._cache:
            return None

        item = self._cache[cache_key]
        if time.time() > item['expires_at']:
            del self._cache[cache_key]
            return None

        return item['value']

    def set(self, key: Union[str, Any], value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果不指定则使用默认值
        """
        cache_key = self._get_key(key)

        # 检查缓存大小
        if len(self._cache) >= self._max_size:
            # 删除过期项
            self._clean_expired()
            # 如果还是满了，删除最早的项
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k]['created_at'])
                del self._cache[oldest_key]

        self._cache[cache_key] = {
            'value': value,
            'created_at': time.time(),
            'expires_at': time.time() + (ttl or self._ttl)
        }

    def delete(self, key: Union[str, Any]) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        cache_key = self._get_key(key)
        if cache_key in self._cache:
            del self._cache[cache_key]
            return True
        return False

    def clear(self) -> None:
        """
        清空缓存
        """
        self._cache.clear()

    def _clean_expired(self) -> int:
        """
        清理过期项

        Returns:
            清理的项数
        """
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if v['expires_at'] < now]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def size(self) -> int:
        """
        获取缓存大小

        Returns:
            缓存项数
        """
        self._clean_expired()
        return len(self._cache)

class FileCache:
    """文件缓存实现"""

    def __init__(self, cache_dir: str = None, ttl: int = 86400):
        """
        初始化文件缓存

        Args:
            cache_dir: 缓存目录
            ttl: 缓存过期时间（秒）
        """
        if cache_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self._cache_dir = project_root / "data" / "cache"
        else:
            self._cache_dir = Path(cache_dir)

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl

    def _get_file_path(self, key: Union[str, Any]) -> Path:
        """
        获取缓存文件路径

        Args:
            key: 缓存键

        Returns:
            缓存文件路径
        """
        if isinstance(key, str):
            key_str = key
        else:
            try:
                key_str = hashlib.md5(json.dumps(key, sort_keys=True).encode()).hexdigest()
            except:
                key_str = str(key)

        # 确保文件名安全
        safe_key = key_str.replace('/', '_').replace('\\', '_')
        return self._cache_dir / f"{safe_key}.json"

    def get(self, key: Union[str, Any]) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期则返回None
        """
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if time.time() > data.get('expires_at', 0):
                file_path.unlink(missing_ok=True)
                return None

            return data.get('value')
        except Exception as e:
            logger.warning(f"读取文件缓存失败: {e}")
            file_path.unlink(missing_ok=True)
            return None

    def set(self, key: Union[str, Any], value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果不指定则使用默认值

        Returns:
            是否设置成功
        """
        file_path = self._get_file_path(key)

        try:
            data = {
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + (ttl or self._ttl)
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            logger.warning(f"写入文件缓存失败: {e}")
            return False

    def delete(self, key: Union[str, Any]) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        file_path = self._get_file_path(key)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except:
                return False
        return False

    def clear(self) -> None:
        """
        清空缓存
        """
        for file in self._cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass

    def _clean_expired(self) -> int:
        """
        清理过期项

        Returns:
            清理的项数
        """
        now = time.time()
        count = 0

        for file in self._cache_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if time.time() > data.get('expires_at', 0):
                    file.unlink()
                    count += 1
            except:
                file.unlink()
                count += 1

        return count

def cached(ttl: int = 3600, cache_type: str = "memory"):
    """
    缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        cache_type: 缓存类型，可选 "memory" 或 "file"
    """
    def decorator(func: Callable) -> Callable:
        # 为每个函数创建独立的缓存实例
        if cache_type == "file":
            cache = FileCache(ttl=ttl)
        else:
            cache = MemoryCache(ttl=ttl)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs
            }

            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"从缓存获取 {func.__name__} 的结果")
                return cached_result

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache.set(cache_key, result, ttl=ttl)
            logger.debug(f"缓存 {func.__name__} 的结果")

            return result

        return wrapper

# 全局缓存实例
memory_cache = MemoryCache()
file_cache = FileCache()

def get_cache(cache_type: str = "memory") -> Union[MemoryCache, FileCache]:
    """
    获取缓存实例

    Args:
        cache_type: 缓存类型，可选 "memory" 或 "file"

    Returns:
        缓存实例
    """
    if cache_type == "file":
        return file_cache
    return memory_cache

if __name__ == "__main__":
    # 测试内存缓存
    print("测试内存缓存...")
    mem_cache = MemoryCache(max_size=10, ttl=5)

    # 设置缓存
    mem_cache.set("key1", "value1")
    mem_cache.set("key2", "value2")

    # 获取缓存
    print(f"key1: {mem_cache.get('key1')}")
    print(f"key2: {mem_cache.get('key2')}")
    print(f"key3: {mem_cache.get('key3')}")

    # 测试过期
    print("等待6秒...")
    time.sleep(6)
    print(f"key1 (过期后): {mem_cache.get('key1')}")

    # 测试文件缓存
    print("\n测试文件缓存...")
    file_cache = FileCache(ttl=5)

    # 设置缓存
    file_cache.set("file_key1", "file_value1")

    # 获取缓存
    print(f"file_key1: {file_cache.get('file_key1')}")

    # 测试装饰器
    print("\n测试缓存装饰器...")

    @cached(ttl=2)
    def slow_function(x, y):
        print(f"执行 slow_function({x}, {y})")
        time.sleep(1)
        return x + y

    # 第一次执行（应该执行函数）
    start = time.time()
    result1 = slow_function(1, 2)
    print(f"结果: {result1}, 耗时: {time.time() - start:.2f}秒")

    # 第二次执行（应该从缓存获取）
    start = time.time()
    result2 = slow_function(1, 2)
    print(f"结果: {result2}, 耗时: {time.time() - start:.2f}秒")

    # 等待缓存过期
    print("等待3秒...")
    time.sleep(3)

    # 第三次执行（应该重新执行函数）
    start = time.time()
    result3 = slow_function(1, 2)
    print(f"结果: {result3}, 耗时: {time.time() - start:.2f}秒")

    print("\n测试完成！")
