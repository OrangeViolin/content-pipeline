# -*- coding: utf-8 -*-
"""头条号文章发布（requests 版，结构参照 csdn.py）

接口通过浏览器访问
https://mp.toutiao.com/profile_v4/graphic/publish?from=toutiao_pc&is_new_connect=0&is_new_user=0
抓包 + 前端 bundle 逆向提取：
  * 登录态: 浏览器 cookie 中的 .toutiao.com 会话（browser_cookie3 直读）
  * 发布/存草稿:
      POST https://mp.toutiao.com/mp/agw/article/publish?source=mp&type=article&aid=1231&mp_publish_ab_val=0
      body 为表单: title / content(Html) / save(0=发布,1=草稿) / extra / ...
  * 传图:
      POST /mp/agw/article_material/photo/upload_picture?type=ueditor&pgc_watermark=0&action=uploadimage&encode=utf-8&is_private=0
      multipart 字段 upfile，返回 {code:0, url}
  * 删草稿: POST /mp/agw/creator_center/delete_draft  {"gid": <pgc_id>}

自包含：仅依赖同目录的 ``pub_util.py``，以及第三方库
``requests`` / ``browser_cookie3`` / ``pyquery`` / ``markdown`` / ``pillow``（可选）。

用法:
    python scripts/toutiao.py 文章.md
    python scripts/toutiao.py 文章目录 --draft
    python scripts/toutiao.py --del-id <pgc_id>
"""
import re
import os
import sys
import io
import time
import json
import base64
import traceback
from os import path

import requests
from pyquery import PyQuery as pq

# 同目录自包含工具（vendored，不依赖 BookerPubTool 包）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pub_util import (
    get_md_title, cookie_str_to_dict, cookie_dict_to_str,
    extract_cookies_multi_browsers, request_retry,
)

PUBLISH_URL = ('https://mp.toutiao.com/mp/agw/article/publish'
               '?source=mp&type=article&aid=1231&mp_publish_ab_val=0')
UPLOAD_URL = ('https://mp.toutiao.com/mp/agw/article_material/photo/upload_picture'
              '?type=ueditor&pgc_watermark=0&action=uploadimage&encode=utf-8&is_private=0')
DELETE_DRAFT_URL = 'https://mp.toutiao.com/mp/agw/creator_center/delete_draft'
LOGIN_CHECK_URL = 'https://mp.toutiao.com/mp/agw/media/user_login_status_api'

EDITOR_REF = ('https://mp.toutiao.com/profile_v4/graphic/publish'
              '?from=toutiao_pc&is_new_connect=0&is_new_user=0')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')


# ---------------------------------------------------------------------------
# 会话 / 登录态
# ---------------------------------------------------------------------------

def get_cookies(args):
    """Cookie 来源：显式指定 > 浏览器提取。"""
    if args.cookie:
        return cookie_str_to_dict(args.cookie)
    cookies = extract_cookies_multi_browsers('toutiao.com')
    print('从浏览器提取到 %d 个 toutiao.com cookie' % len(cookies))
    return cookies


def make_session(args):
    cookies = get_cookies(args)
    if not cookies:
        raise SystemExit('未获取到头条 cookie，请先在浏览器登录头条号')
    sess = requests.Session()
    sess.headers.update({
        'User-Agent': UA,
        'Cookie': cookie_dict_to_str(cookies),
        'Referer': EDITOR_REF,
        'Origin': 'https://mp.toutiao.com',
        'Accept': 'application/json, text/plain, */*',
    })
    try:
        r = sess.get(LOGIN_CHECK_URL, timeout=30)
        data = r.json().get('data', {})
        if not data.get('is_login'):
            raise SystemExit('头条登录态失效，请重新登录头条号')
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
    return sess


# ---------------------------------------------------------------------------
# 图片上传
# ---------------------------------------------------------------------------

def img_to_png(data):
    """尽量转成 PNG（头条传图对格式敏感），失败时原样返回。"""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        buf = io.BytesIO()
        im.convert('RGB').save(buf, 'PNG')
        return buf.getvalue()
    except Exception:
        return data


def upload_image(sess, data, retry=5):
    """上传一张图片，返回 (url, 响应 json)。失败返回 (None, res)。"""
    png = img_to_png(data)
    last = None
    for i in range(retry):
        try:
            r = sess.post(UPLOAD_URL,
                          files={'upfile': ('pic.png', png, 'image/png')},
                          timeout=60)
            res = r.json()
        except Exception as ex:
            last = ex
            print(f'上传失败 retry {i}: {ex}')
            time.sleep(2)
            continue
        url = res.get('url') or res.get('web_url')
        if res.get('code') == 0 and url:
            return url, res
        last = res
        print(f'上传失败 retry {i}: {res.get("message") or res}')
        time.sleep(2 + i * 2)
    return None, last


# ---------------------------------------------------------------------------
# Markdown -> 待发布 HTML
# ---------------------------------------------------------------------------

def md_to_html(md):
    import markdown
    return markdown.markdown(md, extensions=['extra', 'sane_lists'])


def procure_images(sess, html, md_dir, retry=5):
    """把 html 里的图片上传到头条，返回替换后的 html。

    本地相对路径相对 md 所在目录解析；上传失败的图片保持原样（打打警告）。
    """
    root = pq('<div>' + html + '</div>')
    el_imgs = root('img')
    for i in range(len(el_imgs)):
        el = el_imgs.eq(i)
        src = el.attr('src') or ''
        if not src:
            continue
        data = None
        m = re.match(r'data:(image/\w+);base64,([\s\S]*)', src)
        if m:
            try:
                data = base64.b64decode(re.sub(r'\s', '', m.group(2)))
            except Exception:
                data = None
        elif src.startswith('http'):
            try:
                data = request_retry('GET', src, retry=3, timeout=20).content
            except Exception:
                print(f'图片下载失败: {src}')
                continue
        else:
            fp = src.split('?')[0].split('#')[0]
            fp = fp if path.isabs(fp) else path.join(md_dir, fp)
            if not path.isfile(fp):
                print(f'图片文件不存在: {fp}')
                continue
            data = open(fp, 'rb').read()

        if data is None:
            continue
        url, res = upload_image(sess, data, retry=retry)
        if url:
            el.attr('src', url)
        else:
            print(f'图片上传失败，保留原链接: {src[:120]}')
    return root('div').html()


# ---------------------------------------------------------------------------
# 发布 / 删除
# ---------------------------------------------------------------------------

def gen_title_id():
    return '%d_%d' % (int(time.time() * 1000),
                      int.from_bytes(os.urandom(8), 'big') % 10 ** 16)


def publish_article(sess, title, content, save=False, cover_type=2, retry=5):
    """发布文章或存草稿，返回 (code, data)。"""
    word_cnt = len(re.sub(r'<[^>]+>', '', content))
    title_id = gen_title_id()
    extra = {
        'content_source': 100000000402,
        'content_word_cnt': word_cnt,
        'is_multi_title': 0,
        'sub_titles': [],
        'gd_ext': {
            'entrance': '',
            'from_page': 'publisher_mp',
            'enter_from': 'PC',
            'device_platform': 'mp',
            'is_message': 0,
        },
        'tuwen_wtt_transfer_switch': '1',
    }
    body = {
        'source': '29',
        'extra': json.dumps(extra, ensure_ascii=False, separators=(',', ':')),
        'content': content,
        'title': title,
        'search_creation_info': json.dumps(
            {'searchTopOne': 0, 'abstract': '', 'clue_id': ''},
            separators=(',', ':')),
        'title_id': title_id,
        'mp_editor_stat': '{}',
        'is_refute_rumor': '0',
        'save': '1' if save else '0',
        'entrance': '',
        'timer_status': '0',
        'timer_time': '',
        'educluecard': '',
        'draft_form_data': json.dumps({'coverType': cover_type},
                                      separators=(',', ':')),
        'pgc_feed_covers': '[]',
        'article_ad_type': '3',
        'is_fans_article': '0',
        'govern_forward': '0',
        'praise': '0',
        'disable_praise': '0',
        'tree_plan_article': '0',
        'star_order_id': '',
        'star_order_name': '',
        'customer_nick_name': '',
        'activity_tag': '0',
        'trends_writing_tag': '0',
        'claim_exclusive': '0',
    }
    sess.headers['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
    last = None
    for i in range(retry):
        try:
            r = sess.post(PUBLISH_URL, data=body, timeout=60)
            res = r.json()
            if res.get('code') == 0:
                return res.get('code'), res.get('data', {})
            last = res
            print(f'发布失败 retry {i}: {res.get("reason") or res.get("message") or res}')
        except Exception as ex:
            last = ex
            print(f'发布异常 retry {i}: {ex}')
        time.sleep(2 + i * 2)
    raise SystemError(f'发布失败: {last}')


def delete_draft(sess, gid):
    r = sess.post(DELETE_DRAFT_URL, json={'gid': gid}, timeout=30)
    return r.json()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def publish_toutiao(args):
    sess = make_session(args)

    if args.del_id:
        print('删除草稿:', json.dumps(
            delete_draft(sess, args.del_id), ensure_ascii=False))
        return

    if path.isfile(args.fname):
        fnames = [args.fname]
    else:
        fnames = [path.join(args.fname, f) for f in os.listdir(args.fname)]
    fnames = [f for f in fnames if f.endswith('.md')]
    if not fnames:
        print('请提供 MD 文件或目录')
        return

    for f in fnames[:args.num]:
        try:
            post_one(sess, f, args)
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception:
            traceback.print_exc()


def post_one(sess, f, args):
    print(f)
    md = open(f, encoding='utf8').read()
    title, pos = get_md_title(md)
    if not title:
        print('%s MD 文件无标题' % f)
        return
    if len(title) < 5:
        title *= 5
    body = md[pos[1]:]
    html = md_to_html(body)
    print('上传正文图片...')
    html = procure_images(sess, html, path.dirname(path.abspath(f)),
                          retry=args.retry)

    action = '存草稿' if args.draft else '发布'
    print(f'{action}: {title}')
    code, data = publish_article(
        sess, title[:100], html, save=args.draft, retry=args.retry)
    pgc_id = data.get('pgc_id') or ''
    url = 'https://mp.toutiao.com/preview_article/?pgc_id=' + pgc_id if pgc_id else ''
    print('成功:', code, 'pgc_id:', pgc_id, url)
    if not args.draft:
        os.remove(f)


def add_arguments(parser):
    parser.add_argument("fname", help="MD 文件或目录")
    parser.add_argument(
        "-c", "--cookie", default='',
        help="cookie 字符串 (name=v; ...)；默认从 Firefox/Chrome/Edge 提取")
    parser.add_argument(
        "-d", "--draft", action='store_true', help="存草稿而不发布")
    parser.add_argument(
        "-r", "--retry", type=int, default=5, help="上传/发布重试次数 (默认 5)")
    parser.add_argument(
        "-n", "--num", type=int, default=20, help="一次连续发布文章数")
    parser.add_argument(
        "-del", "--del-id", dest="del_id", default='',
        help="删除草稿（传 gid/pgc_id，不发布）")


def reg_subparser(subparsers):
    parser = subparsers.add_parser("toutiao", help="头条号文章发布")
    add_arguments(parser)
    parser.set_defaults(func=publish_toutiao)


def main():
    import argparse
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog="toutiao",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_arguments(parser)
    parser.set_defaults(func=publish_toutiao)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
