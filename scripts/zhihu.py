# -*- coding: utf-8 -*-
"""知乎专栏自动发文章（requests 直连 API）

逆向自 zhuanlan.zhihu.com/write 编辑器（heifetz 前端），核心流程：

  1. 创建草稿   POST https://zhuanlan.zhihu.com/api/articles/drafts
                 {"title": ..., "delta_time": 0, "can_reward": false} -> 返回草稿对象（含 id）
  2. 更新正文   PATCH https://zhuanlan.zhihu.com/api/articles/{draft_id}/draft
                 {"content": "<p>HTML 正文</p>", "table_of_contents": false,
                  "delta_time": 秒, "can_reward": false}                -> 200 空响应
  3. 发布       POST https://www.zhihu.com/api/v4/content/publish
                 {"action": "article", "data": {...}}                  -> {"code":0,...,"id":文章id}

认证：登录态取浏览器 cookie（browser_cookie3 直读 Firefox/Chrome/Edge），
签名：x-zse-93/x-zse-96 由同目录 ``zhihu_sign.py`` 计算（模块 1514 加密）。

自包含：仅依赖同目录的 ``zhihu_sign.py`` / ``module1514.js`` / ``pub_util.py``，
以及第三方库 ``requests`` / ``browser_cookie3`` / ``quickjs``。

用法示例：
  python scripts/zhihu.py 文章.md
  python scripts/zhihu.py 文章目录
  python scripts/zhihu.py 文章.md -i 1        # 发布到第 1 个专栏
"""
import argparse
import json
import os
import re
import subprocess as subp
import sys
import tempfile
import time
import traceback
import uuid
from os import path

import requests

# 同目录自包含模块（vendored，不依赖 BookerDownloadTool / BookerMarkdownTool）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zhihu_sign
from pub_util import cookie_dict_to_str, extract_cookies_multi_browsers, get_md_title

config = {
    'draft_api': 'https://zhuanlan.zhihu.com/api/articles/drafts',
    'publish_api': 'https://www.zhihu.com/api/v4/content/publish',
    'timeout': 30,
    'ua': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'),
}

# 图片语法 ![](url) 替换为 <url>（与旧脚本一致：知乎导入时图片转链接）
RE_IMG = re.compile(r'!\[[^\]]*\]\(([^\)]+)\)')


class ZhihuError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# cookie / 签名请求
# ---------------------------------------------------------------------------

class ZhihuSession:
    """带签名头的知乎请求会话。"""

    def __init__(self, cookie, dc0):
        self.cookie = cookie
        self.dc0 = dc0
        self.sess = requests.Session()

    def _headers(self, url, body_str=None, ref='https://zhuanlan.zhihu.com/write'):
        h = zhihu_sign.make_headers(url, self.dc0, body=body_str)
        h.update({
            'User-Agent': config['ua'],
            'Referer': ref,
            'Cookie': self.cookie,
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'x-api-version': '3.0.91',
            'x-app-za': 'OS=Web',
        })
        return h

    def request(self, method, url, body=None, ref='https://zhuanlan.zhihu.com/write'):
        bstr = json.dumps(body, ensure_ascii=False, separators=(',', ':')) if body is not None else None
        if bstr is not None:
            bstr = bstr.encode('utf-8')
        h = self._headers(url, bstr.decode('utf-8') if bstr else None, ref)
        h.pop('Content-Type', None)  # requests 依据 data 的字节自动设置
        if bstr is not None:
            h['Content-Type'] = 'application/json'
        r = self.sess.request(method, url, headers=h, data=bstr, timeout=config['timeout'])
        if r.status_code in (403, 401):
            raise ZhihuError(f'HTTP {r.status_code} {method} {url}: {r.text[:300]}')
        return r


# ---------------------------------------------------------------------------
# 发布流程
# ---------------------------------------------------------------------------

def create_draft(zs: ZhihuSession, title):
    """创建草稿，返回草稿对象（含 id / url）。"""
    body = {'title': title[:100], 'delta_time': 0, 'can_reward': False}
    r = zs.request('POST', config['draft_api'], body=body)
    r.raise_for_status()
    d = r.json()
    if not d.get('id'):
        raise ZhihuError(f'创建草稿失败：{r.text[:300]}')
    print(f'[draft] id={d.get("id")} url={d.get("url")}')
    return d


def update_content(zs: ZhihuSession, draft_id, content_html, delta_time=0):
    """更新草稿正文（HTML）。"""
    url = f'https://zhuanlan.zhihu.com/api/articles/{draft_id}/draft'
    body = {
        'content': content_html,
        'table_of_contents': False,
        'delta_time': delta_time,
        'can_reward': False,
    }
    r = zs.request('PATCH', url, body=body)
    r.raise_for_status()
    print(f'[content] 正文已更新（{len(content_html)} 字符 HTML）')


def build_publish_data(draft_id, title, content_html, trace_id, column_id=None):
    """构造 /api/v4/content/publish 的 data（字段来自编辑器前端抓包）。"""
    pc_params = {
        'commentPermission': 'anyone',
        'disclaimer_type': 'none',
        'disclaimer_status': 'close',
        'table_of_contents_enabled': False,
        'content': content_html,
        'title': title,
        'commercial_report_info': {'is_report': False, 'commercial_types': []},
        'commercial_zhitask_bind_info': None,
        'canReward': False,
    }
    data = {
        'publish': {'traceId': trace_id},
        'extra_info': {
            'publisher': 'pc',
            'pc_business_params': json.dumps(pc_params, ensure_ascii=False, separators=(',', ':')),
        },
        'draft': {'disabled': 1, 'id': str(draft_id), 'isPublished': False},
        'commentsPermission': {'comment_permission': 'anyone'},
        'creationStatement': {'disclaimer_type': 'none', 'disclaimer_status': 'close'},
        'contentsTables': {'table_of_contents_enabled': False},
        'commercialReportInfo': {'isReport': 0},
        'appreciate': {'can_reward': False, 'tagline': ''},
        'hybridInfo': {},
    }
    if column_id:
        data['column'] = {'column': [column_id]}   # 发布到专栏（前端：selectedColumnId）
    return data


def publish(zs: ZhihuSession, draft_id, title, content_html, column_id=None):
    """发布草稿，返回 (文章id, url)。"""
    trace_id = f'{int(time.time() * 1000)},{uuid.uuid4()}'
    data = build_publish_data(draft_id, title, content_html, trace_id, column_id)
    payload = {'action': 'article', 'data': data}
    r = zs.request('POST', config['publish_api'], body=payload)
    r.raise_for_status()
    d = r.json()
    if d.get('code') != 0 or not d.get('data'):
        raise ZhihuError(f'发布失败：{r.text[:500]}')
    # result 是字符串化的 JSON，内含 publish.id
    aid = None
    try:
        resd = json.loads(d['data'].get('result', '{}'))
        aid = resd.get('publish', {}).get('id') or resd.get('publish', {}).get('id_str')
    except Exception:
        pass
    if not aid:
        raise ZhihuError(f'发布响应缺少文章 id：{r.text[:400]}')
    url = f'https://zhuanlan.zhihu.com/p/{aid}'
    print(f'[publish] 成功 文章id={aid}  url={url}')
    return aid, url


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

def md2html(md):
    """md 正文转 HTML：优先 pandoc，其次内置简单转换。"""
    # 图片语法转 <url>（与旧脚本 zhihu_post_sele.py 一致）
    md = RE_IMG.sub(r'<\1>', md)
    # pandoc
    try:
        fname = path.join(tempfile.gettempdir(), uuid.uuid4().hex + '.md')
        ofname = fname[:-3] + '.html'
        open(fname, 'w', encoding='utf8').write(md)
        subp.Popen(['pandoc', fname, '-o', ofname]).communicate()
        html = open(ofname, encoding='utf8').read()
        try: os.remove(fname)
        except OSError: pass
        try: os.remove(ofname)
        except OSError: pass
        return html
    except Exception:
        pass
    # 内置简单转换：段落 / 标题 / 列表 / 加粗
    lines, buf = md.split('\n'), []

    def esc(s):
        s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        s = re.sub(r'\*(.+?)\*', r'<i>\1</i>', s)
        s = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\1">\1</a>', s)
        return s

    for ln in lines:
        ln = ln.rstrip()
        if not ln.strip():
            continue
        if re.match(r'^#{1,6}\s', ln):
            lv = len(ln) - len(ln.lstrip('#'))
            buf.append(f'<h{lv}>{esc(ln.lstrip("# ").strip())}</h{lv}>')
        elif re.match(r'^\s*[-*+]\s', ln):
            item = re.sub(r'^\s*[-*+]\s', '', ln)
            buf.append(f'<p>{esc(item)}</p>')
        else:
            buf.append(f'<p>{esc(ln.strip())}</p>')
    return '\n'.join(buf)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def post_one(zs, fname, args):
    """处理单个 md 文件：解析标题 -> 创建草稿 -> 填正文 -> 发布。"""
    md = open(fname, encoding='utf8').read()
    title, pos = get_md_title(md)
    if not title:
        print(f'{fname} MD 文件无标题，跳过')
        return False
    title = re.sub(r'[^\u0000-￿]', '', title)[:100]
    body_md = md[pos[1]:] if pos else md
    print(f'[info] 标题: {title}')
    print(f'[info] 正文 md: {len(body_md)} 字符')

    # 专栏 id
    column_id = None
    if args.col_id:
        column_id = args.col_id
    elif args.col_idx > 0:
        cols = fetch_columns_for_user(zs)
        if 1 <= args.col_idx <= len(cols):
            column_id = cols[args.col_idx - 1][0]
            print(f'[column] 选择 {cols[args.col_idx - 1][1]} (id={column_id})')
        else:
            print(f'[column] 专栏序号越界（共 {len(cols)} 个），按普通文章发布')

    if args.dry_run:
        print('[dry-run] 跳过发布')
        return False   # 不删除源文件

    content_html = md2html(body_md)
    d = create_draft(zs, title)
    update_content(zs, d['id'], content_html, delta_time=1)
    aid, url = publish(zs, d['id'], title, content_html, column_id)
    return bool(aid)


# 需要在 CLI 上下文里的 token（这里简单处理：从 /api/v4/me 拿）
def fetch_columns_for_user(zs):
    try:
        r = zs.request('GET', 'https://www.zhihu.com/api/v4/me', ref='https://zhuanlan.zhihu.com/')
        r.raise_for_status()
        url_token = r.json().get('url_token', '')
        if url_token:
            from urllib.parse import quote
            url = (f'https://www.zhihu.com/api/v4/members/{url_token}/column-contributions'
                   f'?offset=0&limit=50&include=' + quote('data[*].column.articles_count'))
            r2 = zs.request('GET', url, ref='https://zhuanlan.zhihu.com/write')
            r2.raise_for_status()
            return [(str(c['column']['id']), c['column'].get('title', ''))
                    for c in r2.json().get('data', []) if c.get('column')]
    except Exception as ex:
        print(f'[column] 获取专栏列表失败: {type(ex).__name__} {str(ex)[:80]}')
    return []


def publish_zhihu(args):
    if path.isfile(args.fname):
        fnames = [args.fname]
    else:
        fnames = [path.join(args.fname, f) for f in os.listdir(args.fname) if f.endswith('.md')]
    fnames = [f for f in fnames if path.isfile(f)]
    if not fnames:
        print('请提供 MD 文件或目录')
        return

    cookie = extract_cookies_multi_browsers('zhihu.com')
    cookie = cookie_dict_to_str(cookie)
    dc0 = zhihu_sign.get_dc0_from_cookie(cookie)
    zs = ZhihuSession(cookie, dc0)

    for f in fnames:
        print(f'\n===== {f} =====')
        try:
            ok = post_one(zs, f, args)
            if ok:
                os.remove(f)
                print(f'[ok] 已删除 {f}')
        except KeyboardInterrupt:
            raise
        except ZhihuError as e:
            print(f'[error] {e}')
        except Exception:
            traceback.print_exc()


def add_arguments(parser):
    parser.add_argument('fname', help='Markdown 文件或目录路径')
    parser.add_argument('-i', '--col-idx', type=int, default=0, help='专栏序号（从 1 开始，0=不发布到专栏）')
    parser.add_argument('-c', '--col-id', default='', help='按专栏 id 发布（如知 123456，优先于 --col-idx）')
    parser.add_argument('-r', '--retry', type=int, default=3, help='发布失败重试次数')
    parser.add_argument('-n', '--dry-run', action='store_true', help='只打印流程不真正发布')


def reg_subparser(subparsers):
    parser = subparsers.add_parser("zhihu", help="知乎文章发布")
    add_arguments(parser)
    parser.set_defaults(func=publish_zhihu)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog="zhihu",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_arguments(parser)
    parser.set_defaults(func=publish_zhihu)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
