#!/usr/bin/env python3
"""
微信公众号文章抓取脚本
通过模拟微信客户端 User-Agent 绕过反爬机制

用法：
    python fetch_wechat_article.py <公众号文章链接> [--download-images]
    python fetch_wechat_article.py <链接1> <链接2> ...  # 批量处理

示例：
    python fetch_wechat_article.py "https://mp.weixin.qq.com/s/xxx"
    python fetch_wechat_article.py "https://mp.weixin.qq.com/s/xxx" --download-images
"""

import sys
import re
import html
import subprocess
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime


# 微信客户端 User-Agent
WECHAT_UA = "Mozilla/5.0 (Linux; Android 13; V2148A) AppleWebKit/537.36 Chrome/116.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.49.2600 WeChat/arm64 Weixin NetType/WIFI Language/zh_CN"


def fetch_wechat_article(url: str) -> dict:
    """抓取微信公众号文章内容"""

    # 使用 curl 发送请求（更稳定）
    result_proc = subprocess.run(
        ["curl", "-s", "-L", "-A", WECHAT_UA, url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    content = result_proc.stdout

    result = {
        "url": url,
        "title": "",
        "author": "",
        "description": "",
        "content": "",
        "images": [],
        "is_video": False,
        "raw_html_length": len(content),
    }

    # 提取标题 - 多种格式兼容
    title_match = re.search(r"msg_title\s*=\s*['\"](.+?)['\"]\.html\(false\)", content)
    if not title_match:
        title_match = re.search(r"msg_title = window\.title = ['\"]([^'\"]+)['\"]", content)
    if not title_match:
        title_match = re.search(r'property="og:title" content="([^"]+)"', content)
    if title_match:
        result["title"] = html.unescape(title_match.group(1).replace("&amp;", "&"))

    # 提取描述
    desc_match = re.search(r'name="description" content="([^"]+)"', content)
    if desc_match:
        desc = desc_match.group(1)
        # 处理转义字符
        desc = desc.replace("\\x0a", "\n").replace("\\x26", "&").replace("&amp;", "&")
        result["description"] = html.unescape(desc)

    # 判断是否为视频号文章（检查实际的 h1 标签，而不是 JS 代码）
    if re.search(r'<h1[^>]*id="js_video_page_title"', content):
        result["is_video"] = True
        result["content"] = result["description"]
    else:
        # 普通图文文章：从 js_content 提取完整正文
        # 匹配 js_content div 开始到文章结束（贪婪匹配到最后一个闭合）
        content_match = re.search(r'id="js_content"[^>]*>(.*?)(?:</div>\s*<!--\s*js_content|<script\b)', content, re.DOTALL)
        if not content_match:
            # 备用方案：更宽松地匹配 js_content 后面的所有内容直到明显边界
            content_match = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*</div>\s*</div>', content, re.DOTALL)
        if content_match:
            inner = content_match.group(1)
            # 去除 HTML 标签，保留文本
            clean = re.sub(r'<[^>]+>', '\n', inner)
            clean = html.unescape(clean)
            # 清理多余空白
            lines = [line.strip() for line in clean.split('\n') if line.strip()]
            result["content"] = '\n'.join(lines)
        else:
            result["content"] = result["description"]

    # 提取公众号名称 - JsDecode 格式优先（真实公众号名）
    author_match = re.search(r"nick_name: JsDecode\(['\"]([^'\"]+)['\"]\)", content)
    if not author_match:
        author_match = re.search(r'class="account_nickname_inner">([^<]+)<', content)
    if not author_match:
        # 最后备选：直接引号格式（可能匹配到广告名，优先级最低）
        author_match = re.search(r"nick_name\s*[:=]\s*['\"]([^'\"]+)['\"]", content)
    if author_match:
        result["author"] = author_match.group(1).strip()

    # 提取图片链接（data-src 和 src 两种方式）
    images = set()
    for pattern in [r'data-src="(https://mmbiz\.qpic\.cn[^"]+)"', r'src="(https://mmbiz\.qpic\.cn[^"]+)"']:
        for match in re.finditer(pattern, content):
            img_url = match.group(1).replace("&amp;", "&")
            images.add(img_url)
    result["images"] = sorted(list(images))

    return result


def download_images(images: list, output_dir: str = None) -> list:
    """下载图片到指定目录，返回本地文件路径列表"""
    if not images:
        return []

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="wechat_article_")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    downloaded = []
    for i, img_url in enumerate(images, 1):
        # 确定文件扩展名
        if "wx_fmt=gif" in img_url:
            ext = "gif"
        elif "wx_fmt=png" in img_url:
            ext = "png"
        else:
            ext = "jpg"

        filename = f"img_{i:02d}.{ext}"
        filepath = os.path.join(output_dir, filename)

        # 使用 curl 下载
        result = subprocess.run(
            ["curl", "-s", "-o", filepath, img_url],
            capture_output=True,
            timeout=30,
        )

        if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            downloaded.append(filepath)
        # 进度消息在调用处根据需要打印

    return downloaded


def fetch_multiple_articles(urls: list) -> list:
    """批量抓取多篇文章"""
    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n📄 正在抓取第 {i}/{len(urls)} 篇...")
        try:
            article = fetch_wechat_article(url)
            results.append(article)
            print(f"   ✅ {article['title'][:30]}...")
        except Exception as e:
            print(f"   ❌ 抓取失败: {e}")
            results.append({"url": url, "error": str(e)})
    return results


def output_json(article: dict):
    """输出 JSON 格式（供其他程序调用）"""
    print(json.dumps(article, ensure_ascii=False, indent=2))


def output_summary(article: dict, image_paths: list = None):
    """输出结构化总结"""
    print("=" * 50)
    print(f"【标题】{article['title']}")
    print(f"【作者】{article['author']}")
    print(f"【类型】{'视频号文章' if article['is_video'] else '图文文章'}")
    print(f"【配图数量】{len(article['images'])} 张")
    print("=" * 50)
    print("【正文】")
    print(article["content"])
    print("=" * 50)

    if article["images"]:
        print("【配图链接】")
        for i, img in enumerate(article["images"][:10], 1):
            print(f"  {i}. {img[:80]}...")
        if len(article["images"]) > 10:
            print(f"  ... 共 {len(article['images'])} 张")

    if image_paths:
        print("=" * 50)
        print("【已下载图片】")
        for path in image_paths:
            print(f"  📷 {path}")

    print("=" * 50)


def output_markdown(article: dict, image_paths: list = None):
    """输出 Markdown 格式，适合存档和进一步处理"""
    article_type = "视频号文章" if article["is_video"] else "图文文章"

    md = f"""# {article['title']}

## 基本信息

| 项目 | 内容 |
|------|------|
| **作者** | {article['author']} |
| **类型** | {article_type} |
| **配图** | {len(article['images'])} 张 |
| **来源** | [原文链接]({article['url']}) |

---

## 正文

{article['content']}

---

## 配图

"""
    if image_paths:
        for i, path in enumerate(image_paths, 1):
            md += f"- 图{i}: `{path}`\n"
    elif article["images"]:
        for i, img in enumerate(article["images"], 1):
            md += f"- 图{i}: {img}\n"
    else:
        md += "*无配图*\n"

    md += """
---

## 待总结（由 cc 填写）

### 核心观点
1.
2.
3.

### 关键信息
-
-

### 金句摘录
> ""
> ""

### 思考/迭代点
- 对我有什么启发？
- 有什么可以借鉴的？

---

*抓取时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M") + "*\n"

    print(md)


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python fetch_wechat_article.py <公众号文章链接>")
        print("  python fetch_wechat_article.py <链接> --download-images")
        print("  python fetch_wechat_article.py <链接> --json")
        print("  python fetch_wechat_article.py <链接> --markdown")
        print("  python fetch_wechat_article.py <链接1> <链接2> ...  # 批量处理")
        sys.exit(1)

    # 解析参数
    args = sys.argv[1:]
    download_flag = "--download-images" in args
    json_flag = "--json" in args
    markdown_flag = "--markdown" in args

    urls = [arg for arg in args if arg.startswith("http")]

    try:
        if len(urls) == 1:
            # 单篇文章
            article = fetch_wechat_article(urls[0])

            image_paths = None
            if download_flag:
                if not json_flag:
                    print("📥 正在下载配图...")
                image_paths = download_images(article["images"])
                if not json_flag:
                    for path in image_paths:
                        print(f"  ✅ 下载成功: {os.path.basename(path)}")
                article["downloaded_images"] = image_paths

            if json_flag:
                output_json(article)
            elif markdown_flag:
                output_markdown(article, image_paths)
            else:
                output_summary(article, image_paths)

        elif len(urls) > 1:
            # 批量处理
            articles = fetch_multiple_articles(urls)

            if json_flag:
                print(json.dumps(articles, ensure_ascii=False, indent=2))
            else:
                print("\n" + "=" * 50)
                print(f"📚 批量抓取完成，共 {len(articles)} 篇")
                print("=" * 50)
                for i, article in enumerate(articles, 1):
                    if "error" in article:
                        print(f"\n❌ 文章 {i}: 抓取失败 - {article['error']}")
                    else:
                        print(f"\n📄 文章 {i}: {article['title']}")
                        print(f"   作者: {article['author']}")
                        print(f"   配图: {len(article['images'])} 张")
        else:
            print("错误：请提供至少一个公众号文章链接")
            sys.exit(1)

    except Exception as e:
        print(f"抓取失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
