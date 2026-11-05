# -*- coding: utf-8 -*-
"""发布类脚本的公共工具（自包含，vendored 自 BookerPubTool / BookerDownloadTool）

供 ``csdn.py`` / ``cnblogs.py`` / ``zhihu.py`` / ``weibo.py`` / ``toutiao.py`` 共用，
不依赖任何 Booker* 仓库或包：

  * ``extract_cookies_multi_browsers`` / ``extract_cookies`` —— 从本机浏览器提取 Cookie
  * ``cookie_dict_to_str`` / ``cookie_str_to_dict``           —— Cookie 字典 <-> 字符串
  * ``get_md_title``                                          —— 提取 Markdown 首个标题行
  * ``timestr`` / ``read_file`` / ``request_retry``           —— 通用小工具
  * ``status_print`` / ``hold_browser``                       —— 发布状态输出 / 浏览器交互
  * ``plrt_create_driver``                                    —— Playwright 驱动（含 stealth 注入）

依赖：``pip install browser_cookie3 requests``；微博发布额外需要 ``playwright``。
"""
import re
from contextlib import contextmanager
from datetime import datetime
from http.cookies import SimpleCookie
from os import path

import browser_cookie3 as bc
import requests

RE_TITLE = r'^#+\x20+(.+?)$'

# 本脚本目录（用于定位 stealth.min.js / patch_env_mock_wasm.js 等资源）
SCRIPTS_DIR = path.dirname(path.abspath(__file__))


def d(name):
    """返回脚本目录下的资源绝对路径。"""
    return path.join(SCRIPTS_DIR, name)


# ---------------------------------------------------------------------------
# Cookie <-> 字符串
# ---------------------------------------------------------------------------

def cookie_str_to_dict(cookie_str: str) -> dict:
    """将 Cookie 字符串解析为字典。

    自动兼容 '; ' (浏览器) 分隔符，并能正确还原被双引号包裹的特殊字符值。
    """
    cookie_str = (cookie_str or '').strip()
    if not cookie_str:
        return {}
    cookie = SimpleCookie(cookie_str)
    return {key: val.value for key, val in cookie.items()}


def cookie_dict_to_str(cookie_dict: dict) -> str:
    """将 Cookie 字典转为合法的 HTTP Cookie 头字符串。

    若值包含逗号、分号、空格等特殊字符，自动用双引号包裹。
    """
    if not cookie_dict:
        return ''
    cookie = SimpleCookie()
    for key, val in cookie_dict.items():
        cookie[key] = str(val)
    # attrs=[] 去掉多余属性, header='' 去掉 Set-Cookie 前缀
    return cookie.output(attrs=[], header='', sep='; ').strip()


# ---------------------------------------------------------------------------
# 本机浏览器 Cookie 提取
# ---------------------------------------------------------------------------

def extract_cookies(browser, domain):
    """从指定浏览器提取 domain 相关的 Cookie 字典。"""
    assert browser in [f.__name__ for f in bc.all_browsers]
    jar = getattr(bc, browser)()
    return {c.name: c.value for c in jar if domain in c.domain}


def extract_cookies_multi_browsers(domain, browsers=('firefox', 'chrome', 'edge')):
    """依次尝试多个浏览器，返回第一个成功提取到的 Cookie 字典。"""
    for br in browsers:
        try:
            ck = extract_cookies(br, domain)
            if ck:
                return ck
        except Exception:
            pass
    return {}


# ---------------------------------------------------------------------------
# Markdown 标题
# ---------------------------------------------------------------------------

def get_md_title(text):
    """返回 (标题, 标题所在的 span)；无标题时返回 (None, (None, None))。"""
    m = re.search(RE_TITLE, text, flags=re.M)
    if not m:
        return None, (None, None)
    return m.group(1).strip(), m.span(1)


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------

def timestr():
    now = datetime.now()
    return f'[{now.year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}]'


def read_file(name, enco=None):
    mode = 'r' if enco else 'rb'
    with open(name, mode, encoding=enco) as f:
        return f.read()


def request_retry(method, url, retry=10, check_status=False, **kw):
    kw.setdefault('timeout', 10)
    for i in range(retry):
        try:
            r = requests.request(method, url, **kw)
            if check_status:
                r.raise_for_status()
            return r
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f'{url} retry {i}')
            if i == retry - 1:
                raise e


# ---------------------------------------------------------------------------
# 发布状态输出 / 浏览器交互
# ---------------------------------------------------------------------------

def status_print(status, message, url=None):
    """Pretty-print a publish result line with a status icon."""
    icons = {
        'success': '✅', 'assisted': '🔵', 'manual': '📋',
        'skipped': '⏭️', 'error': '❌',
    }
    icon = icons.get(status, '❌')
    line = f'{icon} {message}'
    if url:
        line += f' → {url}'
    print(f'{timestr()} {line}')


def hold_browser(msg="浏览器已打开。请在页面中审阅/手动完成后，回到终端按回车关闭。"):
    """Keep the (visible) browser open until the user presses Enter. No-op in headless."""
    print(f'\n{timestr()} {msg}')
    try:
        input()
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# Playwright 驱动（含 stealth 注入）
# ---------------------------------------------------------------------------

def plrt_new_context(browser):
    context = browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    for fname in ('patch_env_mock_wasm.js', 'stealth.min.js'):
        fp = d(fname)
        if path.isfile(fp):
            context.add_init_script(fp)
    return context


def plrt_new_browser(plrt, headless=True):
    return plrt.chromium.launch(
        headless=headless,
        args=[
            # 禁用 AutomationControlled 自动化标记（Chrome94+ 核心参数）
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            # 模拟真人最大化打开浏览器
            "--start-maximized",
        ],
    )


@contextmanager
def plrt_create_driver(headless=True, timeout=30_000):
    """Yield a native Playwright page and its context."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = plrt_new_browser(p, headless)
        context = plrt_new_context(browser)
        page = context.new_page()
        page.set_default_timeout(timeout)
        page.set_default_navigation_timeout(timeout)
        try:
            yield browser, context, page
        finally:
            page.close()
            context.close()
            browser.close()
