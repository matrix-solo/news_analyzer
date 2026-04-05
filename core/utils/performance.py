#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具模块
"""

import time
import logging
import functools
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""
    function_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error: Optional[str] = None


# 全局性能指标存储
_performance_metrics: list = []


def get_performance_metrics() -> list:
    """获取所有性能指标"""
    return _performance_metrics.copy()


def clear_performance_metrics():
    """清空性能指标"""
    global _performance_metrics
    _performance_metrics = []


def timed(func: Optional[Callable] = None, *, log_level: int = logging.INFO):
    """
    性能监控装饰器
    
    用法：
        @timed
        def my_function():
            pass
        
        @timed(log_level=logging.DEBUG)
        def my_function():
            pass
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            start = time.perf_counter()
            
            success = True
            error_msg = None
            
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                end = time.perf_counter()
                end_time = datetime.now()
                duration_ms = (end - start) * 1000
                
                # 记录性能指标
                metric = PerformanceMetric(
                    function_name=fn.__name__,
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg
                )
                _performance_metrics.append(metric)
                
                # 记录日志
                status = "完成" if success else f"失败: {error_msg}"
                logger.log(
                    log_level,
                    f"[性能监控] {fn.__name__} 执行{status}，耗时: {duration_ms:.2f}ms"
                )
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def timed_async(func: Optional[Callable] = None, *, log_level: int = logging.INFO):
    """
    异步函数性能监控装饰器
    
    用法：
        @timed_async
        async def my_function():
            pass
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            start = time.perf_counter()
            
            success = True
            error_msg = None
            
            try:
                result = await fn(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                end = time.perf_counter()
                end_time = datetime.now()
                duration_ms = (end - start) * 1000
                
                metric = PerformanceMetric(
                    function_name=fn.__name__,
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg
                )
                _performance_metrics.append(metric)
                
                status = "完成" if success else f"失败: {error_msg}"
                logger.log(
                    log_level,
                    f"[性能监控] {fn.__name__} 执行{status}，耗时: {duration_ms:.2f}ms"
                )
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


class PerformanceMonitor:
    """性能监控上下文管理器"""
    
    def __init__(self, name: str, log_level: int = logging.INFO):
        self.name = name
        self.log_level = log_level
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        end = time.perf_counter()
        self.duration_ms = (end - self._start) * 1000
        
        success = exc_type is None
        error_msg = str(exc_val) if exc_val else None
        
        metric = PerformanceMetric(
            function_name=self.name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=self.duration_ms,
            success=success,
            error=error_msg
        )
        _performance_metrics.append(metric)
        
        status = "完成" if success else f"失败: {error_msg}"
        logger.log(
            self.log_level,
            f"[性能监控] {self.name} 执行{status}，耗时: {self.duration_ms:.2f}ms"
        )
        
        return False  # 不抑制异常


def get_performance_summary() -> Dict[str, Any]:
    """
    获取性能统计摘要
    
    Returns:
        包含各函数平均耗时、最大耗时、最小耗时的统计信息
    """
    if not _performance_metrics:
        return {}
    
    stats = {}
    
    for metric in _performance_metrics:
        name = metric.function_name
        
        if name not in stats:
            stats[name] = {
                'count': 0,
                'total_ms': 0,
                'max_ms': 0,
                'min_ms': float('inf'),
                'success_count': 0,
                'error_count': 0
            }
        
        stats[name]['count'] += 1
        stats[name]['total_ms'] += metric.duration_ms
        stats[name]['max_ms'] = max(stats[name]['max_ms'], metric.duration_ms)
        stats[name]['min_ms'] = min(stats[name]['min_ms'], metric.duration_ms)
        
        if metric.success:
            stats[name]['success_count'] += 1
        else:
            stats[name]['error_count'] += 1
    
    # 计算平均值
    for name, data in stats.items():
        data['avg_ms'] = data['total_ms'] / data['count'] if data['count'] > 0 else 0
    
    return stats


def log_performance_summary():
    """记录性能统计摘要到日志"""
    summary = get_performance_summary()
    
    if not summary:
        logger.info("[性能监控] 暂无性能数据")
        return
    
    logger.info("=" * 60)
    logger.info("[性能监控] 性能统计摘要")
    logger.info("=" * 60)
    
    for name, data in summary.items():
        logger.info(
            f"{name}: "
            f"调用{data['count']}次, "
            f"平均{data['avg_ms']:.2f}ms, "
            f"最大{data['max_ms']:.2f}ms, "
            f"最小{data['min_ms']:.2f}ms, "
            f"成功{data['success_count']}次, "
            f"失败{data['error_count']}次"
        )
    
    logger.info("=" * 60)
