#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控工具模块
提供数据流监控和日志优化功能
"""

import time
import logging
import psutil
import os
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class DataFlowMonitor:
    """数据流监控器"""

    def __init__(self, name: str):
        """
        初始化数据流监控器

        Args:
            name: 监控器名称
        """
        self.name = name
        self.start_time = time.time()
        self.events: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {
            'count': 0,
            'errors': 0,
            'start_time': self.start_time,
            'last_event_time': self.start_time
        }

    def record_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """
        记录事件

        Args:
            event_type: 事件类型
            details: 事件详情
        """
        event = {
            'timestamp': time.time(),
            'event_type': event_type,
            'details': details or {}
        }
        self.events.append(event)
        self.metrics['last_event_time'] = event['timestamp']

        if event_type == 'error':
            self.metrics['errors'] += 1
        else:
            self.metrics['count'] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取监控指标

        Returns:
            监控指标字典
        """
        current_time = time.time()
        elapsed = current_time - self.start_time

        metrics = self.metrics.copy()
        metrics['elapsed'] = elapsed
        metrics['rate'] = metrics['count'] / elapsed if elapsed > 0 else 0
        metrics['error_rate'] = metrics['errors'] / (metrics['count'] + metrics['errors']) if (metrics['count'] + metrics['errors']) > 0 else 0
        metrics['events_count'] = len(self.events)

        return metrics

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的事件

        Args:
            limit: 事件数量限制

        Returns:
            最近的事件列表
        """
        return self.events[-limit:]

    def reset(self):
        """
        重置监控器
        """
        self.start_time = time.time()
        self.events.clear()
        self.metrics = {
            'count': 0,
            'errors': 0,
            'start_time': self.start_time,
            'last_event_time': self.start_time
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            监控器信息字典
        """
        return {
            'name': self.name,
            'metrics': self.get_metrics(),
            'recent_events': self.get_recent_events()
        }

class SystemMonitor:
    """系统监控器"""

    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """
        获取系统指标

        Returns:
            系统指标字典
        """
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_used = memory.used / (1024 * 1024 * 1024)  # GB
            memory_total = memory.total / (1024 * 1024 * 1024)  # GB
            memory_percent = memory.percent

            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_used = disk.used / (1024 * 1024 * 1024)  # GB
            disk_total = disk.total / (1024 * 1024 * 1024)  # GB
            disk_percent = disk.percent

            # 网络IO
            net_io = psutil.net_io_counters()

            # 进程信息
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            process_cpu = process.cpu_percent(interval=0.1)

            return {
                'cpu': {
                    'percent': cpu_percent
                },
                'memory': {
                    'used': round(memory_used, 2),
                    'total': round(memory_total, 2),
                    'percent': memory_percent
                },
                'disk': {
                    'used': round(disk_used, 2),
                    'total': round(disk_total, 2),
                    'percent': disk_percent
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv
                },
                'process': {
                    'memory_mb': round(process_memory, 2),
                    'cpu_percent': process_cpu
                },
                'timestamp': time.time()
            }
        except Exception as e:
            logger.warning(f"获取系统指标失败: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }

class LoggerOptimizer:
    """日志优化器"""

    @staticmethod
    def setup_logger(
        name: str = None,
        level: int = logging.INFO,
        log_file: str = None,
        console: bool = True
    ) -> logging.Logger:
        """
        设置优化的日志记录器

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_file: 日志文件路径
            console: 是否输出到控制台

        Returns:
            配置好的日志记录器
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # 文件处理器
        if log_file:
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    @staticmethod
    def get_rotating_logger(
        name: str = None,
        level: int = logging.INFO,
        log_file: str = None,
        max_bytes: int = 10485760,  # 10MB
        backup_count: int = 5
    ) -> logging.Logger:
        """
        获取带轮转的日志记录器

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_file: 日志文件路径
            max_bytes: 单个日志文件最大字节数
            backup_count: 备份文件数量

        Returns:
            配置好的日志记录器
        """
        from logging.handlers import RotatingFileHandler

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 轮转文件处理器
        if log_file:
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

def timing_decorator(func: Callable) -> Callable:
    """
    计时装饰器

    Args:
        func: 要装饰的函数

    Returns:
        装饰后的函数
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} 执行时间: {elapsed:.4f}秒")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败，耗时: {elapsed:.4f}秒 - {e}")
            raise
    return wrapper

def monitor_decorator(monitor_name: str = None):
    """
    监控装饰器

    Args:
        monitor_name: 监控器名称
    """
    from functools import wraps

    def decorator(func: Callable) -> Callable:
        monitor = DataFlowMonitor(monitor_name or func.__name__)

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                monitor.record_event('success', {
                    'args': str(args)[:100],
                    'kwargs': str(kwargs)[:100]
                })
                return result
            except Exception as e:
                monitor.record_event('error', {
                    'args': str(args)[:100],
                    'kwargs': str(kwargs)[:100],
                    'error': str(e)[:200]
                })
                raise

        # 添加监控器属性
        wrapper.monitor = monitor
        return wrapper

    return decorator

class MetricsExporter:
    """指标导出器"""

    def __init__(self, export_dir: str = None):
        """
        初始化指标导出器

        Args:
            export_dir: 导出目录
        """
        if export_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.export_dir = project_root / "data" / "metrics"
        else:
            self.export_dir = Path(export_dir)

        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_metrics(self, metrics: Dict[str, Any], filename: str):
        """
        导出指标

        Args:
            metrics: 指标数据
            filename: 文件名
        """
        file_path = self.export_dir / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
            logger.info(f"指标导出成功: {file_path}")
        except Exception as e:
            logger.error(f"指标导出失败: {e}")

    def export_system_metrics(self, filename: str = "system"):
        """
        导出系统指标

        Args:
            filename: 文件名前缀
        """
        metrics = SystemMonitor.get_system_metrics()
        self.export_metrics(metrics, filename)

# 全局监控实例
_data_flow_monitors: Dict[str, DataFlowMonitor] = {}

def get_data_flow_monitor(name: str) -> DataFlowMonitor:
    """
    获取数据流监控器

    Args:
        name: 监控器名称

    Returns:
        数据流监控器实例
    """
    if name not in _data_flow_monitors:
        _data_flow_monitors[name] = DataFlowMonitor(name)
    return _data_flow_monitors[name]

def get_all_monitors() -> Dict[str, DataFlowMonitor]:
    """
    获取所有监控器

    Returns:
        监控器字典
    """
    return _data_flow_monitors

def export_all_metrics(exporter: MetricsExporter):
    """
    导出所有监控器的指标

    Args:
        exporter: 指标导出器
    """
    for name, monitor in _data_flow_monitors.items():
        metrics = monitor.to_dict()
        exporter.export_metrics(metrics, f"monitor_{name}")

if __name__ == "__main__":
    # 测试监控模块
    print("测试监控模块...")

    # 测试数据流监控
    print("\n1. 测试数据流监控:")
    monitor = DataFlowMonitor("test_monitor")

    # 记录事件
    monitor.record_event('success', {"data": "test"})
    monitor.record_event('success', {"data": "test2"})
    monitor.record_event('error', {"error": "test error"})

    # 获取指标
    metrics = monitor.get_metrics()
    print(f"监控指标: {metrics}")

    # 获取最近事件
    events = monitor.get_recent_events()
    print(f"最近事件: {events}")

    # 测试系统监控
    print("\n2. 测试系统监控:")
    system_metrics = SystemMonitor.get_system_metrics()
    print(f"系统指标: {system_metrics}")

    # 测试装饰器
    print("\n3. 测试装饰器:")

    @monitor_decorator("test_function")
    @timing_decorator
    def test_function(x, y):
        time.sleep(0.1)
        return x + y

    result = test_function(1, 2)
    print(f"函数结果: {result}")
    print(f"函数监控指标: {test_function.monitor.get_metrics()}")

    # 测试指标导出
    print("\n4. 测试指标导出:")
    exporter = MetricsExporter()
    exporter.export_system_metrics()

    # 测试日志优化
    print("\n5. 测试日志优化:")
    optimized_logger = LoggerOptimizer.setup_logger(
        name="test_logger",
        level=logging.DEBUG
    )
    optimized_logger.debug("调试信息")
    optimized_logger.info("信息")
    optimized_logger.warning("警告")
    optimized_logger.error("错误")

    print("\n测试完成！")
