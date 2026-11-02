# -*- coding: utf-8 -*-
"""发布类脚本的公共工具（自包含，vendored 自 BookerPubTool / BookerDownloadTool）

供 ``csdn.py`` / ``cnblogs.py`` / ``zhihu.py`` 共用，不依赖任何 Booker* 仓库或包：

  * ``extract_cookies_multi_browsers`` / ``extract_cookies`` —— 从本机浏览器提取 Cookie
  * ``cookie_dict_to_str`` / ``cookie_str_to_dict``           —— Cookie 字典 <-> 字符串
  * ``get_md_title``                                          —— 提取 Markdown 首个标题行

依赖：``pip install browser_cookie3``
"""
import re
from http.cookies import SimpleCookie

import browser_cookie3 as bc

RE_TITLE = r'^#+\x20+(.+?)$'


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
