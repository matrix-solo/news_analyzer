#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 转 PDF 工具模块（使用 reportlab，纯 Python 实现）
支持将特定表格转换为图表
"""

import logging
import re
import io
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger("MD2PDF")

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab 模块未安装，PDF 生成功能不可用")


def register_chinese_fonts():
    """注册中文字体"""
    try:
        # 尝试注册常见的中文字体
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
            "/System/Library/Fonts/PingFang.ttc",  # macOS
        ]
        for font_path in font_paths:
            if Path(font_path).exists():
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
    except Exception as e:
        logger.warning(f"注册中文字体失败: {e}")
    return 'Helvetica'


def parse_markdown(md_content: str) -> List[Tuple[str, str, str]]:
    """
    解析 Markdown 内容为结构化数据
    
    Returns:
        List of (type, content, level) tuples
    """
    elements = []
    lines = md_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # 标题
        if line.startswith('#'):
            level = len(re.match(r'^#+', line).group())
            content = line.lstrip('#').strip()
            elements.append(('heading', content, str(level)))
        
        # 分隔线
        elif line == '---':
            elements.append(('hr', '', ''))
        
        # 引用
        elif line.startswith('>'):
            content = line.lstrip('>').strip()
            elements.append(('quote', content, ''))
        
        # 表格
        elif '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            i -= 1
            elements.append(('table', '\n'.join(table_lines), ''))
        
        # 列表
        elif line.startswith('- ') or re.match(r'^\d+\. ', line):
            content = re.sub(r'^[-\d.]+ ', '', line)
            elements.append(('list', content, ''))
        
        # 普通段落
        else:
            elements.append(('paragraph', line, ''))
        
        i += 1
    
    return elements


def create_pdf_from_md(md_content: str, output_path: Path) -> bool:
    """
    将 Markdown 转换为 PDF
    
    Args:
        md_content: Markdown 内容
        output_path: 输出 PDF 路径
    
    Returns:
        是否成功
    """
    if not REPORTLAB_AVAILABLE:
        logger.warning("reportlab 未安装，无法生成 PDF")
        return False
    
    try:
        # 注册中文字体
        font_name = register_chinese_fonts()
        
        # 创建文档
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # 创建样式
        styles = getSampleStyleSheet()
        
        # 自定义样式
        styles.add(ParagraphStyle(
            name='ChineseHeading1',
            fontName=font_name,
            fontSize=18,
            leading=24,
            spaceAfter=12,
            textColor=colors.HexColor('#1a1a1a'),
            alignment=TA_LEFT
        ))
        
        styles.add(ParagraphStyle(
            name='ChineseHeading2',
            fontName=font_name,
            fontSize=14,
            leading=20,
            spaceAfter=10,
            spaceBefore=16,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_LEFT
        ))
        
        styles.add(ParagraphStyle(
            name='ChineseHeading3',
            fontName=font_name,
            fontSize=12,
            leading=16,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.HexColor('#34495e'),
            alignment=TA_LEFT
        ))
        
        styles.add(ParagraphStyle(
            name='ChineseBody',
            fontName=font_name,
            fontSize=10,
            leading=16,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))
        
        styles.add(ParagraphStyle(
            name='ChineseQuote',
            fontName=font_name,
            fontSize=10,
            leading=14,
            leftIndent=20,
            textColor=colors.HexColor('#666666'),
            backColor=colors.HexColor('#f9f9f9'),
            borderPadding=8,
            alignment=TA_LEFT
        ))
        
        styles.add(ParagraphStyle(
            name='ChineseList',
            fontName=font_name,
            fontSize=10,
            leading=14,
            leftIndent=20,
            spaceAfter=4,
            alignment=TA_LEFT
        ))
        
        # 解析 Markdown
        elements = parse_markdown(md_content)
        
        # 构建 PDF 内容
        story = []
        
        for elem_type, content, level in elements:
            if elem_type == 'heading':
                if level == '1':
                    story.append(Paragraph(content, styles['ChineseHeading1']))
                elif level == '2':
                    story.append(Paragraph(content, styles['ChineseHeading2']))
                else:
                    story.append(Paragraph(content, styles['ChineseHeading3']))
            
            elif elem_type == 'paragraph':
                # 处理粗体和链接
                content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
                content = re.sub(r'\[(.+?)\]\((.+?)\)', r'<link href="\2">\1</link>', content)
                story.append(Paragraph(content, styles['ChineseBody']))
            
            elif elem_type == 'quote':
                story.append(Paragraph(f'"{content}"', styles['ChineseQuote']))
            
            elif elem_type == 'list':
                content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
                story.append(Paragraph(f"• {content}", styles['ChineseList']))
            
            elif elem_type == 'hr':
                story.append(Spacer(1, 12))
            
            elif elem_type == 'table':
                # 解析表格数据
                table_lines = content.split('\n')
                if len(table_lines) >= 2:
                    table_data = []
                    for line in table_lines:
                        if '---' not in line:
                            cells = [c.strip() for c in line.split('|') if c.strip()]
                            if cells:
                                table_data.append(cells)
                    
                    if table_data:
                        # 检查是否应该转换为图表
                        should_chart, chart_type = is_chart_table(table_data)
                        
                        if should_chart and chart_type == 'bar':
                            # 检测是领域总览表还是历史对比表
                            if len(table_data) > 0 and len(table_data[0]) > 0 and '对比' in table_data[0][0]:
                                # 历史对比表
                                chart_drawing = create_comparison_chart(table_data, font_name)
                            else:
                                # 领域总览表
                                chart_drawing = create_bar_chart(table_data, font_name)
                            
                            # 将图表添加到story
                            story.append(chart_drawing)
                            story.append(Spacer(1, 12))
                            
                            # 同时保留简化版表格（只保留关键行）
                            # 过滤掉数值为0或空的行
                            filtered_data = [table_data[0]]  # 保留表头
                            for row in table_data[1:]:
                                if len(row) >= 2 and any(re.search(r'\d', cell) for cell in row[1:]):
                                    filtered_data.append(row)
                            
                            if len(filtered_data) > 1:
                                # 添加说明文字
                                story.append(Paragraph("<i>（详细数据见上表）</i>", styles['ChineseBody']))
                                story.append(Spacer(1, 6))
                        
                        else:
                            # 普通表格，正常渲染
                            t = Table(table_data)
                            t.setStyle(TableStyle([
                                ('FONTNAME', (0, 0), (-1, -1), font_name),
                                ('FONTSIZE', (0, 0), (-1, -1), 9),
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                                ('TOPPADDING', (0, 0), (-1, -1), 6),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                            ]))
                            story.append(t)
                            story.append(Spacer(1, 12))
        
        # 生成 PDF
        doc.build(story)
        logger.info(f"PDF 生成成功: {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"PDF 生成失败: {e}")
        return False


def convert_md_file_to_pdf(md_path: Path) -> Optional[Path]:
    """
    将 Markdown 文件转换为 PDF
    
    Args:
        md_path: Markdown 文件路径
    
    Returns:
        PDF 文件路径，失败返回 None
    """
    if not md_path.exists():
        logger.error(f"文件不存在: {md_path}")
        return None
    
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    pdf_path = md_path.with_suffix('.pdf')
    if create_pdf_from_md(md_content, pdf_path):
        return pdf_path
    return None


def is_pdf_available() -> bool:
    """检查 PDF 生成功能是否可用"""
    return REPORTLAB_AVAILABLE


def is_chart_table(table_data: List[List[str]]) -> Tuple[bool, str]:
    """
    判断表格是否应该转换为图表
    
    Returns:
        (是否转换, 图表类型)
        图表类型: 'bar' (柱状图), 'line' (折线图), '' (不转换)
    """
    if not table_data or len(table_data) < 2:
        return False, ''
    
    headers = table_data[0]
    header_text = ' '.join(headers)
    
    # 领域数据总览表特征（更宽松的检测）
    has_date_cols = any(keyword in header_text for keyword in ['当日', '近7天', '近30天'])
    has_indicator = any(keyword in header_text for keyword in ['指标', '新闻数量', '平均综合评分', '高分事件'])
    if has_date_cols and has_indicator:
        return True, 'bar'
    
    # 历史对比表特征（更宽松的检测）
    if '对比' in header_text and len(table_data[0]) >= 3:
        return True, 'bar'
    
    return False, ''


def create_bar_chart(table_data: List[List[str]], font_name: str = 'Helvetica') -> Drawing:
    """
    从表格数据创建柱状图
    
    Args:
        table_data: 表格数据，第一行为表头
        font_name: 字体名称
    
    Returns:
        Drawing 对象
    """
    drawing = Drawing(500, 250)
    
    # 解析数据
    headers = table_data[0]
    data_rows = table_data[1:]
    
    # 提取数值列（跳过第一列通常是标签列）
    categories = []
    series_names = headers[1:]  # 当日、近7天、近30天等
    
    # 准备图表数据
    chart_data = [[] for _ in series_names]
    
    for row in data_rows:
        if len(row) < 2:
            continue
        categories.append(row[0][:15])  # 指标名称，限制长度
        for i, value in enumerate(row[1:len(series_names)+1]):
            try:
                # 提取数值（去掉百分号等）
                num_str = re.sub(r'[^\d.]', '', value)
                num = float(num_str) if num_str else 0
                chart_data[i].append(num)
            except (ValueError, TypeError) as e:
                logger.debug(f"解析数值失败: {value}, {e}")
                chart_data[i].append(0)
    
    if not categories or not any(chart_data):
        return drawing
    
    # 创建柱状图
    chart = VerticalBarChart()
    chart.x = 60
    chart.y = 50
    chart.width = 400
    chart.height = 150
    
    # 设置数据
    chart.data = chart_data
    chart.categoryAxis.categoryNames = categories
    
    # 设置样式
    chart.valueAxis.valueMin = 0
    max_val = max([max(d) if d else 0 for d in chart_data])
    chart.valueAxis.valueMax = max_val * 1.2 if max_val > 0 else 100
    
    # 设置颜色
    chart.bars[0].fillColor = colors.HexColor('#3498db')  # 蓝色 - 当日
    if len(chart_data) > 1:
        chart.bars[1].fillColor = colors.HexColor('#2ecc71')  # 绿色 - 近7天
    if len(chart_data) > 2:
        chart.bars[2].fillColor = colors.HexColor('#e74c3c')  # 红色 - 近30天
    
    # 设置标签
    chart.categoryAxis.labels.fontName = font_name
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.labels.fontName = font_name
    chart.valueAxis.labels.fontSize = 8
    
    # 添加图例（使用String对象手动添加）
    legend_y = 200
    legend_items = [
        (colors.HexColor('#3498db'), series_names[0] if len(series_names) > 0 else '当日'),
        (colors.HexColor('#2ecc71'), series_names[1] if len(series_names) > 1 else '近7天'),
        (colors.HexColor('#e74c3c'), series_names[2] if len(series_names) > 2 else '近30天'),
    ]
    
    for i, (color, name) in enumerate(legend_items[:len(series_names)]):
        # 图例色块
        legend_rect = Rect(350, legend_y - i*15, 10, 10, fillColor=color, strokeColor=None)
        drawing.add(legend_rect)
        # 图例文字
        legend_text = String(365, legend_y - i*15 + 2, name, fontName=font_name, fontSize=8)
        drawing.add(legend_text)
    
    drawing.add(chart)
    
    # 添加标题
    title = String(250, 230, '数据对比图表', fontName=font_name, fontSize=12, textAnchor='middle')
    drawing.add(title)
    
    return drawing


def create_comparison_chart(table_data: List[List[str]], font_name: str = 'Helvetica') -> Drawing:
    """
    创建对比柱状图（用于历史对比表）
    
    Args:
        table_data: 表格数据
        font_name: 字体名称
    
    Returns:
        Drawing 对象
    """
    drawing = Drawing(500, 200)
    
    # 解析数据 - 第一行是当前事件，后续是历史事件
    data_rows = table_data[1:] if len(table_data) > 1 else []
    
    if len(data_rows) < 2:
        return drawing
    
    # 提取标题和分数
    labels = []
    scores = []
    
    for row in data_rows[:6]:  # 最多显示6条
        if len(row) >= 4:
            label = row[1] if len(row[1]) < 10 else row[1][:10] + '...'
            labels.append(label)
            try:
                score = float(re.sub(r'[^\d.]', '', row[3]))
                scores.append(score)
            except (ValueError, TypeError) as e:
                logger.debug(f"解析分数失败: {row[3] if len(row) > 3 else 'N/A'}, {e}")
                scores.append(0)
    
    if not labels:
        return drawing
    
    # 创建柱状图
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 40
    chart.width = 420
    chart.height = 120
    
    chart.data = [scores]
    chart.categoryAxis.categoryNames = labels
    
    # 设置样式
    chart.valueAxis.valueMin = 0
    max_score = max(scores) if scores else 100
    chart.valueAxis.valueMax = max_score * 1.2
    
    # 当前事件用红色，历史用蓝色
    colors_list = [colors.HexColor('#e74c3c')] + [colors.HexColor('#3498db')] * (len(scores) - 1)
    for i, color in enumerate(colors_list):
        if i < len(chart.bars):
            chart.bars[i].fillColor = color
    
    chart.categoryAxis.labels.fontName = font_name
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontName = font_name
    chart.valueAxis.labels.fontSize = 8
    
    drawing.add(chart)
    
    # 添加标题
    title = String(250, 180, '历史得分对比', fontName=font_name, fontSize=11, textAnchor='middle')
    drawing.add(title)
    
    return drawing
