# -*- coding: utf-8 -*-
class DataValidator:

    def validate_combined_result(self, news, result):

        # 校验合并处理结果的完整性

        validation_rules = {

            'translation': self._validate_translation,

            'summary': self._validate_summary,

            'analysis': self._validate_analysis,

            'scoring': self._validate_scoring

        }

        validation_results = {}

        for field, validator in validation_rules.items():

            if field in result:

                validation_results[field] = validator(result[field])

            else:

                validation_results[field] = {'status': 'error', 'message': f'字段 {field} 缺失'}

        # 处理校验失败

        has_errors = any(v['status'] == 'error' for v in validation_results.values())

        if has_errors:

            # 尝试AI补救

            remediation_result = self._attempt_ai_remediation(news, result, validation_results)

            if remediation_result:

                return {'status': 'remediated', 'results': validation_results, 'remediation': remediation_result}

            else:

                # 填充默认值

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

        required_scores = ['source_score', 'influence_score', 'value_score', 'compliance_score']

        missing_scores = [score for score in required_scores if score not in scoring]

        if missing_scores:

            return {'status': 'error', 'message': f'缺失评分字段: {missing_scores}'}

        return {'status': 'valid'}

    def _attempt_ai_remediation(self, news, result, validation_results):

        # 尝试AI补救

        # 实际实现中需要调用AI API进行补救

        # 这里返回None表示补救失败

        return None

    def _fill_default_values(self, result, validation_results):

        # 填充默认值

        default_values = {}

        if validation_results.get('translation', {}).get('status') == 'error':

            result['translation'] = '暂无翻译'

            default_values['translation'] = '暂无翻译'

        if validation_results.get('summary', {}).get('status') == 'error':

            result['summary'] = '暂无摘要'

            default_values['summary'] = '暂无摘要'

        if validation_results.get('analysis', {}).get('status') == 'error':

            if 'analysis' not in result:

                result['analysis'] = {}

            for field in ['who', 'what', 'when', 'where', 'why', 'how']:

                if field not in result['analysis'] or not result['analysis'][field]:

                    result['analysis'][field] = '暂无信息'

                    default_values[f'analysis.{field}'] = '暂无信息'

        if validation_results.get('scoring', {}).get('status') == 'error':

            if 'scoring' not in result:

                result['scoring'] = {}

            for field in ['source_score', 'influence_score', 'value_score', 'compliance_score']:

                if field not in result['scoring']:

                    result['scoring'][field] = 0.0

                    default_values[f'scoring.{field}'] = 0.0

        return default_values
