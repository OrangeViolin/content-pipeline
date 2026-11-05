# -*- coding: utf-8 -*-
"""
知乎 x-zse-93 / x-zse-96 / x-zst-81 请求头签名计算（Python 版）。

算法来源：逆向知乎 heifetz 前端包 `3964.app.*.js`。
  - 模块 93823：header 名与版本常量（x-zse-93="101_3_3.0"、x-zse-96="2.0_"+sig）
  - 模块 88545：Web 端签名 source 拼接 + 调用 encryptor
  - 模块 10261：MD5
  - 模块 1514：真正的加密器 ZP（VM 混淆的块加密 + 自定义 base64）
  - 模块 62845：F="2.0"（x-zse-96 前缀）、Web="3_2.0"（x-zst-81 前缀）

模块 1514 是 JS 写的混淆 VM，难以 1:1 移植为纯 Python；
这里使用 quickjs（Python 绑定 QuickJS JS 引擎）直接执行模块 1514 的原始 JS 代码，
保证与浏览器端算法完全一致。source 拼接与 MD5 用纯 Python 实现。

详见 doc/zhihu_sign.md。
"""
import hashlib
import os
import json
from urllib.parse import quote, urlparse

try:
    import quickjs
except ImportError:
    quickjs = None

# ---------------------------------------------------------------------------
# 常量（来自模块 93823 / 62845 / 88545）
# ---------------------------------------------------------------------------
ZSE93 = "101_3_3.0"          # x-zse-93 值：appId(Zhihu=101) + "_" + 平台(3=Web) + "_" + 版本(3.0)
SIG_VERSION = "2.0"          # 模块 62845 的 F 常量，x-zse-96 前缀
ZST81_PREFIX = "3_2.0"       # 模块 62845 Web 平台版本常量，x-zst-81 前缀


# ---------------------------------------------------------------------------
# 加载模块 1514（在 quickjs 中运行），获得 ZP 加密函数
# ---------------------------------------------------------------------------
_JS_TEMPLATE = r"""
// ---- atob shim（模块 1514 case 331 用 base64 解码初始字节码）----
var atob = function(b64){
  var B='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var out='', i=0, len=b64.length, chr1,chr2,chr3,enc1,enc2,enc3,enc4;
  while(i<len){
    enc1=B.indexOf(b64.charAt(i++)); enc2=B.indexOf(b64.charAt(i++));
    enc3=B.indexOf(b64.charAt(i++)); enc4=B.indexOf(b64.charAt(i++));
    chr1=(enc1<<2)|(enc2>>4); chr2=((enc2&15)<<4)|(enc3>>2); chr3=((enc3&3)<<6)|enc4;
    out+=String.fromCharCode(chr1);
    if(enc3!=64) out+=String.fromCharCode(chr2);
    if(enc4!=64) out+=String.fromCharCode(chr3);
  }
  return out;
};
var window = {};
// ---- webpack 模块 shim ----
var __mod = {}; var __exp = {};
function __req(id){
  if(id===74185) return {_: function(x){ return typeof x; }};
  throw new Error('missing module '+id);
}
// ---- 知乎签名模块 1514（完整原代码，webpack 工厂函数）----
// 模块体形如 function(__unused_webpack_module, exports, __webpack_require__){ ... }
// 直接以 (__mod, __exp, __req) 调用它
// __MODULE_1514_BODY__

;(__MODULE_1514_BODY__)(__mod, __exp, __req);
;window.__ZP = __exp.ZP;
"""

_CTX = None


def _ensure_ctx():
    """初始化 quickjs 上下文并加载模块 1514。"""
    global _CTX
    if _CTX is not None:
        return _CTX
    if quickjs is None:
        raise RuntimeError("需要安装 quickjs 库：pip install quickjs")
    mod_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "module1514.js")
    if not os.path.exists(mod_file):
        raise FileNotFoundError("缺少 module1514.js（知乎加密模块原代码）")
    body = open(mod_file, encoding="utf-8").read().strip()
    # 去掉 webpack 模块头 "1514:function(...)"
    import re
    body = re.sub(r"^\d+:", "", body)
    if body.endswith(","):
        body = body[:-1]
    js = _JS_TEMPLATE.replace("__MODULE_1514_BODY__", body)
    ctx = quickjs.Context()
    ctx.eval(js)
    _CTX = ctx
    return ctx


def zhihu_encrypt(s):
    """对应模块 1514 导出的 ZP：ZP(e) = __g._encrypt(encodeURIComponent(e))。

    返回 base64 风格字符串（自定义字符集，含 '=' 作普通字符）。
    """
    ctx = _ensure_ctx()
    return ctx.eval("__exp.ZP(" + json.dumps(s) + ")")


def md5hex(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _uri_encode(s):
    """JS encodeURIComponent 近似（保留字母数字 -_.!~*'()）。"""
    return quote(s, safe="-_.!~*'()")


# ---------------------------------------------------------------------------
# 签名 source 构造（模块 88545 的 eA 函数）
# ---------------------------------------------------------------------------
def build_source(url, dc0, xzst81=None, body=None):
    """Web 端 source：eA = [zse93, path+search, dc0, body?, xZst81].filter(Boolean).join("+")。

    模块 88545:
        var eg = mR(url);        // new URL(url) 的 pathname + search
        var ey = Wn(body);       // body 序列化（string/URLSearchParams/JSON）
        var eA = [ef(zse93), eg, ed(dc0), kA(ey)&&ey, eh(xZst81)].filter(Boolean).join("+");
    """
    u = urlparse(url)
    path_search = (u.path if u.path else "") + (("?" + u.query) if u.query else "")
    parts = [ZSE93, path_search, dc0]
    if body is not None:
        if isinstance(body, (dict, list)):
            body = json.dumps(body, separators=(",", ":"))
        parts.append(body)
    if xzst81:
        parts.append(xzst81)
    return "+".join(p for p in parts if p)


def compute_signature(url, dc0, xzst81=None, body=None):
    """签名 = ZP(md5(source))。返回 (source, md5hex, sig)。"""
    source = build_source(url, dc0, xzst81, body)
    md5_hex = md5hex(source)
    sig = zhihu_encrypt(md5_hex)      # ZP 内部会做 encodeURIComponent
    return source, md5_hex, sig


def make_headers(url, dc0, xzst81=None, body=None):
    """返回 {x-zse-93, x-zse-96, (x-zst-81)} 请求头。"""
    _, _, sig = compute_signature(url, dc0, xzst81, body)
    headers = {
        "x-zse-93": ZSE93,
        "x-zse-96": SIG_VERSION + "_" + sig,
    }
    if xzst81:
        headers["x-zst-81"] = xzst81
    return headers


def get_dc0_from_cookie(cookie_header):
    """从 Cookie 头中提取 d_c0 值。"""
    import re
    m = re.search(r"d_c0=([^;]+)", cookie_header or "")
    return m.group(1) if m else None


if __name__ == "__main__":
    # 示例：计算目标接口的请求头
    url = "https://www.zhihu.com/api/v5.1/topics/19588503/feeds/timeline_activity/v2?desktop=true&page=1&limit=7"
    dc0 = "23GUX1lpmhuPTnyZMrbH5UfZHvz-TQoLs7I=|1766998849"
    h = make_headers(url, dc0)
    print(h)
