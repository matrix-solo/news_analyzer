# -*- coding: utf-8 -*-
class FieldNormalizer:

    def normalize_fields(self, item):

        # 基于实际信源字段建立映射

        field_mapping = {

            'title': ['title', 'headline', 'subject'],

            'link': ['link', 'url'],

            'description': ['description', 'summary'],

            'pub_date': ['pub_date', 'published', 'date', 'pubdate'],

            'author': ['author', 'creator', 'by'],

            'category': ['category', 'tags', 'topic'],

            'guid': ['guid', 'id'],

            'source': ['source', 'from', 'origin'],

            'content': ['content', 'fulltext', 'body']

        }

        normalized = {}

        for standard_field, source_fields in field_mapping.items():

            for source_field in source_fields:

                if source_field in item and item[source_field]:

                    normalized[standard_field] = item[source_field]

                    break

            if standard_field not in normalized:

                normalized[standard_field] = None

        # 标准化日期格式

        if normalized.get('pub_date'):

            normalized['pub_date'] = self._normalize_date(normalized['pub_date'])

        # 处理特殊情况:部分信源使用guid作为链接

        if not normalized.get('link') and normalized.get('guid'):

            normalized['link'] = normalized['guid']

        return normalized

    def _normalize_date(self, date_str):

        # 简单的日期标准化处理

        # 实际实现中可能需要更复杂的日期解析

        return date_str
