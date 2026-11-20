#!/usr/bin/env python3
"""Synthetic checks for WeChat body fidelity. No live editor and no phone preview."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import unescape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from md2wechat_formatter import THEMES, build_css, render_markdown  # noqa: E402
from wechat_fidelity import (  # noqa: E402
    FISH_PRESET,
    COVER_RATIO,
    ImageOpError,
    THUMB_RATIO,
    apply_image_ops,
    article_flattened_to_images,
    assess_body,
    assess_image_source,
    audit_draft,
    brand_preset,
    classify_image_src,
    crop_box,
    defer_html_tables,
    extract_bold,
    extract_paste_payload,
    image_upload_counts_as_success,
    migration_scope,
    sibling_margin_gap_risk,
    simulate_editor_reopen,
    table_image_plan,
    wrap_theme_plate,
)

CDN_A = 'https://mmbiz.qpic.cn/a.png'
CDN_B = 'https://mmbiz.qpic.cn/b.png'
CDN_C = 'https://mmbiz.qpic.cn/c.png'


def svg_plain(cards: list[str]) -> str:
    import re
    raw = ''.join(re.findall(r'<text\b[^>]*>(.*?)</text>', ''.join(cards)))
    return unescape(raw)


class ThemePlateTests(unittest.TestCase):
    def test_one_plate_covers_sibling_sections_and_list(self):
        blocks = ''.join(
            f'<section style="background-color:#F2EDE3;"><p>段{index}</p></section>'
            for index in range(12)
        )
        inner = blocks + '<ul><li style="margin:0 0 8px;">末项</li></ul>'
        bare = sibling_margin_gap_risk(inner)
        self.assertTrue(bare['gap_risk'])
        self.assertIn('sibling_backgrounds_without_plate', bare['reasons'])
        self.assertIn('list_outside_plate', bare['reasons'])
        self.assertFalse(bare['phone_verified'])

        wrapped = wrap_theme_plate(inner, '#F2EDE3')
        closed = sibling_margin_gap_risk(wrapped)
        self.assertFalse(closed['gap_risk'])
        self.assertEqual(wrapped.count('padding:1px 0'), 1)
        again = wrap_theme_plate(wrapped, '#f2ede3')
        self.assertEqual(again.count('padding:1px 0'), 1)

    def test_reopen_keeps_style_without_claiming_a_live_editor(self):
        wrapped = wrap_theme_plate('<p>甲</p><ul><li>乙</li></ul>', '#F2EDE3')
        tagged = wrapped.replace('<section ', '<section id="plate" ', 1)
        reopened = simulate_editor_reopen(tagged)
        self.assertNotIn('id=', reopened)
        self.assertIn('background-color:#F2EDE3;padding:1px 0', reopened)
        self.assertFalse(sibling_margin_gap_risk(reopened)['gap_risk'])
        self.assertFalse(sibling_margin_gap_risk(reopened)['checked_live_editor'])

    def test_paste_payload_is_not_the_body_background(self):
        html, _tables = render_markdown('甲\n\n- 乙\n\n## 第二节\n\n下一段。\n')
        self.assertIn('body {', html)
        self.assertIn('background: #F2EDE3', html)
        payload = extract_paste_payload(html)
        self.assertNotIn('<body', payload.lower())
        self.assertNotIn('<style', payload.lower())
        self.assertIn('background-color:#F2EDE3;padding:1px 0', payload)
        self.assertIn('乙', payload)
        self.assertFalse(sibling_margin_gap_risk(payload)['gap_risk'])
        self.assertEqual(payload.count('padding:1px 0'), 1)


class BrandTests(unittest.TestCase):
    def test_01fish_preset_does_not_repaint_other_themes(self):
        fish = brand_preset('01fish')
        self.assertEqual(fish['paper'], '#F2EDE3')
        self.assertEqual(fish['ink'], '#1A3328')
        self.assertEqual(fish['fish_red'], '#C44536')
        self.assertEqual(fish['body_px'], 15)
        self.assertEqual(fish['line_height'], '2')
        self.assertEqual(fish['h2_px'], 20)
        self.assertEqual(fish['h3_px'], 17)
        self.assertEqual(fish['caption_px'], 13)
        overridden = brand_preset('01fish', {'paper': '#FFFFFF'})
        self.assertEqual(overridden['paper'], '#FFFFFF')
        self.assertEqual(FISH_PRESET['paper'], '#F2EDE3')
        with self.assertRaises(KeyError):
            brand_preset('chinese')

        fish_css = build_css('01fish', 'medium')
        other_css = build_css('chinese', 'medium')
        self.assertIn('font-size: 15px', fish_css)
        self.assertIn('line-height: 2', fish_css)
        self.assertIn('font-size: 20px', fish_css)
        self.assertIn('font-size: 17px', fish_css)
        self.assertIn('font-size: 13px', fish_css)
        self.assertIn('color: #C44536', fish_css)
        self.assertIn('color: #1A3328', fish_css)
        self.assertIn('line-height: 1.75', other_css)
        self.assertIn('background: #F9F5F1', other_css)
        self.assertNotIn('#C44536', other_css)
        self.assertEqual(THEMES['chinese']['heading'], '#8B0000')
        self.assertIn('height: auto', fish_css)


class TableGateTests(unittest.TestCase):
    def test_new_body_keeps_cells_and_refuses_a_qualified_claim(self):
        html, tables = render_markdown(
            '| 项 | 统计口径 |\n| --- | --- |\n| 样本 | 全量且不截断 |\n'
        )
        payload = extract_paste_payload(html)
        self.assertNotIn('<table', payload.lower())
        self.assertIn('样本', payload)
        self.assertIn('全量且不截断', payload)
        self.assertIn('统计口径', payload)
        self.assertEqual(tables[0]['rows'], [['样本', '全量且不截断']])
        gate = assess_body(payload)
        self.assertTrue(gate['blocked_by_pending_table_image'])
        self.assertFalse(gate['blocked_by_html_table'])
        self.assertFalse(gate['may_call_qualified'])
        self.assertFalse(gate['phone_verified'])
        self.assertFalse(gate['automation_claims_phone_acceptance'])
        self.assertTrue(any('待配图' in action for action in gate['actions']))

        original = '<table><tr><th>统计口径</th></tr><tr><td>全量且不截断</td></tr></table>'
        scope = migration_scope(original)
        self.assertFalse(scope['authorized_to_rewrite_user_text'])
        self.assertFalse(scope['mutated'])
        self.assertTrue(scope['overflow_x_is_not_a_fix'])
        self.assertEqual(scope['tables'][0]['rows'], [['全量且不截断']])
        self.assertEqual(original, '<table><tr><th>统计口径</th></tr><tr><td>全量且不截断</td></tr></table>')
        replaced, found = defer_html_tables(original)
        self.assertNotIn('<table', replaced.lower())
        self.assertEqual(found[0]['source_lines'], ['统计口径：全量且不截断'])

    def test_svg_cards_keep_facts_and_are_not_a_png(self):
        table = {
            'caption': '对照',
            'headers': ['H0', 'H1', 'H2', 'H3', 'H4'],
            'rows': [[f'C{row}{col}' for col in range(5)] for row in range(7)],
            'source_lines': ['统计口径：全量且不截断'],
        }
        plan = table_image_plan(table)
        self.assertGreaterEqual(plan['card_count'], 4)
        self.assertFalse(plan['png_rendered'])
        self.assertFalse(plan['wechat_ready'])
        self.assertFalse(plan['phone_verified'])
        plain = svg_plain(plan['cards'])
        self.assertIn('统计口径：全量且不截断', plain)
        for header in table['headers']:
            self.assertIn(header, plain)
        for row in table['rows']:
            for cell in row:
                self.assertIn(cell, plain)
        blob = ''.join(plan['cards'])
        self.assertNotIn('clipPath', blob)
        self.assertNotIn('textLength', blob)
        self.assertNotIn('...', blob)
        self.assertIn('width="390"', blob)
        sizes = [int(item) for item in __import__('re').findall(r'font-size="(\d+)"', blob)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 16)
        with self.assertRaises(ValueError):
            table_image_plan({'headers': ['A'], 'rows': [['B']], 'source_lines': []}, font_px=15)

    def test_existing_table_blocks_a_clean_claim(self):
        gate = assess_body('<table><tr><td>甲</td></tr></table>')
        self.assertTrue(gate['blocked_by_html_table'])
        self.assertFalse(gate['may_call_qualified'])
        clean = assess_body('<section style="background-color:#F2EDE3;padding:1px 0;"><p>甲</p></section>')
        self.assertFalse(clean['blocked_by_html_table'])
        self.assertFalse(clean['blocked_by_pending_table_image'])
        self.assertFalse(clean['may_call_qualified'])
        self.assertFalse(clean['phone_verified'])


class AuditTests(unittest.TestCase):
    def test_whitespace_only_is_not_a_word_change(self):
        report = audit_draft('<p>甲乙</p>', '<p>甲\n乙</p>')
        self.assertTrue(report['text_ok'])
        self.assertTrue(report['allowed_whitespace'])
        self.assertEqual(report['text_changes'], [])
        self.assertFalse(report['used_character_count_as_equality'])
        self.assertFalse(report['phone_verified'])

    def test_punctuation_and_same_length_swap_are_reported(self):
        punct = audit_draft('<p>甲。</p>', '<p>甲</p>')
        self.assertFalse(punct['text_ok'])
        self.assertTrue(any('。' in item['before'] for item in punct['text_changes']))
        swapped = audit_draft('<p>甲乙</p>', '<p>乙甲</p>')
        self.assertFalse(swapped['text_ok'])
        self.assertNotEqual(swapped['text_changes'], [])

    def test_images_bold_links_tables_and_theme(self):
        before = (
            '<section style="background-color:#F2EDE3;padding:1px 0;">'
            '<p style="color:#C44536"><strong>重点</strong></p>'
            '<a href="https://example.com/a">链接</a>'
            f'<img src="{CDN_A}" /><img src="{CDN_B}" />'
            '<table><tr><td>格子</td></tr></table>'
            '</section>'
        )
        lost = before.replace(f'<img src="{CDN_B}" />', '')
        lost_report = audit_draft(before, lost)
        self.assertFalse(lost_report['images_ok'])
        blob = json.dumps(lost_report['image_changes'], ensure_ascii=False)
        self.assertIn(CDN_B, blob)

        swapped = before.replace(CDN_A, 'SWAP').replace(CDN_B, CDN_A).replace('SWAP', CDN_B)
        order = audit_draft(before, swapped)
        self.assertFalse(order['images_ok'])
        self.assertEqual(order['before_images'], [CDN_A, CDN_B])
        self.assertEqual(order['after_images'], [CDN_B, CDN_A])

        mapped = audit_draft(before, swapped, expected_images=[CDN_B, CDN_A])
        self.assertTrue(mapped['images_ok'])

        recolored = before.replace('<p style="color:#C44536">', '<p style="color:#333333">')
        color = audit_draft(before, recolored)
        self.assertFalse(color['bold_ok'])
        self.assertEqual(color['bold_changes'][0]['text'], '重点')
        self.assertEqual(color['bold_changes'][0]['before_color'], '#C44536')
        self.assertEqual(color['bold_changes'][0]['after_color'], '#333333')
        own = extract_bold('<p style="color:#333333"><strong style="color:#C44536">重点</strong></p>')
        self.assertEqual(own[0]['color'], '#C44536')

        unlinked = before.replace('https://example.com/a', 'https://example.com/b')
        self.assertFalse(audit_draft(before, unlinked)['links_ok'])

        no_table = before.replace('<table><tr><td>格子</td></tr></table>', '')
        tables = audit_draft(before, no_table)
        self.assertFalse(tables['tables_ok'])
        self.assertEqual(tables['table_changes'][0]['before'][0]['rows'], [['格子']])

        no_plate = before.replace(
            '<section style="background-color:#F2EDE3;padding:1px 0;">',
            '<section>',
        )
        self.assertFalse(audit_draft(before, no_plate)['theme_ok'])
        added = audit_draft(
            '<p>甲</p>',
            wrap_theme_plate('<p>甲</p>', '#F2EDE3'),
            allow_theme_plate_add=True,
            expected_plate='#F2EDE3',
        )
        self.assertTrue(added['theme_ok'])
        self.assertTrue(added['ok'])

    def test_image_ops_use_anchors_and_keep_the_plate(self):
        html = (
            '<section style="background-color:#F2EDE3;padding:1px 0;">'
            '<h2>甲</h2><p>第一段</p>'
            f'<section><img src="{CDN_A}" /></section>'
            '<h2>乙</h2><p>第二段锚点</p><p><strong>重点</strong>来源保留</p>'
            f'<section><img src="{CDN_B}" /></section>'
            '</section>'
        )
        changed, manifest = apply_image_ops(html, [{
            'action': 'replace',
            'anchor': '第二段锚点',
            'old_src': CDN_B,
            'new_src': CDN_C,
        }])
        self.assertIn(CDN_A, changed)
        self.assertNotIn(CDN_B, changed)
        self.assertIn(CDN_C, changed)
        self.assertIn('padding:1px 0', changed)
        self.assertIn('<strong>重点</strong>', changed)
        self.assertEqual(changed.count('<section'), html.count('<section'))
        self.assertTrue(manifest[0]['publish_success'])
        report = audit_draft(html, changed, expected_images=[CDN_A, CDN_C])
        self.assertTrue(report['text_ok'])
        self.assertTrue(report['images_ok'])
        self.assertTrue(report['bold_ok'])
        self.assertTrue(report['theme_ok'])

        with self.assertRaises(ImageOpError):
            apply_image_ops(
                f'<p>锚点</p><img src="{CDN_A}" /><img src="{CDN_B}" />',
                [{'action': 'replace', 'anchor': '锚点', 'new_src': CDN_C}],
            )
        local, local_manifest = apply_image_ops(
            '<p>锚点</p><img src="file:///tmp/a.png" />',
            [{'action': 'replace', 'anchor': '锚点', 'new_src': 'data:image/png;base64,aaaa'}],
        )
        self.assertIn('data:image/png;base64,aaaa', local)
        self.assertFalse(local_manifest[0]['publish_success'])
        self.assertFalse(image_upload_counts_as_success('file:///tmp/a.png'))
        self.assertEqual(classify_image_src(CDN_A), 'official_cdn')
        self.assertNotEqual(classify_image_src('http://mmbiz.qpic.cn/a.png'), 'official_cdn')
        self.assertTrue(article_flattened_to_images(f'<img src="{CDN_A}" />'))
        self.assertFalse(article_flattened_to_images(f'<p>甲</p><img src="{CDN_A}" />'))

        added, added_manifest = apply_image_ops(
            '<section style="background-color:#F2EDE3;padding:1px 0;"><p>仅此一段</p></section>',
            [{'action': 'add', 'anchor': '仅此一段', 'new_src': CDN_A}],
        )
        self.assertLess(added.find(CDN_A), added.rfind('</section>'))
        self.assertIn('仅此一段', added)
        self.assertEqual(added_manifest[0]['action'], 'add')


class ImagePolicyTests(unittest.TestCase):
    def test_cover_and_thumb_crop_do_not_stretch(self):
        cover = crop_box(2350, 800, COVER_RATIO)
        thumb = crop_box(2350, 800, THUMB_RATIO)
        self.assertFalse(cover['stretched'])
        self.assertFalse(thumb['stretched'])
        self.assertAlmostEqual(cover['w'] / cover['h'], COVER_RATIO)
        self.assertAlmostEqual(thumb['w'] / thumb['h'], THUMB_RATIO)
        self.assertLessEqual(cover['w'], 2350)
        self.assertLessEqual(cover['h'], 800)
        self.assertLessEqual(thumb['w'], 2350)
        self.assertLessEqual(thumb['h'], 800)
        self.assertNotEqual((cover['w'], cover['h']), (thumb['w'], thumb['h']))
        self.assertEqual(cover['scale_x'], 1.0)
        self.assertEqual(thumb['scale_y'], 1.0)
        shot = assess_image_source('screenshot', 2)
        self.assertFalse(shot['accept'])
        self.assertFalse(shot['png_rendered'])
        vector = assess_image_source('vector')
        self.assertTrue(vector['accept'])
        self.assertFalse(vector['png_rendered'])
        self.assertEqual(vector['css_width'], 390)
        self.assertTrue(assess_image_source('photo')['keep_natural_ratio'])


class ToolAndDocTests(unittest.TestCase):
    def test_workbench_is_local_and_explicit(self):
        text = (ROOT / 'scripts' / 'wechat-draft-workbench.html').read_text(encoding='utf-8')
        self.assertNotIn('fetch(', text)
        self.assertNotIn('XMLHttpRequest', text)
        self.assertNotIn('WebSocket', text)
        self.assertNotIn('clipboard.read', text)
        self.assertNotIn('.readText', text)
        self.assertNotIn('readText(', text)
        self.assertIn('ClipboardItem', text)
        self.assertIn("addEventListener(\"paste\"", text)
        self.assertIn('type="file"', text)
        self.assertEqual(text.count('innerHTML'), 1)
        self.assertIn('parsed.body.innerHTML', text)
        self.assertNotIn('document.body.innerHTML', text)
        self.assertNotIn('insertAdjacentHTML', text)
        self.assertIn('phone_verified=false', text)
        self.assertNotIn('WECHAT_APPSECRET', text)

    def test_fallback_docs_agree(self):
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        guide = (ROOT / 'references' / 'distribute-platforms.md').read_text(encoding='utf-8')
        fidelity = (ROOT / 'references' / 'wechat-draft-fidelity.md').read_text(encoding='utf-8')
        for document in (skill, guide, fidelity):
            self.assertNotIn('API 凭证缺失或调用失败时降级 L1', document)
            self.assertNotIn('API 调用失败 → L0 降级为 L1', document)
        self.assertIn('停在 L3', fidelity)
        self.assertIn('computerUse', skill)
        self.assertIn('不是发布', skill)

    def test_cli_exit_codes_do_not_mean_phone_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            before = directory / 'before.html'
            after = directory / 'after.html'
            table = directory / 'table.html'
            plain = directory / 'plain.html'
            before.write_text('<p>甲乙</p>', encoding='utf-8')
            after.write_text('<p>甲\n乙</p>', encoding='utf-8')
            table.write_text('<table><tr><td>格子</td></tr></table>', encoding='utf-8')
            plain.write_text('<p>甲</p>', encoding='utf-8')
            original = table.read_bytes()
            audit = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'wechat_fidelity.py'), 'audit', str(before), str(after)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(audit.returncode, 0)
            self.assertIn('"phone_verified": false', audit.stdout)
            changed = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'wechat_fidelity.py'), 'audit', str(before), str(plain)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(changed.returncode, 1)
            scope = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'wechat_fidelity.py'), 'scope', str(table)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(scope.returncode, 0)
            self.assertEqual(table.read_bytes(), original)
            self.assertIn('格子', scope.stdout)
            gates = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'wechat_fidelity.py'), 'gates', str(table)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(gates.returncode, 2)
            self.assertIn('"may_call_qualified": false', gates.stdout)
            clear = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'wechat_fidelity.py'), 'gates', str(plain)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(clear.returncode, 0)
            self.assertIn('"phone_verified": false', clear.stdout)


if __name__ == '__main__':
    unittest.main()
