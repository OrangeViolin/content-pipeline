# -*- coding: utf-8 -*-
"""weibo — 发布微博（Playwright 版，结构参照 jike-plrt）。

接受一个 MD 文件或目录，把每篇 Markdown 转成微博正文并发布到微博。
- 正文来源：MD 的 H1 作为首行（--no-title 关闭），正文转纯文本，
  超长文本按段落自动拆分为多条微博（--max-chars，默认 2000 字）。
- 登录态：优先注入 --cookie 或本机浏览器 weibo.com 的 Cookie；
  否则在打开的浏览器中人工扫码/登录。
- 发布失败时退回「辅助模式」：内容已预填，留浏览器给人工审阅/发布。

自包含：仅依赖同目录的 ``pub_util.py``，以及第三方库 ``playwright`` /
``browser_cookie3``（``playwright install chromium``）。

用法:
    python scripts/weibo.py --input 文章.md
    python scripts/weibo.py --input 文章目录 --max-chars 140
    python scripts/weibo.py --input 文章.md --preview          # 只预填不发布
"""
import re
import os
import sys
from os import path

# 同目录自包含工具（vendored，不依赖 BookerPubTool 包）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pub_util import (
    timestr, plrt_create_driver, read_file, get_md_title, cookie_str_to_dict,
    extract_cookies_multi_browsers, status_print, hold_browser,
)

WEIBO_URL = 'https://weibo.com/'
COMPOSE_URL = 'https://weibo.com/compose'

SELECTORS = {
    'loginIndicator': (
        'img[class*="avatar"], div[class*="Avatar"], '
        'span[class*="avatar"], a[class*="avatar"]'),
    'composeBtn': (
        'a[href*="compose"], div[class*="composer"], '
        'textarea[placeholder*="分享"], div[contenteditable="true"]'),
    'contentEditor': (
        'div[contenteditable="true"], textarea[placeholder*="分享"], '
        '[aria-label*="微博正文"], div[role="textbox"]'),
    'publishBtn': (
        'button:has-text("发布"), div[class*="publish"]:has-text("发布"), '
        'button[class*="send"], button[class*="submit"]'),
}

_MD_IMG_RE = re.compile(r'!\[([^\]]*)\]\([^)]+\)')
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_MD_TAG_RE = re.compile(r'<[^>]+>')


# ---------------------------------------------------------------------------
# Markdown -> 微博正文
# ---------------------------------------------------------------------------

def _md_to_text(md):
    """粗略把 Markdown 转成微博正文纯文本。"""
    s = md
    s = _MD_TAG_RE.sub('', s)                                  # 去 HTML 标签
    s = _MD_IMG_RE.sub(r'\1', s)                               # 图片 -> alt 文字
    s = _MD_LINK_RE.sub(r'\1', s)                              # 链接 -> 文字
    s = re.sub(r'^\s{0,3}#{1,6}\s+', '', s, flags=re.M)        # 去标题井号
    s = re.sub(r'^\s{0,3}[-*+]\s+', '· ', s, flags=re.M)       # 列表符
    s = re.sub(r'^\s{0,3}>+\s?', '', s, flags=re.M)            # 引用
    s = re.sub(r'^`{1,3}[\s\S]*?`{1,3}$', '', s, flags=re.M)   # 代码块
    s = re.sub(r'\*\*|__|`|~~', '', s)                         # 强调/代码标记
    lines = [ln.rstrip() for ln in s.splitlines()]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def _split_posts(text, max_chars):
    """按空行分段，打包成 <= max_chars 字的多条微博。"""
    paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    posts, cur = [], ''
    for p in paras:
        if len(p) > max_chars:
            if cur:
                posts.append(cur)
                cur = ''
            while len(p) > max_chars:
                posts.append(p[:max_chars])
                p = p[max_chars:]
            cur = p
        elif cur and len(cur) + 1 + len(p) > max_chars:
            posts.append(cur)
            cur = p
        else:
            cur = p if not cur else cur + '\n' + p
    if cur:
        posts.append(cur)
    return posts


def _md_to_posts(md, max_chars, include_title=True):
    """把一篇 MD 转成若干条微博正文。"""
    title, pos = get_md_title(md)
    body = md[pos[1]:] if pos[0] else md
    body_text = _md_to_text(body)
    title_text = title.strip() if title else ''
    if include_title and title_text:
        body_text = f'{title_text}\n\n{body_text}' if body_text else title_text
    return _split_posts(body_text, max_chars) or ([title_text] if title_text else [])


def _collect_md(input_path, num):
    """收集待发布的 MD 文件（文件或目录）。"""
    if not input_path:
        status_print('manual', 'No MD file or directory provided. Pass --input <MD 文件或目录>.')
        return []
    if path.isfile(input_path):
        return [input_path] if input_path.endswith('.md') else []
    if path.isdir(input_path):
        fnames = sorted(f for f in os.listdir(input_path) if f.endswith('.md'))
        return [path.join(input_path, f) for f in fnames[:num]]
    return []


# ---------------------------------------------------------------------------
# 登录态
# ---------------------------------------------------------------------------

def get_cookies(args):
    """Cookie 来源：显式指定 > 浏览器提取。"""
    if args.cookie:
        cookies = cookie_str_to_dict(args.cookie)
        if not cookies:
            status_print('error', '无法解析 --cookie，请提供形如 "SUB=xxx; SUBP=yyy" 的字符串')
        return cookies
    cookies = extract_cookies_multi_browsers('weibo.com')
    if not cookies:
        cookies = extract_cookies_multi_browsers('weibo.cn')
    cookies = cookies or {}
    print(f'{timestr()} 从浏览器提取到 {len(cookies)} 个微博 cookie')
    return cookies


def _inject_cookies(context, cookies):
    if not cookies:
        print(f'{timestr()} 未注入微博 Cookie，将采用浏览器人工登录')
        return
    try:
        context.add_cookies([
            {'name': k, 'value': v, 'domain': 'weibo.com', 'path': '/'}
            for k, v in cookies.items()
        ])
    except Exception:
        pass


def _ensure_login(page, args):
    page.goto(WEIBO_URL, wait_until='domcontentloaded')
    page.wait_for_timeout(3000)
    if 'passport.weibo.com' in page.url:
        status_print('assisted', '未登录微博。请在浏览器中完成登录。')
        if args.headless:
            status_print('error', '无头模式下无法人工登录，请去掉 -H 或提供 Cookie。')
            return False
        hold_browser('请在浏览器中扫码/登录微博，完成后回车继续。')
        page.goto(WEIBO_URL, wait_until='domcontentloaded')
        page.wait_for_timeout(2500)
        if 'passport.weibo.com' in page.url:
            status_print('error', '登录失败，请检查 Cookie 或重新登录。')
            return False
    return True


# ---------------------------------------------------------------------------
# 发布器交互
# ---------------------------------------------------------------------------

def _open_compose(page):
    """打开微博发布器（优先直接访问 compose 页，退回首页找发布入口）。"""
    try:
        page.goto(COMPOSE_URL, wait_until='domcontentloaded')
        page.wait_for_timeout(2500)
        if page.query_selector(SELECTORS['contentEditor']):
            return
    except Exception:
        pass
    page.goto(WEIBO_URL, wait_until='domcontentloaded')
    page.wait_for_timeout(2500)
    try:
        el = page.wait_for_selector(SELECTORS['composeBtn'], timeout=5000)
        el.click()
        page.wait_for_timeout(1200)
        return
    except Exception:
        raise RuntimeError('无法打开微博发布器')


def _fill_editor(page, text):
    editor = page.wait_for_selector(SELECTORS['contentEditor'], timeout=8000)
    editor.click()
    page.wait_for_timeout(300)
    page.keyboard.insert_text(text)


def _publish_one(page, text, args, idx):
    """填一条微博并发布；返回是否成功点击发布。"""
    try:
        _open_compose(page)
        _fill_editor(page, text)
    except Exception:
        status_print('assisted', '打开发布器/定位编辑器失败，微博已留在浏览器中。')
        if not args.headless:
            hold_browser('请在浏览器中手动发布，完成后回车继续/关闭。')
        return False
    print(f'{timestr()} 第 {idx} 条已预填，正文 {len(text)} 字')
    if args.preview:
        return False
    try:
        page.wait_for_selector(SELECTORS['publishBtn'], timeout=8000)
        page.wait_for_timeout(300)
        page.click(SELECTORS['publishBtn'])
        page.wait_for_timeout(3000)
        return True
    except Exception:
        status_print('assisted', '发布按钮未找到，内容已预填，请手动发布。')
        if not args.headless:
            hold_browser('浏览器中内容已填好，请手动点击发布，完成后回车继续。')
        return False


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def publish_weibo(args):
    fnames = _collect_md(args.input, args.num)
    if not fnames:
        status_print('manual', f'请提供有效的 MD 文件或目录: {args.input}')
        return

    posts = []
    for f in fnames:
        md = read_file(f, 'utf-8')
        for text in _md_to_posts(md, args.max_chars, include_title=not args.no_title):
            posts.append((f, text))
    if not posts:
        status_print('manual', '没有可发布的正文内容。')
        return
    print(f'{timestr()} 共 {len(posts)} 条待发布微博（来源 {len(fnames)} 个 MD 文件）')

    cookies = get_cookies(args)

    with plrt_create_driver(headless=args.headless) as (browser, context, page):
        _inject_cookies(context, cookies)
        if not _ensure_login(page, args):
            return

        for idx, (f, text) in enumerate(posts, 1):
            print(f'\n{timestr()} [{idx}/{len(posts)}] {path.basename(f)}')
            ok = _publish_one(page, text, args, idx)
            if args.preview:
                status_print('assisted', f'已预填第 {idx} 条：{text[:40]}')
                if not args.headless:
                    hold_browser('（预览模式）已预填，审阅后回车继续下一条。')
                continue
            if not ok:
                return  # 已进入辅助发布流程，中断批量
            status_print('success', f'已发布第 {idx} 条微博: {path.basename(f)}')

        if args.preview:
            status_print('assisted', f'预览完成，共预填 {len(posts)} 条（未发布）。')
        else:
            status_print('success', f'全部发布完成，共 {len(posts)} 条。')


def add_arguments(parser):
    parser.add_argument("--input", help="MD 文件或目录路径")
    parser.add_argument("-c", "--cookie", default=None,
                        help="cookie 字符串 (name=v; ...)；默认从浏览器提取")
    parser.add_argument("-p", "--preview", action="store_true",
                        help="只预填内容、不点发布，留浏览器给人工审阅")
    parser.add_argument("-H", "--headless", action="store_true",
                        help="以无头模式运行 Chromium（默认可见浏览器）")
    parser.add_argument("--max-chars", type=int, default=2000,
                        help="每条微博最长字数，默认 2000，超长自动拆分")
    parser.add_argument("--no-title", action="store_true",
                        help="不在正文前拼接 MD 标题")
    parser.add_argument("-n", "--num", type=int, default=20,
                        help="一次最多处理 MD 文件数，默认 20")


def reg_subparser(subparsers):
    parser = subparsers.add_parser("weibo", help="发布微博（MD 文件或目录）")
    add_arguments(parser)
    parser.set_defaults(func=publish_weibo)


def main():
    import argparse
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog="weibo",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_arguments(parser)
    parser.set_defaults(func=publish_weibo)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
