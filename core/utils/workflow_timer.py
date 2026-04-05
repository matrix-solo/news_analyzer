#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流时间追踪器 - 追踪工作流各环节耗时并生成日志

功能：
1. 追踪工作流各阶段耗时
2. 每次运行生成独立的时间追踪日志文件
3. 与心跳监控集成
4. 支持嵌套阶段追踪
"""

import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager

logger = logging.getLogger("WorkflowTimer")

_project_root = Path(__file__).parent.parent.parent
_timer_log_dir = _project_root / "logs" / "workflow_timers"


@dataclass
class StageMetric:
    """阶段指标"""
    name: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    status: str = "running"
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class WorkflowRun:
    """工作流运行记录"""
    workflow_name: str
    run_id: str
    start_time: str
    end_time: Optional[str] = None
    total_duration_seconds: float = 0.0
    status: str = "running"
    stages: List[StageMetric] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "run_id": self.run_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_seconds": self.total_duration_seconds,
            "status": self.status,
            "stages": [asdict(s) for s in self.stages],
            "summary": self.summary
        }


class WorkflowTimer:
    """工作流时间追踪器"""

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()
        self.current_stage: Optional[StageMetric] = None
        self.stages: List[StageMetric] = []
        self._stage_stack: List[StageMetric] = []

        _timer_log_dir.mkdir(parents=True, exist_ok=True)

    def start(self) -> "WorkflowTimer":
        """开始工作流"""
        logger.info(f"[{self.workflow_name}] 工作流开始 - {self.run_id}")
        return self

    def begin_stage(self, stage_name: str, details: Dict[str, Any] = None) -> StageMetric:
        """开始一个阶段"""
        stage = StageMetric(
            name=stage_name,
            start_time=datetime.now().isoformat(),
            details=details or {}
        )
        self._stage_stack.append(stage)
        logger.info(f"[{self.workflow_name}] 阶段开始: {stage_name}")
        return stage

    def end_stage(self, stage_name: str = None, status: str = "success",
                  details: Dict[str, Any] = None, error: str = None) -> Optional[StageMetric]:
        """结束当前阶段"""
        if not self._stage_stack:
            logger.warning(f"[{self.workflow_name}] 没有正在进行的阶段")
            return None

        stage = self._stage_stack.pop()
        if stage_name and stage.name != stage_name:
            logger.warning(f"[{self.workflow_name}] 阶段名称不匹配: {stage.name} vs {stage_name}")

        now = datetime.now()
        start = datetime.fromisoformat(stage.start_time)
        stage.end_time = now.isoformat()
        stage.duration_seconds = (now - start).total_seconds()
        stage.status = status
        stage.error = error

        if details:
            stage.details.update(details)

        self.stages.append(stage)

        status_icon = "✅" if status == "success" else "❌"
        logger.info(
            f"[{self.workflow_name}] 阶段结束: {stage.name} "
            f"{status_icon} 耗时: {stage.duration_seconds:.2f}s"
        )

        return stage

    def finish(self, status: str = "success", summary: Dict[str, Any] = None) -> WorkflowRun:
        """完成工作流"""
        now = datetime.now()
        total_duration = (now - self.start_time).total_seconds()

        run = WorkflowRun(
            workflow_name=self.workflow_name,
            run_id=self.run_id,
            start_time=self.start_time.isoformat(),
            end_time=now.isoformat(),
            total_duration_seconds=total_duration,
            status=status,
            stages=self.stages,
            summary=summary or {}
        )

        self._save_run(run)
        self._print_summary(run)

        return run

    def _save_run(self, run: WorkflowRun):
        """保存运行记录到文件"""
        log_file = _timer_log_dir / f"{self.workflow_name}_{self.run_id}.json"
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(run.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"[{self.workflow_name}] 时间追踪日志已保存: {log_file}")
        except Exception as e:
            logger.error(f"保存时间追踪日志失败: {e}")

    def _print_summary(self, run: WorkflowRun):
        """打印运行摘要"""
        logger.info("=" * 70)
        logger.info(f"📊 [{self.workflow_name}] 工作流时间追踪报告")
        logger.info(f"运行ID: {self.run_id}")
        logger.info(f"状态: {run.status}")
        logger.info(f"总耗时: {run.total_duration_seconds:.2f}秒 ({run.total_duration_seconds/60:.1f}分钟)")
        logger.info("-" * 70)

        if self.stages:
            logger.info("各阶段耗时明细:")
            for stage in self.stages:
                status_icon = "✅" if stage.status == "success" else "❌"
                pct = (stage.duration_seconds / run.total_duration_seconds * 100) if run.total_duration_seconds > 0 else 0
                logger.info(
                    f"  {status_icon} {stage.name}: {stage.duration_seconds:.2f}s ({pct:.1f}%)"
                )
                if stage.details:
                    for k, v in stage.details.items():
                        if v is not None:
                            logger.info(f"      └─ {k}: {v}")
                if stage.error:
                    logger.info(f"      └─ 错误: {stage.error}")

        logger.info("=" * 70)

    @contextmanager
    def stage(self, stage_name: str, details: Dict[str, Any] = None):
        """阶段上下文管理器"""
        self.begin_stage(stage_name, details)
        error = None
        status = "success"
        try:
            yield
        except Exception as e:
            error = str(e)
            status = "failed"
            raise
        finally:
            self.end_stage(stage_name, status=status, error=error)

    def add_summary(self, key: str, value: Any):
        """添加摘要信息"""
        pass


def get_timer_logs(workflow_name: str = None, limit: int = 10) -> List[Dict]:
    """获取历史时间追踪日志"""
    logs = []
    pattern = f"{workflow_name}_*.json" if workflow_name else "*.json"

    for f in sorted(_timer_log_dir.glob(pattern), reverse=True)[:limit]:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                logs.append(json.load(fp))
        except Exception:
            pass

    return logs


def cleanup_old_logs(days: int = 30):
    """清理旧的时间追踪日志"""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)

    for f in _timer_log_dir.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                logger.info(f"清理旧日志: {f}")
        except Exception:
            pass
