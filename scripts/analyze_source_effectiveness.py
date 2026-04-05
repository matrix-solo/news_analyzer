#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

信源有效性分析工具

分析监控数据,生成信源有效性报告,为信源配置调整提供建议

"""

import os

import sys

import json

import logging

from datetime import datetime, timedelta

from pathlib import Path

from typing import Dict, List, Optional

# 添加项目根目录到Python路径

sys.path.insert(0, str(Path(__file__).parent.parent))

from health_monitor.monitoring_data import get_monitoring_manager

from health_monitor.health_monitor import get_health_monitor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger("SourceEffectivenessAnalyzer")

class SourceEffectivenessAnalyzer:

    """信源有效性分析器"""

    def __init__(self):

        self.monitoring_manager = get_monitoring_manager()

        self.health_monitor = get_health_monitor()

    def analyze_sources(self, days: int = 7) -> Dict:

        """

        分析信源有效性

        Args:

            days: 分析的天数

        Returns:

            分析结果

        """

        analysis = {

            'generated_at': datetime.now().isoformat(),

            'analysis_period': f"最近{days}天",

            'sources': {},

            'overall': {

                'total_sources': 0,

                'healthy_sources': 0,

                'degraded_sources': 0,

                'problematic_sources': 0

            }

        }

        # 获取所有信源的健康状态

        all_health = self.health_monitor.get_all_health()

        for source_name, health in all_health.items():

            # 获取历史监控数据

            history = self.monitoring_manager.get_source_history(source_name, days)

            source_analysis = self._analyze_source(source_name, health, history)

            analysis['sources'][source_name] = source_analysis

        # 统计整体情况

        analysis['overall']['total_sources'] = len(analysis['sources'])

        analysis['overall']['healthy_sources'] = sum(1 for s in analysis['sources'].values() if s['status'] == 'healthy')

        analysis['overall']['degraded_sources'] = sum(1 for s in analysis['sources'].values() if s['status'] == 'degraded')

        analysis['overall']['problematic_sources'] = sum(1 for s in analysis['sources'].values() if s['status'] == 'problematic')

        return analysis

    def _analyze_source(self, source_name: str, health: any, history: List[Dict]) -> Dict:

        """

        分析单个信源

        Args:

            source_name: 源名称

            health: 健康状态

            history: 历史监控数据

        Returns:

            信源分析结果

        """

        analysis = {

            'status': 'healthy',

            'communication': {

                'success_rate': 0.0,

                'avg_response_time': 0.0,

                'issues': []

            },

            'data_return': {

                'success_rate': 0.0,

                'issues': []

            },

            'parsing': {

                'success_rate': 0.0,

                'issues': []

            },

            'timeliness': {

                'success_rate': 0.0,

                'avg_news_age': 0.0,

                'max_news_age': 0.0,

                'timeliness_rate': 0.0,

                'issues': []

            },

            'overall_health': 0.0,

            'recommendations': []

        }

        if not history:

            analysis['status'] = 'no_data'

            analysis['recommendations'].append("无监控数据,请先进行采集")

            return analysis

        # 分析历史数据

        communication_success = sum(1 for r in history if r['communication_status'])

        data_return_success = sum(1 for r in history if r['data_return_status'])

        parsing_success = sum(1 for r in history if r['parsing_status'])

        timeliness_success = sum(1 for r in history if r['timeliness_status'])

        total_records = len(history)

        analysis['communication']['success_rate'] = communication_success / total_records

        analysis['data_return']['success_rate'] = data_return_success / total_records

        analysis['parsing']['success_rate'] = parsing_success / total_records

        analysis['timeliness']['success_rate'] = timeliness_success / total_records

        # 计算平均响应时间

        response_times = [r['response_time'] for r in history if r['response_time'] > 0]

        if response_times:

            analysis['communication']['avg_response_time'] = sum(response_times) / len(response_times)

        # 计算时效性指标

        avg_news_ages = [r['avg_news_age'] for r in history if r['avg_news_age'] > 0]

        max_news_ages = [r['max_news_age'] for r in history if r['max_news_age'] > 0]

        timeliness_rates = [r['timeliness_rate'] for r in history if r['timeliness_rate'] > 0]

        if avg_news_ages:

            analysis['timeliness']['avg_news_age'] = sum(avg_news_ages) / len(avg_news_ages)

        if max_news_ages:

            analysis['timeliness']['max_news_age'] = max(max_news_ages)

        if timeliness_rates:

            analysis['timeliness']['timeliness_rate'] = sum(timeliness_rates) / len(timeliness_rates)

        # 计算综合健康度

        overall_health = self.health_monitor.get_overall_health(source_name)

        analysis['overall_health'] = overall_health

        # 评估状态

        if overall_health >= 0.8:

            analysis['status'] = 'healthy'

        elif overall_health >= 0.5:

            analysis['status'] = 'degraded'

        else:

            analysis['status'] = 'problematic'

        # 生成建议

        self._generate_recommendations(analysis, health)

        return analysis

    def _generate_recommendations(self, analysis: Dict, health: any):

        """

        生成建议

        Args:

            analysis: 分析结果

            health: 健康状态

        """

        recommendations = []

        # 通信问题

        if analysis['communication']['success_rate'] < 0.8:

            recommendations.append("通信成功率低,建议检查网络连接或代理设置")

        if analysis['communication']['avg_response_time'] > 5:

            recommendations.append("响应时间过长,建议检查网络或源服务器状态")

        # 数据返回问题

        if analysis['data_return']['success_rate'] < 0.8:

            recommendations.append("数据返回成功率低,建议检查源URL是否有效")

        # 解析问题

        if analysis['parsing']['success_rate'] < 0.8:

            recommendations.append("解析成功率低,建议检查源的XML格式是否规范")

        # 时效性问题

        if analysis['timeliness']['timeliness_rate'] < 0.7:

            recommendations.append("时效性合格率低,建议检查源是否正常更新")

        if analysis['timeliness']['avg_news_age'] > 7:

            recommendations.append("平均新闻年龄超过7天,建议考虑更换源或禁用")

        if analysis['timeliness']['max_news_age'] > 14:

            recommendations.append("存在超过14天的旧新闻,建议检查源的更新机制")

        # 综合建议

        if analysis['status'] == 'problematic':

            recommendations.append("信源状态严重问题,建议暂时禁用并寻找替代源")

        elif analysis['status'] == 'degraded':

            recommendations.append("信源状态降级,建议重点监控并尝试优化")

        analysis['recommendations'] = recommendations

    def generate_report(self, days: int = 7) -> str:

        """

        生成分析报告

        Args:

            days: 分析的天数

        Returns:

            报告字符串

        """

        analysis = self.analyze_sources(days)

        lines = []

        lines.append("=" * 80)

        lines.append("信源有效性分析报告")

        lines.append("=" * 80)

        lines.append(f"生成时间: {analysis['generated_at']}")

        lines.append(f"分析周期: {analysis['analysis_period']}")

        lines.append("")

        # 整体情况

        lines.append("-" * 80)

        lines.append("整体情况:")

        lines.append(f"总信源数: {analysis['overall']['total_sources']}")

        lines.append(f"健康信源: {analysis['overall']['healthy_sources']}")

        lines.append(f"降级信源: {analysis['overall']['degraded_sources']}")

        lines.append(f"问题信源: {analysis['overall']['problematic_sources']}")

        lines.append("")

        # 详细分析

        lines.append("-" * 80)

        lines.append("详细分析:")

        lines.append("")

        for source_name, source_analysis in analysis['sources'].items():

            lines.append(f"信源: {source_name}")

            lines.append(f"状态: {source_analysis['status']}")

            lines.append(f"综合健康度: {source_analysis['overall_health']:.2f}")

            lines.append("")

            lines.append("  通信状态:")

            lines.append(f"    成功率: {source_analysis['communication']['success_rate']:.2f}")

            lines.append(f"    平均响应时间: {source_analysis['communication']['avg_response_time']:.2f}秒")

            lines.append("  数据返回:")

            lines.append(f"    成功率: {source_analysis['data_return']['success_rate']:.2f}")

            lines.append("  解析状态:")

            lines.append(f"    成功率: {source_analysis['parsing']['success_rate']:.2f}")

            lines.append("  时效性:")

            lines.append(f"    成功率: {source_analysis['timeliness']['success_rate']:.2f}")

            lines.append(f"    平均新闻年龄: {source_analysis['timeliness']['avg_news_age']:.1f}天")

            lines.append(f"    最大新闻年龄: {source_analysis['timeliness']['max_news_age']:.1f}天")

            lines.append(f"    时效性合格率: {source_analysis['timeliness']['timeliness_rate']:.2f}")

            if source_analysis['recommendations']:

                lines.append("  建议:")

                for recommendation in source_analysis['recommendations']:

                    lines.append(f"    - {recommendation}")

            lines.append("")

        return "\n".join(lines)

    def save_report(self, days: int = 7, output_dir: str = None):

        """

        保存分析报告

        Args:

            days: 分析的天数

            output_dir: 输出目录

        """

        output_dir = Path(output_dir or Path(__file__).parent.parent / "data" / "reports")

        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成分析数据

        analysis = self.analyze_sources(days)

        # 保存JSON数据

        json_file = output_dir / f"source_effectiveness_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"

        with open(json_file, 'w', encoding='utf-8') as f:

            json.dump(analysis, f, ensure_ascii=False, indent=2)

        # 保存文本报告

        report_file = output_dir / f"source_effectiveness_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

        report_content = self.generate_report(days)

        with open(report_file, 'w', encoding='utf-8') as f:

            f.write(report_content)

        logger.info(f"分析报告已保存: {json_file}")

        logger.info(f"文本报告已保存: {report_file}")

        return str(report_file)

def main():

    """主函数"""

    analyzer = SourceEffectivenessAnalyzer()

    # 分析最近7天的数据

    report_file = analyzer.save_report(days=7)

    # 打印报告路径

    print(f"\n分析完成!报告已保存至:")

    print(f"{report_file}")

    # 打印简要报告

    print("\n\n" + "=" * 80)

    print("信源有效性分析摘要")

    print("=" * 80)

    analysis = analyzer.analyze_sources(days=7)

    print(f"分析周期: {analysis['analysis_period']}")

    print(f"总信源数: {analysis['overall']['total_sources']}")

    print(f"健康信源: {analysis['overall']['healthy_sources']}")

    print(f"降级信源: {analysis['overall']['degraded_sources']}")

    print(f"问题信源: {analysis['overall']['problematic_sources']}")

    # 打印问题信源

    problematic_sources = [name for name, info in analysis['sources'].items() if info['status'] == 'problematic']

    if problematic_sources:

        print("\n问题信源:")

        for source in problematic_sources:

            print(f"  - {source}")

    print("\n详细报告请查看生成的文件。")

if __name__ == "__main__":

    main()
