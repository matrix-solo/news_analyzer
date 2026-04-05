#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理工具模块
提供统一的错误处理机制，提高系统可靠性
"""

import logging
import traceback
import sys
from typing import Optional, Callable, Any, Dict, Union
from functools import wraps

logger = logging.getLogger(__name__)

class NewsAnalyzerError(Exception):
    """新闻分析器基础异常类"""

    def __init__(self, message: str, error_code: int = 500, details: Optional[Dict] = None):
        """
        初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        将异常转换为字典

        Returns:
            异常信息字典
        """
        return {
            'error_code': self.error_code,
            'message': str(self),
            'details': self.details
        }

class ConfigurationError(NewsAnalyzerError):
    """配置错误"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_code=400, details=details)

class NetworkError(NewsAnalyzerError):
    """网络错误"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_code=503, details=details)

class DatabaseError(NewsAnalyzerError):
    """数据库错误"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_code=500, details=details)

class AIError(NewsAnalyzerError):
    """AI处理错误"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_code=500, details=details)

class ValidationError(NewsAnalyzerError):
    """数据验证错误"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_code=400, details=details)

def error_handler(default_return: Any = None, log_level: int = logging.ERROR):
    """
    错误处理装饰器

    Args:
        default_return: 错误发生时的默认返回值
        log_level: 日志级别
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except NewsAnalyzerError as e:
                # 已知异常
                logger.log(log_level, f"{func.__name__} 执行失败: {e}")
                if e.details:
                    logger.log(log_level, f"错误详情: {e.details}")
                return default_return
            except Exception as e:
                # 未知异常
                logger.log(log_level, f"{func.__name__} 执行失败: {e}")
                logger.log(log_level, f"堆栈信息: {traceback.format_exc()}")
                return default_return
        return wrapper
    return decorator

def async_error_handler(default_return: Any = None, log_level: int = logging.ERROR):
    """
    异步错误处理装饰器

    Args:
        default_return: 错误发生时的默认返回值
        log_level: 日志级别
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except NewsAnalyzerError as e:
                # 已知异常
                logger.log(log_level, f"{func.__name__} 执行失败: {e}")
                if e.details:
                    logger.log(log_level, f"错误详情: {e.details}")
                return default_return
            except Exception as e:
                # 未知异常
                logger.log(log_level, f"{func.__name__} 执行失败: {e}")
                logger.log(log_level, f"堆栈信息: {traceback.format_exc()}")
                return default_return
        return wrapper
    return decorator

def handle_error_with_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    带重试的错误处理装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避系数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (NetworkError, DatabaseError) as e:
                    # 只对网络和数据库错误进行重试
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"{func.__name__} 失败，{current_delay}秒后重试... ({attempt + 1}/{max_retries})")
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} 重试{max_retries}次后仍失败: {e}")
                except Exception as e:
                    # 其他错误不重试
                    logger.error(f"{func.__name__} 执行失败: {e}")
                    raise

            if last_exception:
                raise last_exception
        return wrapper
    return decorator

def log_exception(logger: Optional[logging.Logger] = None, level: int = logging.ERROR):
    """
    异常日志记录装饰器

    Args:
        logger: 日志记录器
        level: 日志级别
    """
    def decorator(func: Callable) -> Callable:
        log = logger or logging.getLogger(func.__module__)

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.log(level, f"{func.__name__} 执行失败: {e}")
                log.log(level, f"堆栈信息: {traceback.format_exc()}")
                raise
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    安全执行函数

    Args:
        func: 要执行的函数
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        包含执行结果或错误信息的字典
    """
    try:
        result = func(*args, **kwargs)
        return {
            'success': True,
            'result': result,
            'error': None
        }
    except NewsAnalyzerError as e:
        return {
            'success': False,
            'result': None,
            'error': e.to_dict()
        }
    except Exception as e:
        return {
            'success': False,
            'result': None,
            'error': {
                'error_code': 500,
                'message': str(e),
                'details': {
                    'traceback': traceback.format_exc()
                }
            }
        }

def format_error_message(error: Union[Exception, Dict]) -> str:
    """
    格式化错误消息

    Args:
        error: 错误对象或错误字典

    Returns:
        格式化的错误消息
    """
    if isinstance(error, Exception):
        return f"{type(error).__name__}: {str(error)}"
    elif isinstance(error, dict):
        message = error.get('message', '未知错误')
        error_code = error.get('error_code', 500)
        return f"错误 {error_code}: {message}"
    return str(error)

if __name__ == "__main__":
    # 测试错误处理
    print("测试错误处理模块...")

    # 测试自定义异常
    print("\n1. 测试自定义异常:")
    try:
        raise ConfigurationError("配置文件不存在", details={"file": "config.yaml"})
    except NewsAnalyzerError as e:
        print(f"捕获到异常: {e}")
        print(f"错误代码: {e.error_code}")
        print(f"错误详情: {e.details}")
        print(f"异常转字典: {e.to_dict()}")

    # 测试错误处理装饰器
    print("\n2. 测试错误处理装饰器:")

    @error_handler(default_return="默认返回值")
    def test_function():
        raise ValueError("测试错误")

    result = test_function()
    print(f"函数执行结果: {result}")

    # 测试带重试的错误处理
    print("\n3. 测试带重试的错误处理:")

    @handle_error_with_retry(max_retries=2, delay=0.5)
    def test_retry():
        print("执行测试函数")
        raise NetworkError("网络错误")

    try:
        test_retry()
    except NetworkError as e:
        print(f"最终捕获到异常: {e}")

    # 测试安全执行
    print("\n4. 测试安全执行:")

    def success_func():
        return "执行成功"

    def error_func():
        raise ValueError("执行失败")

    result1 = safe_execute(success_func)
    print(f"成功函数执行结果: {result1}")

    result2 = safe_execute(error_func)
    print(f"错误函数执行结果: {result2}")

    # 测试格式化错误消息
    print("\n5. 测试格式化错误消息:")

    error = ValueError("测试错误")
    print(f"异常对象格式化: {format_error_message(error)}")

    error_dict = {"error_code": 400, "message": "参数错误"}
    print(f"错误字典格式化: {format_error_message(error_dict)}")

    print("\n测试完成！")
