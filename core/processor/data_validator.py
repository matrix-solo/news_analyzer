# -*- coding: utf-8 -*-
import logging
from typing import Dict, Any, Optional, Callable

from core.utils.defaults import DefaultValues

logger = logging.getLogger(__name__)


class DataValidator:

    VALID_DOMAINS = ['政治', '经济', '科技', '军事', '社会', '文化', '体育', '娱乐']

    def __init__(self, ai_provider: Optional[Callable] = None):
        self.ai_provider = ai_provider

    def validate_combined_result(self, news, result):

        validation_rules = {

            'translation': self._validate_translation,

            'summary': self._validate_summary,

            'analysis': self._validate_analysis,

            'scoring': self._validate_scoring,

            'domain': self._validate_domain

        }

        validation_results = {}

        for field, validator in validation_rules.items():

            if field in result:

                validation_results[field] = validator(result[field])

            else:

                validation_results[field] = {'status': 'error', 'message': f'字段 {field} 缺失'}

        has_errors = any(v['status'] == 'error' for v in validation_results.values())

        if has_errors:

            remediation_result = self._attempt_ai_remediation(news, result, validation_results)

            if remediation_result:

                return {'status': 'remediated', 'results': validation_results, 'remediation': remediation_result}

            else:

                default_values = self._fill_default_values(result, validation_results)

                return {'status': 'default_filled', 'results': validation_results, 'default_values': default_values}

        return {'status': 'valid', 'results': validation_results}

    def _validate_translation(self, translation):

        if translation:

            return {'status': 'valid'}

        return {'status': 'error', 'message': '翻译结果为空'}

    def _validate_summary(self, summary):

        if summary:

            return {'status': 'valid'}

        return {'status': 'error', 'message': '摘要结果为空'}

    def _validate_analysis(self, analysis):

        if not analysis:

            return {'status': 'error', 'message': '分析结果为空'}

        w5h1_fields = ['who', 'what', 'when', 'where', 'why', 'how']

        missing_fields = [field for field in w5h1_fields if field not in analysis or not analysis[field]]

        if missing_fields:

            return {'status': 'error', 'message': f'缺失5W1H字段: {missing_fields}'}

        return {'status': 'valid'}

    def _validate_scoring(self, scoring):

        if not scoring:

            return {'status': 'error', 'message': '评分结果为空'}

        required_scores = ['influence_score', 'value_score']

        missing_scores = [score for score in required_scores if score not in scoring]

        if missing_scores:

            return {'status': 'error', 'message': f'缺失评分字段: {missing_scores}'}

        return {'status': 'valid'}

    def _validate_domain(self, domain):

        if not domain:

            return {'status': 'error', 'message': '领域分类为空'}

        if domain not in self.VALID_DOMAINS:

            return {'status': 'error', 'message': f'领域分类无效: {domain}，有效值: {self.VALID_DOMAINS}'}

        return {'status': 'valid'}

    def _attempt_ai_remediation(self, news: Dict, result: Dict, validation_results: Dict) -> Optional[Dict]:
        """
        尝试通过 AI 补救校验失败的字段

        Args:
            news: 原始新闻数据
            result: AI 返回的结果
            validation_results: 各字段校验结果

        Returns:
            补救后的结果，如果补救失败返回 None
        """
        if not self.ai_provider:
            logger.debug("DataValidator: 无 AI provider，跳过补救")
            return None

        failed_fields = [
            field for field, v in validation_results.items()
            if v.get('status') == 'error'
        ]

        if not failed_fields:
            return None

        logger.info(f"DataValidator: 尝试 AI 补救失败字段: {failed_fields}")

        title = news.get('title', '未知标题')
        content = news.get('content', '')[:500]
        source = news.get('source_name', '')

        prompt = self._build_remediation_prompt(
            title, source, content, failed_fields, result
        )

        try:
            response = self.ai_provider(prompt)
            fixed_result = self._parse_remediation_response(response, result)
            if fixed_result:
                logger.info(f"DataValidator: AI 补救成功")
                return fixed_result
            else:
                logger.warning(f"DataValidator: AI 补救解析失败")
                return None
        except Exception as e:
            logger.error(f"DataValidator: AI 补救调用失败: {e}")
            return None

    def _build_remediation_prompt(
        self,
        title: str,
        source: str,
        content: str,
        failed_fields: list,
        current_result: Dict
    ) -> str:
        """构建补救 prompt"""
        fields_desc = {
            'translation': '中文翻译',
            'summary': '100字以内核心摘要',
            'analysis': '5W1H分析（who/what/when/where/why/how）',
            'scoring': '评分（influence_score/value_score）',
            'domain': f'领域分类（必须在 {self.VALID_DOMAINS} 之一）'
        }

        failed_desc = [f"{f}（{fields_desc.get(f, f)}）" for f in failed_fields]

        current_values = {}
        for field in failed_fields:
            if field == 'analysis' and 'analysis' in current_result:
                current_values[field] = str(current_result['analysis'])
            elif field == 'scoring' and 'scoring' in current_result:
                current_values[field] = str(current_result['scoring'])
            else:
                current_values[field] = current_result.get(field, '无')

        return f"""你是一个专业的新闻分析专家。请根据以下信息，修复校验失败的字段。

原始新闻信息：
- 信源：{source}
- 标题：{title}
- 内容：{content[:300]}

当前 AI 返回结果：
{self._format_result_for_prompt(current_result)}

校验失败的字段：{', '.join(failed_desc)}

当前值：
{self._format_current_values(failed_fields, current_values)}

请直接输出修复后的完整 JSON（包含所有字段），确保：
1. 校验失败的字段被正确修复
2. 其他字段保持不变
3. domain 必须在 {self.VALID_DOMAINS} 之一
4. 只输出 JSON，不要其他文字
"""

    def _format_result_for_prompt(self, result: Dict) -> str:
        """格式化结果用于 prompt"""
        lines = []
        for k, v in result.items():
            if k == 'analysis':
                lines.append(f'  analysis: {v}')
            elif k == 'scoring':
                lines.append(f'  scoring: {v}')
            else:
                lines.append(f'  {k}: {v}')
        return '\n'.join(lines) if lines else '无'

    def _format_current_values(self, failed_fields: list, current_values: Dict) -> str:
        """格式化当前值用于 prompt"""
        lines = []
        for field in failed_fields:
            lines.append(f'  {field}: {current_values.get(field, "无")}')
        return '\n'.join(lines)

    def _parse_remediation_response(self, response: str, original_result: Dict) -> Optional[Dict]:
        """解析补救响应"""
        from core.utils.text_utils import parse_json_str
        fixed = parse_json_str(response)
        if not fixed:
            return None

        for key in original_result:
            if key not in fixed and key in original_result:
                fixed[key] = original_result[key]

        return fixed

    def _fill_default_values(self, result, validation_results):

        default_values = {}

        # P-12 修复：使用统一默认值常量
        if validation_results.get('translation', {}).get('status') == 'error':

            result['translation'] = DefaultValues.TEXT_NO_TRANSLATION

            default_values['translation'] = DefaultValues.TEXT_NO_TRANSLATION

        if validation_results.get('summary', {}).get('status') == 'error':

            result['summary'] = DefaultValues.TEXT_NO_SUMMARY

            default_values['summary'] = DefaultValues.TEXT_NO_SUMMARY

        if validation_results.get('analysis', {}).get('status') == 'error':

            if 'analysis' not in result:

                result['analysis'] = {}

            for field in DefaultValues.W5H1_FIELDS:

                if field not in result['analysis'] or not result['analysis'][field]:

                    default_val = DefaultValues.get_text_default(field)
                    result['analysis'][field] = default_val

                    default_values[f'analysis.{field}'] = default_val

        if validation_results.get('scoring', {}).get('status') == 'error':

            if 'scoring' not in result:

                result['scoring'] = {}

            # P-12 修复：使用 5.0 与 task1_collector 保持一致
            for field in ['influence_score', 'value_score']:

                if field not in result['scoring']:

                    result['scoring'][field] = DefaultValues.SCORE_DEFAULT

                    default_values[f'scoring.{field}'] = DefaultValues.SCORE_DEFAULT

        if validation_results.get('domain', {}).get('status') == 'error':

            result['domain'] = DefaultValues.DOMAIN_DEFAULT

            default_values['domain'] = DefaultValues.DOMAIN_DEFAULT

        return default_values
