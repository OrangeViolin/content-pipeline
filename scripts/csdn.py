# -*- coding: utf-8 -*-
"""CSDN 博客发布（requests 版）

直接调用 CSDN 官网编辑器同款 API（签名算法逆向自 editor.csdn.net/md/ 前端 bundle），
无需启动浏览器。Cookie 通过 browser_cookie3 从本机浏览器（Firefox/Chrome/Edge）提取。

接口: POST https://bizapi.csdn.net/blog-console-api/v3/mdeditor/saveArticle
签名: Base64(HMAC-SHA256(StringToSign, appSecret))
      StringToSign = METHOD\\n Accept\\n [Content-MD5 恒空]\\n Content-Type\\n Date[恒空]\\n
                     排序后的 x-ca-key/x-ca-nonce...\\n 去掉 csdn.net 域名后的 URL

自包含：仅依赖同目录的 ``pub_util.py``（cookie 提取 / Markdown 标题），
以及第三方库 ``requests`` / ``browser_cookie3`` / ``markdown``（可选）。

用法:
    python scripts/csdn.py 文章.md
    python scripts/csdn.py 文章目录 -ct 默认分类 -tg a,b --draft
    python scripts/csdn.py --del-id 123456
"""
import re
import os
import sys
import time
import uuid
import json
import hmac
import hashlib
import base64
import logging
import argparse
from os import path

import requests
import traceback

# 同目录自包含工具（vendored，不依赖 BookerPubTool 包）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pub_util import cookie_str_to_dict, extract_cookies_multi_browsers, get_md_title

log = logging.getLogger('csdn_post')

# 由 editor.csdn.net/md/ 前端 reverse-engineered
CA_KEY = '203803574'
CA_SECRET = '9znpamsyl2c7cdrr9sas0le9vbc3r6ba'
CSDN_NET_RE = re.compile(r'^(?=^.{3,255}$)(http(s)?://)?(www\.)?[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.csdn\.net)')
API_BASE = 'https://bizapi.csdn.net'
SAVE_ARTICLE_URL = API_BASE + '/blog-console-api/v3/mdeditor/saveArticle'
GET_BASE_INFO_URL = API_BASE + '/blog-console-api/v3/editor/getBaseInfo'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def gen_nonce():
    """等价前端 b(): UUID v4"""
    return str(uuid.uuid4())


def pick_sign_headers(headers):
    """等价前端 v(): 只挑出 x-ca-key/x-ca-nonce/x-ca-signature/x-ca-signature-headers"""
    keep = {
        'x-ca-key', 'x-ca-nonce',
        'x-ca-signature', 'x-ca-signature-headers',
    }
    return {
        k.lower(): v
        for k, v in headers.items()
        if k.lower().startswith('x-ca-') and k.lower() in keep
    }


def build_url_with_query(url, params):
    """等价前端 URL 尾段: 去掉 csdn.net 域名前缀 + 追加排序后的 query"""
    url_path = CSDN_NET_RE.sub('', url)
    if params:
        items = []
        for k in sorted(params):
            v = params[k]
            items.append('%s=%s' % (k, v) if v not in (None, '') else k)
        if items:
            url_path += '?' + '&'.join(items)
    return url_path


def gen_sign(method, url, params, accept, content_type, date, headers):
    """等价前端 w(): 构造 StringToSign 并返回 base64(HMAC-SHA256)"""
    parts = [method, accept, '', content_type, date]
    picked = pick_sign_headers(headers)
    for k in sorted(picked):
        parts.append('%s:%s' % (k, picked[k]))
    parts.append(build_url_with_query(url, params))
    string_to_sign = '\n'.join(parts)
    digest = hmac.new(
        CA_SECRET.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode('utf-8'), string_to_sign


def build_auth_headers(method, url, params=None, content_type=''):
    """等价前端 y(): 构造带签名的请求头"""
    params = params or {}
    headers = {'Accept': '*/*'}
    if content_type:
        headers['Content-Type'] = content_type
    headers['X-Ca-Key'] = CA_KEY
    nonce = gen_nonce()
    headers['X-Ca-Nonce'] = nonce
    sig, _ = gen_sign(method, url, params, headers['Accept'], content_type, '', headers)
    headers['X-Ca-Signature'] = sig
    headers['X-Ca-Signature-Headers'] = 'x-ca-key,x-ca-nonce'
    return headers


def csdn_request(method, url, params=None, body=None, cookies=None, retry=5):
    """带签名的 CSDN API 请求；cookies 为 {name: value} 字典"""
    content_type = 'application/json' if body is not None else ''
    headers = build_auth_headers(method, url, params, content_type)
    headers['User-Agent'] = UA
    headers['Referer'] = 'https://editor.csdn.net/md/'
    headers['Origin'] = 'https://editor.csdn.net'

    # 所有 cookie 均来自 .csdn.net 域，直接以 Cookie 头发送
    if isinstance(cookies, dict) and cookies:
        headers['Cookie'] = '; '.join('%s=%s' % (k, v) for k, v in cookies.items())

    last_ex = None
    for i in range(retry):
        try:
            resp = requests.request(
                method, url, params=params, json=body, headers=headers, timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()
            log.warning('HTTP %s: %s', resp.status_code, resp.text[:300])
        except Exception as ex:
            last_ex = ex
            log.warning('request failed: %s', ex)
        time.sleep(2)
    raise SystemError('CSDN API 请求失败: %s' % last_ex or 'HTTP 非 200')


def get_base_info(cookies):
    """获取用户信息与可用分类，返回 data dict"""
    return csdn_request('GET', GET_BASE_INFO_URL, cookies=cookies)


def del_article(cookies, article_id, retry=5):
    """删除文章/草稿；POST /blog/phoenix/console/v1/article/del"""
    url = API_BASE + '/blog/phoenix/console/v1/article/del'
    return csdn_request(
        'POST', url, body={'articleId': article_id}, cookies=cookies, retry=retry,
    )


def save_article(cookies, title, md, cate='默认分类', tags=None,
                 publish=True, article_id='', retry=20):
    """发布/保存文章；返回 (code, data/msg)"""
    tags = tags or ['默认标签']
    if isinstance(tags, (list, tuple)):
        tags = ','.join(tags)
    # content 为 markdown 渲染的 HTML（service 需 content 非空）
    try:
        import markdown as md_lib
        html = md_lib.markdown(md, extensions=['extra'])
    except Exception:
        html = '<p>' + md.replace('\n', '<br>\n') + '</p>'

    body = {
        'id': article_id,
        'title': title,
        'markdowncontent': md,
        'content': html,
        'readType': 'public',
        'level': 0,
        'tags': tags,
        'status': 0 if publish else 2,
        'categories': cate,
        'type': 'original',
        'original_link': '',
        'authorized_status': False,
        'Description': '',
        'resource_url': '',
        'not_auto_saved': '1',
        'source': 'pc_mdeditor',
        'cover_images': [],
        'cover_type': 0,
        'is_new': 1,
        'vote_id': 0,
        'resource_id': '',
        'pubStatus': 'publish' if publish else 'draft',
        'creator_activity_id': '',
        'creation_statement': 0,
    }
    return csdn_request(
        'POST', SAVE_ARTICLE_URL, body=body, cookies=cookies, retry=retry,
    )


def publish_csdn(args):
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(message)s')

    # cookie 来源: 显式指定 > 本地 JSON > browser_cookie3
    cookies = {}
    if args.cookie:
        if path.isfile(args.cookie):
            cookies = json.loads(open(args.cookie, encoding='utf8').read())
        else:
            cookies = cookie_str_to_dict(args.cookie)
    else:
        cookies = extract_cookies_multi_browsers('csdn.net')
        print('从浏览器提取到 %d 个 csdn.net cookie' % len(cookies))
    if not cookies:
        raise SystemError('未获取到 CSDN cookie，请先在浏览器登录 CSDN')

    # 删除模式
    if args.del_id:
        resp = del_article(cookies, args.del_id)
        print('删除结果:', json.dumps(resp, ensure_ascii=False))
        return

    # 校验登录态
    info = get_base_info(cookies)
    if info.get('code') != 200:
        raise SystemError('登录校验失败: %s' % json.dumps(info, ensure_ascii=False))
    print('登录用户:', info['data'].get('muser_name'), info['data'].get('nickname'))
    categorys = info['data'].get('categorys', [])
    if args.cate not in categorys:
        print('警告: 分类 "%s" 不在已有分类列表中，将新建' % args.cate)

    if path.isfile(args.fname):
        fnames = [args.fname]
    else:
        fnames = [path.join(args.fname, f) for f in os.listdir(args.fname)]
    fnames = [f for f in fnames if f.endswith('.md')]
    if not fnames:
        print('请提供 MD 文件或目录')
        return

    for f in fnames:
        try:
            post_one(f, info, cookies, args)
        except KeyboardInterrupt:
            raise
        except Exception:
            traceback.print_exc()


def post_one(f, info, cookies, args):
    print(f)
    md = open(f, encoding='utf8').read()
    # 图片标记转为 URL（与旧版行为一致）
    md = re.sub(r'!\[[^\]]*\]\(([^\)]+)\)', r'<\1>', md)
    title, pos = get_md_title(md)
    if not title:
        print('%s MD 文件无标题' % f)
        return
    if len(title) < 5:
        title *= 5
    body = md[pos[1]:]

    action = '存草稿' if args.draft else '发布'
    print('%s: %s' % (action, title))
    resp = save_article(
        cookies, title, body,
        cate=args.cate, tags=args.tags.split(','),
        publish=not args.draft, retry=args.retry,
    )
    code = resp.get('code')
    if code != 200:
        print('失败:', json.dumps(resp, ensure_ascii=False))
        return
    data = resp.get('data', {})
    aid = data.get('id') or data.get('articleId') or ''
    url = 'https://blog.csdn.net/%s/article/details/%s' % (info['data'].get('muser_name'), aid)
    print('成功:', code, '文章ID:', aid, url)
    if not args.draft:
        os.remove(f)


def add_arguments(parser):
    parser.add_argument('fname', help='MD 文件或目录')
    parser.add_argument('-c', '--cookie', default='', help='cookie 字符串 (name=v; ...) 或 {name:value} JSON 文件；默认 browser_cookie3 提取')
    parser.add_argument('-ct', '--cate', default='默认分类', help='分类 (默认: 默认分类)')
    parser.add_argument('-tg', '--tags', default='默认标签', help='标签，逗号分隔')
    parser.add_argument('-d', '--draft', action='store_true', help='存草稿而不发布')
    parser.add_argument('-r', '--retry', type=int, default=20, help='重试次数 (默认 20)')
    parser.add_argument('-V', '--verbose', action='store_true', help='打印签名细节')
    parser.add_argument('-del', '--del-id', dest='del_id', default='',
                        help='删除文章/草稿（传文章ID，不发布）')


def reg_subparser(subparsers):
    parser = subparsers.add_parser("csdn", help="CSDN 文章发布")
    add_arguments(parser)
    parser.set_defaults(func=publish_csdn)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog="csdn",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_arguments(parser)
    parser.set_defaults(func=publish_csdn)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
