#!/usr/bin/env python3
"""Offline checks for WeChat body fidelity.

The module reads and transforms HTML strings only. It does not open a network
connection, read a clipboard, or talk to the WeChat API. A passing report is a
structural comparison. Saving a draft, reopening the editor, and reading the
article on a phone stay manual.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import urllib.parse
from html.parser import HTMLParser
from xml.sax.saxutils import escape as xml_escape

FISH_PRESET = {
    'id': '01fish',
    'paper': '#F2EDE3',
    'ink': '#1A3328',
    'fish_red': '#C44536',
    'body_px': 15,
    'line_height': '2',
    'h2_px': 20,
    'h3_px': 17,
    'caption_px': 13,
}

READING_WIDTH_PX = 390
COVER_RATIO = 2.35
THUMB_RATIO = 1.0
PLATE_PADDING = '1px 0'
OFFICIAL_CDN_HOSTS = frozenset({'mmbiz.qpic.cn', 'mmbiz.qlogo.cn'})

_VOID_TAGS = frozenset({
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
    'meta', 'param', 'source', 'track', 'wbr',
})
_SKIP_TAGS = frozenset({'script', 'style', 'noscript'})


class ImageOpError(ValueError):
    """The image edit is ambiguous or unsafe. Nothing is guessed by index."""


class _TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {'type': 'el', 'tag': '#root', 'attrs': [], 'children': []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {'type': 'el', 'tag': tag.lower(), 'attrs': list(attrs), 'children': []}
        self.stack[-1]['children'].append(node)
        if tag.lower() not in _VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = {'type': 'el', 'tag': tag.lower(), 'attrs': list(attrs), 'children': []}
        self.stack[-1]['children'].append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]['tag'] == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1]['children'].append({'type': 'text', 'text': data})


def parse_html(html: str) -> dict:
    parser = _TreeParser()
    parser.feed(html or '')
    parser.close()
    return parser.root


def _attr(node: dict, name: str):
    for key, value in node.get('attrs', []):
        if str(key).lower() == name:
            return value
    return None


def _style(node: dict) -> str:
    value = _attr(node, 'style')
    return value or ''


def _children(node: dict, tag: str | None = None) -> list[dict]:
    found = []
    for child in node.get('children', []):
        if child.get('type') != 'el':
            continue
        if tag is None or child['tag'] == tag:
            found.append(child)
    return found


def _walk_elements(node: dict):
    if node.get('type') != 'el':
        return
    yield node
    for child in node.get('children', []):
        yield from _walk_elements(child)


def _text(node: dict) -> str:
    if node.get('type') == 'text':
        return node.get('text', '')
    if node.get('tag') in _SKIP_TAGS:
        return ''
    return ''.join(_text(child) for child in node.get('children', []))


def brand_preset(name: str, overrides: dict | None = None) -> dict:
    """Return the 01fish preset. Other brand names are not filled with these colors."""
    if name != '01fish':
        raise KeyError(f'没有名为 {name} 的预设。01fish 的色值不会套到其他品牌上。')
    data = {
        'paper': FISH_PRESET['paper'],
        'ink': FISH_PRESET['ink'],
        'fish_red': FISH_PRESET['fish_red'],
        'body_px': FISH_PRESET['body_px'],
        'line_height': FISH_PRESET['line_height'],
        'h2_px': FISH_PRESET['h2_px'],
        'h3_px': FISH_PRESET['h3_px'],
        'caption_px': FISH_PRESET['caption_px'],
    }
    if overrides:
        unknown = sorted(set(overrides) - set(data))
        if unknown:
            raise KeyError('未知覆盖项: ' + ', '.join(unknown))
        data.update(overrides)
    return data


def normalize_hex_color(value: str) -> str:
    match = re.fullmatch(r'#([0-9A-Fa-f]{6})', (value or '').strip())
    if not match:
        raise ValueError('颜色必须是 #RRGGBB，不能把任意 CSS 写进正文')
    return '#' + match.group(1).upper()


def wrap_theme_plate(content_html: str, background: str) -> str:
    """Wrap the whole paste payload in one padded plate.

    Sibling section margins and list-item margins sit outside each child's own
    background, so coloring each block still leaves the page color in the gap.
    One ancestor with an inline background and a non-zero vertical padding
    paints that gap. The padding value is the one checked against editor
    reopen behavior: ``1px 0``. A browser ``body`` background is not part of
    this string and is not a pasteable background.
    """
    background = normalize_hex_color(background)
    stripped = (content_html or '').strip()
    if _opening_plate_matches(stripped, background):
        return content_html
    style = f'background-color:{background};padding:{PLATE_PADDING}'
    return f'<section style="{style}">\n{content_html}\n</section>'


def _opening_plate_matches(stripped: str, background: str) -> bool:
    match = re.match(r'^<section\b([^>]*)>', stripped, re.IGNORECASE)
    if not match:
        return False
    compact = re.sub(r'\s+', '', match.group(1)).lower()
    wanted = f'background-color:{background};padding:{PLATE_PADDING}'.lower().replace(' ', '')
    return wanted in compact


def extract_paste_payload(full_html: str) -> str:
    """Return the `.content` fragment. The document body is not the payload."""
    match = re.search(
        r'<div\b[^>]*\bclass\s*=\s*["\'][^"\']*\bcontent\b[^"\']*["\'][^>]*>([\s\S]*)</div>\s*</body>',
        full_html,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError('预览页里没有 .content。浏览器 body 背景不能当作粘贴载荷。')
    payload = match.group(1).strip()
    if re.match(r'(?is)^<body\b', payload):
        raise ValueError('粘贴载荷不应是 body')
    return payload


def simulate_editor_reopen(html: str) -> str:
    """Drop id attributes and keep style. This is not a live editor round-trip."""
    return re.sub(r'\s+id\s*=\s*("[^"]*"|\'[^\']*\')', '', html or '', flags=re.IGNORECASE)


def _has_background(style: str) -> bool:
    compact = style.replace(' ', '').lower()
    return 'background-color:' in compact or 'background:' in compact


def _vertical_padding(style: str) -> bool:
    match = re.search(r'(?:^|;)\s*padding\s*:\s*([^;]+)', style, re.IGNORECASE)
    if match:
        parts = match.group(1).strip().split()
        vertical = parts[0] if parts else '0'
        if len(parts) == 4:
            vertical_values = (parts[0], parts[2])
        else:
            vertical_values = (vertical,)
        return any(item not in {'0', '0px'} for item in vertical_values)
    for side in ('padding-top', 'padding-bottom'):
        side_match = re.search(rf'(?:^|;)\s*{side}\s*:\s*([^;]+)', style, re.IGNORECASE)
        if side_match and side_match.group(1).strip() not in {'0', '0px'}:
            return True
    return False


def _is_padded_plate(node: dict) -> bool:
    if node.get('tag') not in {'section', 'div'}:
        return False
    style = _style(node)
    return bool(style) and _has_background(style) and _vertical_padding(style)


def _background_color(style: str):
    compact = re.sub(r'\s+', '', style)
    match = re.search(r'background-color:(#[0-9A-Fa-f]{6})', compact, re.IGNORECASE)
    if not match:
        match = re.search(r'(?:^|;)background:(#[0-9A-Fa-f]{6})', compact, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def sibling_margin_gap_risk(html: str) -> dict:
    """Structural clue for white gaps. Not a screenshot of the phone preview.

    Adjacent boxes paint only their own background. The margin between them,
    and a list that sits outside a padded plate, shows whatever is behind.
    """
    tree = parse_html(html)
    reasons: list[str] = []

    def visit(node: dict, covered: bool):
        if node.get('type') != 'el':
            return
        plate = _is_padded_plate(node)
        now_covered = covered or plate
        elements = _children(node)
        if not now_covered:
            themed = [child for child in elements if _has_background(_style(child))]
            if len(themed) >= 2:
                reasons.append('sibling_backgrounds_without_plate')
            if any(child['tag'] in {'ul', 'ol'} for child in elements):
                reasons.append('list_outside_plate')
        for child in elements:
            visit(child, now_covered)

    visit(tree, False)
    unique = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return {
        'gap_risk': bool(unique),
        'reasons': unique,
        'phone_verified': False,
        'checked_live_editor': False,
    }


def plate_colors(html: str) -> list:
    colors = []

    def visit(node: dict, under_plate: bool):
        if node.get('type') != 'el':
            return
        plate = _is_padded_plate(node)
        if plate and not under_plate:
            colors.append(_background_color(_style(node)))
        for child in _children(node):
            visit(child, under_plate or plate)

    visit(parse_html(html), False)
    return colors


def visible_text(html: str) -> str:
    parts: list[str] = []

    def visit(node: dict, skip: bool):
        if node.get('type') == 'text':
            if not skip:
                parts.append(node.get('text', ''))
            return
        class_name = _attr(node, 'class') or ''
        classes = class_name.split() if isinstance(class_name, str) else []
        skipping = skip or node.get('tag') in _SKIP_TAGS or 'tip' in classes
        for child in node.get('children', []):
            visit(child, skipping)

    visit(parse_html(html), False)
    return ''.join(parts)


def _nonsws(value: str) -> str:
    return re.sub(r'\s+', '', value or '')


def _norm_color(value):
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw:
        return None
    match = re.fullmatch(r'#([0-9a-f]{6})', raw)
    if match:
        return '#' + match.group(1).upper()
    match = re.fullmatch(r'#([0-9a-f]{3})', raw)
    if match:
        return '#' + ''.join(char * 2 for char in match.group(1)).upper()
    match = re.fullmatch(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', raw)
    if match:
        numbers = [int(item) for item in match.groups()]
        if all(0 <= number <= 255 for number in numbers):
            return '#{:02X}{:02X}{:02X}'.format(*numbers)
    return raw


def _css_color(style: str):
    for part in (style or '').split(';'):
        if ':' not in part:
            continue
        key, val = part.split(':', 1)
        if key.strip().lower() == 'color':
            return _norm_color(val)
    return None


def _effective_color(chain: list[dict]):
    for node in reversed(chain):
        if node.get('tag') in {None, '#root'}:
            continue
        color = _css_color(_style(node))
        if color:
            return color
        named = _attr(node, 'color')
        if named:
            return _norm_color(named)
    return None


def extract_bold(html: str) -> list[dict]:
    found = []

    def visit(node: dict, ancestors: list[dict]):
        if node.get('type') != 'el' or node.get('tag') in _SKIP_TAGS:
            return
        chain = ancestors + [node]
        if node['tag'] in {'strong', 'b'}:
            found.append({
                'text': _text(node).strip(),
                'color': _effective_color(chain),
            })
        for child in _children(node):
            visit(child, chain)

    visit(parse_html(html), [])
    return found


def extract_links(html: str) -> list[dict]:
    found = []

    def visit(node: dict):
        if node.get('type') != 'el' or node.get('tag') in _SKIP_TAGS:
            return
        if node['tag'] == 'a':
            found.append((_attr(node, 'href') or '', _text(node).strip()))
        for child in _children(node):
            visit(child)

    visit(parse_html(html))
    return found


def _src_of(tag: str) -> str:
    match = re.search(r'\bsrc\s*=\s*(["\'])(.*?)\1', tag, re.IGNORECASE | re.DOTALL)
    return match.group(2) if match else ''


def image_srcs(html: str) -> list[str]:
    return [_src_of(tag) for tag in re.findall(r'<img\b[^>]*>', html or '', re.IGNORECASE)]


def classify_image_src(src: str) -> str:
    if src is None or not str(src).strip():
        return 'missing'
    value = str(src).strip()
    lower = value.lower()
    if lower.startswith(('data:', 'file:', 'blob:', '/', './', '../')):
        return 'local_preview'
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or '').lower()
    if parsed.scheme == 'https' and host in OFFICIAL_CDN_HOSTS:
        return 'official_cdn'
    return 'not_official_cdn'


def image_upload_counts_as_success(src: str) -> bool:
    return classify_image_src(src) == 'official_cdn'


def article_flattened_to_images(html: str) -> bool:
    return _nonsws(visible_text(html)) == '' and len(image_srcs(html)) > 0


def _cell_text(node: dict) -> str:
    return re.sub(r'\s+', ' ', _text(node)).strip()


def parse_table_html(table_html: str) -> dict:
    tree = parse_html(table_html)
    table = next((node for node in _walk_elements(tree) if node['tag'] == 'table'), None)
    if table is None:
        return {'caption': '', 'headers': [], 'rows': [], 'source_lines': []}
    caption_node = next((node for node in _walk_elements(table) if node['tag'] == 'caption'), None)
    caption = _cell_text(caption_node) if caption_node else ''
    headers: list[str] = []
    rows: list[list[str]] = []

    def take_rows(container: dict, allow_header: bool):
        nonlocal headers
        for row_node in container.get('children', []):
            if row_node.get('type') != 'el' or row_node['tag'] != 'tr':
                continue
            cells = [
                child for child in row_node.get('children', [])
                if child.get('type') == 'el' and child['tag'] in {'td', 'th'}
            ]
            values = [_cell_text(cell) for cell in cells]
            if not values:
                continue
            if allow_header and not headers and all(cell['tag'] == 'th' for cell in cells):
                headers = values
            else:
                rows.append(values)

    thead = next((node for node in table.get('children', []) if node.get('tag') == 'thead'), None)
    tbody = next((node for node in table.get('children', []) if node.get('tag') == 'tbody'), None)
    if thead is not None:
        take_rows(thead, True)
    if tbody is not None:
        take_rows(tbody, False)
    if thead is None and tbody is None:
        take_rows(table, True)

    source_lines = []
    for index, header in enumerate(headers):
        if any(token in header for token in ('来源', '口径', '统计')):
            for row in rows:
                if index < len(row) and row[index]:
                    source_lines.append(f'{header}：{row[index]}')
    return {
        'caption': caption,
        'headers': headers,
        'rows': rows,
        'source_lines': source_lines,
    }


def extract_tables(html: str) -> list[dict]:
    return [
        parse_table_html(match.group(0))
        for match in re.finditer(r'<table\b[^>]*>[\s\S]*?</table>', html or '', re.IGNORECASE)
    ]


def migration_scope(html: str) -> dict:
    """List tables in an existing draft. Do not rewrite the caller's HTML."""
    return {
        'authorized_to_rewrite_user_text': False,
        'mutated': False,
        'tables': extract_tables(html),
        'action': '只标出待图像化的表。未授权不删除表格、不改写单元格文字。',
        'overflow_x_is_not_a_fix': True,
        'phone_verified': False,
        'checked_live_editor': False,
    }


def render_pending_table(info: dict, index: int) -> str:
    """Preserve every cell as text and mark the block as not yet an image."""
    lines = [
        f'<section data-wechat-table-pending="1" data-table-index="{index}">',
        '<p><strong>待配图</strong>：这些格子还不是手机配图，不能把这篇标成可以发出的正文。</p>',
    ]
    if info.get('caption'):
        lines.append(f'<p>题注：{xml_escape(info["caption"])}</p>')
    if info.get('source_lines'):
        for line in info['source_lines']:
            lines.append(f'<p>{xml_escape(line)}</p>')
    else:
        lines.append('<p>来源/统计口径：未单列。下面各格原文都保留。</p>')
    if info.get('headers'):
        lines.append('<p>表头：' + '｜'.join(xml_escape(cell) for cell in info['headers']) + '</p>')
    for row in info.get('rows', []):
        lines.append('<p>行：' + '｜'.join(xml_escape(cell) for cell in row) + '</p>')
    lines.append('</section>')
    return ''.join(lines)


def defer_html_tables(html: str) -> tuple[str, list[dict]]:
    """Replace HTML tables in newly generated body HTML. Existing drafts use migration_scope."""
    tables: list[dict] = []

    def replace(match: re.Match) -> str:
        info = parse_table_html(match.group(0))
        tables.append(info)
        return render_pending_table(info, len(tables))

    replaced = re.sub(r'<table\b[^>]*>[\s\S]*?</table>', replace, html or '', flags=re.IGNORECASE)
    return replaced, tables


def _wrap_svg_text(text: str, width_chars: int) -> list[str]:
    if text == '':
        return ['']
    lines = []
    buf = ''
    for char in text:
        buf += char
        if len(buf) >= width_chars:
            lines.append(buf)
            buf = ''
    if buf:
        lines.append(buf)
    return lines


def table_to_svg_cards(
    table: dict,
    *,
    card_width: int = READING_WIDTH_PX,
    max_cols: int = 3,
    max_rows: int = 6,
    font_px: int = 16,
    background: str = FISH_PRESET['paper'],
) -> list[str]:
    """Editable vector cards. This does not rasterize PNG and is not WeChat-ready."""
    if font_px < 16:
        raise ValueError('配图字号不能压到 16px 以下')
    background = normalize_hex_color(background)
    headers = list(table.get('headers') or [])
    rows = [list(row) for row in table.get('rows') or []]
    width = max((len(row) for row in rows), default=0)
    column_count = max(len(headers), width, 1)
    if len(headers) < column_count:
        headers = headers + [''] * (column_count - len(headers))
    column_groups = [list(range(start, min(start + max_cols, column_count))) for start in range(0, column_count, max_cols)]
    row_groups = [rows[start:start + max_rows] for start in range(0, max(len(rows), 1), max_rows)]
    if not rows:
        row_groups = [[]]
    cards = []
    total = len(column_groups) * len(row_groups)
    number = 0
    for columns in column_groups:
        for group in row_groups:
            number += 1
            cards.append(_svg_card(
                table,
                headers,
                columns,
                group,
                card_width=card_width,
                font_px=font_px,
                background=background,
                number=number,
                total=total,
            ))
    return cards


def _svg_card(table, headers, columns, rows, *, card_width, font_px, background, number, total) -> str:
    title = table.get('caption') or '数据'
    ink = FISH_PRESET['ink']
    line_height = font_px + 8
    y = 28
    lines = [(title + f'（{number}/{total}）', 18, ink, True)]
    for source in table.get('source_lines') or []:
        for piece in _wrap_svg_text(source, 18):
            lines.append((piece, font_px, ink, False))
    selected_headers = [headers[index] for index in columns]
    if any(selected_headers):
        for piece in _wrap_svg_text('｜'.join(selected_headers), 18):
            lines.append((piece, font_px, ink, True))
    for row in rows:
        values = []
        for index in columns:
            values.append(row[index] if index < len(row) else '')
        for piece in _wrap_svg_text('｜'.join(values), 18):
            lines.append((piece, font_px, '#333333', False))
    height = 28 + len(lines) * line_height + 20
    body = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{card_width}" height="{height}" viewBox="0 0 {card_width} {height}">',
        f'<rect width="{card_width}" height="{height}" fill="{background}"/>',
    ]
    cursor = y
    for text, size, color, _strong in lines:
        weight = ' font-weight="700"' if size > font_px or _strong else ''
        body.append(
            f'<text x="20" y="{cursor}" font-size="{size}" fill="{color}" '
            f'font-family="PingFang SC, Microsoft YaHei, sans-serif"{weight}>'
            f'{xml_escape(text)}</text>'
        )
        cursor += line_height
    body.append('</svg>')
    return ''.join(body)


def table_image_plan(table: dict, **kwargs) -> dict:
    cards = table_to_svg_cards(table, **kwargs)
    return {
        'format': 'svg',
        'cards': cards,
        'card_count': len(cards),
        'png_rendered': False,
        'cdn_uploaded': False,
        'wechat_ready': False,
        'phone_verified': False,
        'checked_live_editor': False,
        'next_gates': [
            'SVG 只是可编辑矢量。本仓库没有栅格化依赖，不能把它说成已经导出的 PNG。',
            f'导出后按 {READING_WIDTH_PX}px 宽做手机阅读。截图局部放大不算合格。',
            '图片要上传到官方 CDN，再用段落锚点替换待配图块。',
            '保存草稿并重开后看首、中、尾的底板和图片顺序。自动检查代替不了这一步。',
        ],
    }


def assess_image_source(kind: str, enlargement: float = 1) -> dict:
    source = (kind or '').lower()
    base = {'png_rendered': False, 'phone_verified': False, 'checked_live_editor': False}
    if source == 'screenshot' and enlargement > 1:
        return {
            **base,
            'accept': False,
            'reason': '截图局部放大后会糊，不作为正文配图。',
        }
    if source == 'vector':
        return {
            **base,
            'accept': True,
            'prefer': 'editable_vector_then_png',
            'css_width': READING_WIDTH_PX,
            'reason': '先留可编辑矢量，再导出清晰 PNG。这里没有执行导出。',
        }
    if source in {'photo', 'user'}:
        return {
            **base,
            'accept': True,
            'keep_natural_ratio': True,
            'reason': '用户自带图保持自然比例，不拉成统一画幅。',
        }
    return {**base, 'accept': False, 'reason': '未知图片来源。'}


def crop_box(src_w: float, src_h: float, target_ratio: float) -> dict:
    """Center-crop. Both axes stay at scale 1, so the picture is not stretched."""
    if src_w <= 0 or src_h <= 0 or target_ratio <= 0:
        raise ValueError('裁切尺寸必须为正')
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        crop_w = src_h * target_ratio
        box = {'x': (src_w - crop_w) / 2, 'y': 0.0, 'w': crop_w, 'h': float(src_h)}
    else:
        crop_h = src_w / target_ratio
        box = {'x': 0.0, 'y': (src_h - crop_h) / 2, 'w': float(src_w), 'h': crop_h}
    if box['w'] - src_w > 1e-6 or box['h'] - src_h > 1e-6:
        raise ValueError('裁切框不能大于原图')
    box.update({
        'target_ratio': float(target_ratio),
        'stretched': False,
        'scale_x': 1.0,
        'scale_y': 1.0,
    })
    return box


def _visible_index(html: str):
    chars = []
    index = 0
    length = len(html)
    while index < length:
        if html.startswith('<', index):
            end = html.find('>', index)
            if end < 0:
                break
            tag = html[index:end + 1]
            name_match = re.match(r'</?\s*([a-zA-Z0-9]+)', tag)
            name = name_match.group(1).lower() if name_match else ''
            if name in _SKIP_TAGS and not tag.startswith('</'):
                closer = re.search(rf'</{name}\s*>', html[end + 1:], re.IGNORECASE)
                index = end + 1 + closer.end() if closer else end + 1
                continue
            index = end + 1
            continue
        chars.append((index, html[index]))
        index += 1
    return ''.join(char for _, char in chars), chars


def _safe_src(src: str) -> str:
    if not isinstance(src, str) or not src.strip():
        raise ImageOpError('缺少图片地址')
    if any(char in src for char in '<>"\' \n\r\t'):
        raise ImageOpError('图片地址含有空白或标记，已停止')
    return src


def _locate_image(html: str, anchor: str, old_src: str | None):
    if not anchor or not anchor.strip():
        raise ImageOpError('缺少段落锚点，已停止，没有按序号替换')
    visible, chars = _visible_index(html)
    occurrences = []
    start = 0
    while True:
        found = visible.find(anchor, start)
        if found < 0:
            break
        occurrences.append(found)
        start = found + len(anchor)
    if len(occurrences) != 1:
        raise ImageOpError('锚点不是唯一段落，已停止，没有按序号猜')
    html_end = chars[occurrences[0] + len(anchor) - 1][0] + 1
    next_heading = re.search(r'<h[1-3]\b', html[html_end:], re.IGNORECASE)
    limit = html_end + next_heading.start() if next_heading else len(html)
    imgs = []
    for match in re.finditer(r'<img\b[^>]*>', html[html_end:limit], re.IGNORECASE):
        tag = match.group(0)
        imgs.append((html_end + match.start(), html_end + match.end(), _src_of(tag), tag))
    if old_src:
        imgs = [item for item in imgs if item[2] == old_src]
    if len(imgs) != 1:
        seen = [item[2] for item in imgs] or ['（范围内没有匹配图片）']
        raise ImageOpError('锚点范围内的图片不唯一：' + ' | '.join(seen))
    return imgs[0], html_end, limit


def _set_src(tag: str, new_src: str) -> str:
    if re.search(r'\bsrc\s*=', tag, re.IGNORECASE):
        return re.sub(
            r'\bsrc\s*=\s*(["\']).*?\1',
            lambda match: f'src={match.group(1)}{new_src}{match.group(1)}',
            tag,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return tag[:-1] + f' src="{new_src}">'


def apply_image_ops(html: str, ops: list[dict]) -> tuple[str, list[dict]]:
    """Replace, add, or keep images by paragraph anchor. Parent markup stays."""
    current = html
    manifest = []
    for op in ops:
        action = op.get('action')
        anchor = op.get('anchor', '')
        if action == 'keep':
            (start, end, src, _tag), _html_end, _limit = _locate_image(current, anchor, op.get('old_src'))
            del start, end
            manifest.append({'action': 'keep', 'anchor': anchor, 'src': src})
            continue
        if action == 'replace':
            new_src = _safe_src(op.get('new_src', ''))
            (start, end, old, _tag), _html_end, _limit = _locate_image(current, anchor, op.get('old_src'))
            current = current[:start] + _set_src(current[start:end], new_src) + current[end:]
            manifest.append({
                'action': 'replace',
                'anchor': anchor,
                'from': old,
                'to': new_src,
                'publish_success': image_upload_counts_as_success(new_src),
            })
            continue
        if action == 'add':
            new_src = _safe_src(op.get('new_src', ''))
            located_visible, located_chars = _visible_index(current)
            found = located_visible.find(anchor)
            if found < 0 or located_visible.find(anchor, found + len(anchor)) >= 0:
                raise ImageOpError('锚点不是唯一段落，已停止，没有按序号猜')
            html_end = located_chars[found + len(anchor) - 1][0] + 1
            next_heading = re.search(r'<h[1-3]\b', current[html_end:], re.IGNORECASE)
            limit = html_end + next_heading.start() if next_heading else len(current)
            close_p = re.search(r'</p\s*>', current[html_end:limit], re.IGNORECASE)
            if not close_p:
                raise ImageOpError('锚点后面没有可插入的段落结尾')
            insert_at = html_end + close_p.end()
            snippet = (
                '<section style="text-align:center;">'
                f'<img src="{new_src}" style="max-width:100%;height:auto;display:block;" />'
                '</section>'
            )
            current = current[:insert_at] + snippet + current[insert_at:]
            manifest.append({
                'action': 'add',
                'anchor': anchor,
                'src': new_src,
                'publish_success': image_upload_counts_as_success(new_src),
            })
            continue
        raise ImageOpError('未知图片操作')
    return current, manifest


def _sequence_changes(before: list, after: list, label: str) -> list[dict]:
    matcher = difflib.SequenceMatcher(a=before, b=after)
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        changes.append({
            'field': label,
            'type': tag,
            'before': before[i1:i2],
            'after': after[j1:j2],
        })
    return changes


def audit_draft(
    before_html: str,
    after_html: str,
    *,
    expected_images: list[str] | None = None,
    allow_theme_plate_add: bool = False,
    expected_plate: str | None = None,
) -> dict:
    """Compare two bodies field by field. Whitespace-only serialization is allowed.

    ``ok`` means the compared fields match. It does not mean a phone preview or
    a saved draft was checked.
    """
    before_text = visible_text(before_html)
    after_text = visible_text(after_html)
    text_changes = _collapse_char_changes(before_text, after_text)
    text_ok = not text_changes
    allowed_whitespace = []
    if text_ok and before_text != after_text:
        allowed_whitespace.append({
            'kind': 'serialization_or_wrapper',
            'note': '非空白字符一致。差别只在空白或换行，包含包装和序列化造成的空白。',
        })

    before_images = image_srcs(before_html)
    after_images = image_srcs(after_html)
    image_changes = []
    if expected_images is None:
        image_changes = _sequence_changes(before_images, after_images, 'image')
    elif after_images != list(expected_images):
        image_changes.append({
            'field': 'image',
            'type': 'expected_mismatch',
            'expected': list(expected_images),
            'actual': after_images,
            'before': before_images,
        })
    images_ok = not image_changes

    bold_changes = _bold_changes(extract_bold(before_html), extract_bold(after_html))
    link_changes = _sequence_changes(extract_links(before_html), extract_links(after_html), 'link')
    before_tables = extract_tables(before_html)
    after_tables = extract_tables(after_html)
    table_changes = [] if before_tables == after_tables else [{
        'field': 'table',
        'before': before_tables,
        'after': after_tables,
    }]

    if expected_plate is not None:
        expected_plate = normalize_hex_color(expected_plate)
    before_plates = plate_colors(before_html)
    after_plates = plate_colors(after_html)
    theme_changes = []
    if before_plates != after_plates:
        allowed_add = (
            allow_theme_plate_add
            and before_plates == []
            and expected_plate is not None
            and after_plates == [expected_plate]
        )
        if allowed_add:
            theme_changes.append({'type': 'allowed_plate_add', 'color': expected_plate})
        else:
            theme_changes.append({'field': 'theme', 'before': before_plates, 'after': after_plates})
    if expected_plate is not None and after_plates != [expected_plate]:
        theme_changes.append({'field': 'theme', 'expected': [expected_plate], 'after': after_plates})
    theme_ok = not any(item.get('field') == 'theme' for item in theme_changes)

    flattened = article_flattened_to_images(after_html)
    ok = text_ok and images_ok and not bold_changes and not link_changes and not table_changes and theme_ok and not flattened
    return {
        'ok': ok,
        'text_ok': text_ok,
        'allowed_whitespace': allowed_whitespace,
        'text_changes': text_changes,
        'images_ok': images_ok,
        'image_changes': image_changes,
        'before_images': before_images,
        'after_images': after_images,
        'bold_ok': not bold_changes,
        'bold_changes': bold_changes,
        'links_ok': not link_changes,
        'link_changes': link_changes,
        'tables_ok': not table_changes,
        'table_changes': table_changes,
        'theme_ok': theme_ok,
        'theme_changes': theme_changes,
        'article_flattened_to_images': flattened,
        'used_character_count_as_equality': False,
        'phone_verified': False,
        'checked_live_editor': False,
        'compared': ['text', 'punctuation', 'images', 'bold', 'links', 'tables', 'theme'],
    }


def _collapse_char_changes(before_text: str, after_text: str) -> list[dict]:
    before = _nonsws(before_text)
    after = _nonsws(after_text)
    if before == after:
        return []
    changes = []
    matcher = difflib.SequenceMatcher(a=before, b=after)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        changes.append({
            'field': 'text',
            'type': tag,
            'before': before[i1:i2],
            'after': after[j1:j2],
        })
    return changes


def _bold_changes(before: list[dict], after: list[dict]) -> list[dict]:
    changes = []
    matcher = difflib.SequenceMatcher(
        a=[item['text'] for item in before],
        b=[item['text'] for item in after],
    )
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for left, right in zip(before[i1:i2], after[j1:j2]):
                if left['color'] != right['color']:
                    changes.append({
                        'field': 'bold',
                        'text': left['text'],
                        'before_color': left['color'],
                        'after_color': right['color'],
                    })
        else:
            changes.append({
                'field': 'bold',
                'type': tag,
                'before': before[i1:i2],
                'after': after[j1:j2],
            })
    return changes


def assess_body(html: str) -> dict:
    tables = extract_tables(html)
    pending = len(re.findall(r'data-wechat-table-pending\s*=', html or '', re.IGNORECASE))
    images = [{'src': src, 'class': classify_image_src(src)} for src in image_srcs(html)]
    non_cdn = [item['src'] for item in images if item['class'] != 'official_cdn']
    flattened = article_flattened_to_images(html)
    actions = []
    if tables:
        actions.append('正文仍有 HTML 表格。不要改用横向滑动。把格子做成手机配图，事实和来源/统计口径保持原句；没有授权不能先删用户的字。')
    if pending:
        actions.append('仍有待配图块。信息多就拆成多张，字号不要压小。矢量导出清晰 PNG 并上传官方 CDN 之后，再替换这个块。')
    if non_cdn:
        actions.append('有图片不是官方 CDN。file、data 和本地路径可以留在本地预览，不能当成草稿图片已经成功。')
    if flattened:
        actions.append('正文被收成只有图片。只有原来的表格内容可以转成配图，整篇要保持可编辑。')
    blocked = bool(tables or pending or non_cdn or flattened)
    if not blocked:
        actions.append('结构上未见 HTML 表格、待配图块或非官方图片。保存草稿、重开编辑器和手机阅读仍要人工看。')
    return {
        'blocked_by_html_table': bool(tables),
        'blocked_by_pending_table_image': bool(pending),
        'blocked_by_non_cdn_image': bool(non_cdn),
        'article_flattened_to_images': flattened,
        'html_table_count': len(tables),
        'pending_table_blocks': pending,
        'images': images,
        'actions': actions,
        'may_call_qualified': False,
        'automation_claims_phone_acceptance': False,
        'phone_verified': False,
        'checked_live_editor': False,
    }


def _load(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='离线检查公众号正文。不访问网络，退出码也不代表手机已经看过。',
    )
    sub = parser.add_subparsers(dest='cmd', required=True)

    audit = sub.add_parser('audit')
    audit.add_argument('before')
    audit.add_argument('after')
    audit.add_argument('--expect-images', help='换图后的显式 URL 顺序，用逗号分隔')
    audit.add_argument('--allow-plate-add', action='store_true')
    audit.add_argument('--plate', help='期望的底板色，例如 #F2EDE3')

    scope = sub.add_parser('scope')
    scope.add_argument('html')

    gates = sub.add_parser('gates')
    gates.add_argument('html')

    args = parser.parse_args(argv)
    if args.cmd == 'audit':
        expected = None
        if args.expect_images is not None:
            expected = [item for item in args.expect_images.split(',') if item]
        report = audit_draft(
            _load(args.before),
            _load(args.after),
            expected_images=expected,
            allow_theme_plate_add=args.allow_plate_add,
            expected_plate=args.plate,
        )
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')
        return 0 if report['ok'] else 1
    if args.cmd == 'scope':
        html = _load(args.html)
        report = migration_scope(html)
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')
        return 0
    report = assess_body(_load(args.html))
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write('\n')
    blocked = (
        report['blocked_by_html_table']
        or report['blocked_by_pending_table_image']
        or report['blocked_by_non_cdn_image']
        or report['article_flattened_to_images']
    )
    return 2 if blocked else 0


if __name__ == '__main__':
    sys.exit(main())
