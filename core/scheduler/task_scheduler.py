#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器
管理RSS增量抓取和每日归档的定时执行
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.collector.unified_collector import UnifiedRSSCollector


@dataclass
class ScheduledTask:
    """定时任务"""
    name: str
    func: Callable
    interval_seconds: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    run_count: int = 0
    
    def should_run(self) -> bool:
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        return datetime.now() >= self.next_run
    
    def mark_run(self):
        self.last_run = datetime.now()
        self.next_run = self.last_run + timedelta(seconds=self.interval_seconds)
        self.run_count += 1


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        self.logger = logging.getLogger("TaskScheduler")
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self.incremental_collector: Optional[UnifiedRSSCollector] = None
    
    def add_task(self, name: str, func: Callable, interval_seconds: int, enabled: bool = True):
        """添加定时任务"""
        task = ScheduledTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            enabled=enabled
        )
        self.tasks[name] = task
        self.logger.info(f"添加任务: {name} (间隔: {interval_seconds}秒)")
    
    def remove_task(self, name: str) -> bool:
        """移除任务"""
        if name in self.tasks:
            del self.tasks[name]
            self.logger.info(f"移除任务: {name}")
            return True
        return False
    
    def enable_task(self, name: str):
        """启用任务"""
        if name in self.tasks:
            self.tasks[name].enabled = True
    
    def disable_task(self, name: str):
        """禁用任务"""
        if name in self.tasks:
            self.tasks[name].enabled = False
    
    def setup_rss_tasks(self, crawl_interval: int = 1800):
        """设置RSS相关定时任务"""
        self.incremental_collector = UnifiedRSSCollector(
            incremental_mode=True,
            background_mode=False
        )
        
        self.add_task(
            name="rss_incremental_crawl",
            func=self.incremental_collector.crawl_once,
            interval_seconds=crawl_interval
        )
        
        self.add_task(
            name="rss_daily_archive",
            func=self._daily_archive_task,
            interval_seconds=3600
        )
        
        self.logger.info("RSS定时任务已配置")
    
    def _daily_archive_task(self):
        """每日归档任务"""
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        if current_time >= "00:10" and current_time <= "01:10":
            if self.incremental_collector:
                self.logger.info("执行每日归档...")
                self.incremental_collector.archive_yesterday()
    
    def start(self):
        """启动调度器"""
        if self._running:
            self.logger.warning("调度器已在运行")
            return
        
        self._running = True
        self._stop_event.clear()
        
        def _run_loop():
            self.logger.info("🚀 任务调度器启动")
            
            while not self._stop_event.is_set():
                try:
                    self._check_and_run_tasks()
                except Exception as e:
                    self.logger.error(f"任务执行异常: {e}")
                
                time.sleep(1)
            
            self.logger.info("任务调度器已停止")
        
        self._thread = threading.Thread(target=_run_loop, daemon=True)
        self._thread.start()
    
    def _check_and_run_tasks(self):
        """检查并执行到期任务"""
        for name, task in self.tasks.items():
            if task.should_run():
                try:
                    self.logger.info(f"执行任务: {name}")
                    task.func()
                    task.mark_run()
                except Exception as e:
                    self.logger.error(f"任务执行失败 {name}: {e}")
    
    def stop(self):
        """停止调度器"""
        if not self._running:
            return
        
        self._stop_event.set()
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5)
        
        if self.incremental_collector:
            self.incremental_collector.close()
        
        self.logger.info("调度器已停止")
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            'is_running': self._running,
            'tasks': {
                name: {
                    'enabled': task.enabled,
                    'interval_seconds': task.interval_seconds,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'run_count': task.run_count
                }
                for name, task in self.tasks.items()
            }
        }
    
    def run_once(self):
        """执行一次所有任务"""
        self.logger.info("执行一次所有任务...")
        for name, task in self.tasks.items():
            if task.enabled:
                try:
                    self.logger.info(f"执行: {name}")
                    task.func()
                    task.mark_run()
                except Exception as e:
                    self.logger.error(f"执行失败 {name}: {e}")


def run_scheduler_daemon(crawl_interval: int = 1800):
    """运行调度器守护进程"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = TaskScheduler()
    scheduler.setup_rss_tasks(crawl_interval)
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止...")
        scheduler.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="定时任务调度器")
    parser.add_argument('--daemon', action='store_true', help='以守护进程方式运行')
    parser.add_argument('--interval', type=int, default=1800, help='抓取间隔(秒)')
    parser.add_argument('--once', action='store_true', help='只执行一次')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if args.once:
        scheduler = TaskScheduler()
        scheduler.setup_rss_tasks(args.interval)
        scheduler.run_once()
    elif args.daemon:
        run_scheduler_daemon(args.interval)
    else:
        scheduler = TaskScheduler()
        scheduler.setup_rss_tasks(args.interval)
        scheduler.run_once()
