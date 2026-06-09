"""
Fetch ani.gamer.com.tw page source via FlareSolverr (bypasses CF challenge).
Results are logged to README.md in this directory.

Requires FlareSolverr running on localhost:8191.
"""

import json
import os
import sys
import requests
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, 'README.md')
SOURCE_DIR = os.path.join(SCRIPT_DIR, 'source')

FLARESOLVERR_URL = os.environ.get('FLARESOLVERR_URL', 'http://localhost:8191/v1')
TARGET_URL = 'https://ani.gamer.com.tw/'

today = datetime.now().strftime('%Y-%m-%d')
now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def fetch_via_flaresolverr():
    """Send request to FlareSolverr and get solved page."""
    print(f"[1/2] Sending request to FlareSolverr: {TARGET_URL}")
    payload = {
        "cmd": "request.get",
        "url": TARGET_URL,
        "maxTimeout": 60000,
    }

    try:
        resp = requests.post(FLARESOLVERR_URL, json=payload, timeout=90)
        data = resp.json()
    except Exception as e:
        return None, f"FlareSolverr error: {e}", None

    if data.get('status') != 'ok':
        return None, f"FlareSolverr status: {data.get('status')} - {data.get('message', '')}", None

    solution = data.get('solution', {})
    status = solution.get('status', 'unknown')
    html = solution.get('response', '')
    cookies = solution.get('cookies', [])
    user_agent = solution.get('userAgent', '')

    return html, status, {'cookies': cookies, 'user_agent': user_agent}


def main():
    os.makedirs(SOURCE_DIR, exist_ok=True)

    html, status, meta = fetch_via_flaresolverr()

    if html is None:
        print(f"FAIL: {status}")
        html = ""
        html_len = 0
        title = ""
        cf_blocked = True
    else:
        html_len = len(html)
        # Extract title from HTML
        import re
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        cf_blocked = "challenge" in html[:3000].lower() or "just a moment" in title.lower()

    print(f"[2/2] Result: status={status}, html={html_len:,} bytes, title={title[:60]}, cf_blocked={cf_blocked}")

    # Save source
    source_file = os.path.join(SOURCE_DIR, f"{today}.html")
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Source saved to {source_file}")

    # Save cookies if available
    if meta and meta.get('cookies'):
        cookie_file = os.path.join(SOURCE_DIR, f"{today}_cookies.json")
        with open(cookie_file, 'w') as f:
            json.dump(meta['cookies'], f, indent=2)

    # Update README
    success = not cf_blocked and html_len > 5000
    status_icon = "PASS" if success else "FAIL"
    status_clean = str(status).split('\n')[0][:80]
    title_clean = title.replace('\n', ' ')[:50]
    entry = f"| {today} | {status_icon} | {status_clean} | {html_len:,} | {title_clean} |"

    update_readme(now_str, entry, success, status, html_len, title, source_file)

    if success:
        print(f"SUCCESS: Got {html_len:,} bytes, title: {title[:60]}")
        # Auto-build schedule
        try:
            import subprocess
            subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, 'build_schedule.py')], check=True)
            print("Schedule built successfully")
        except Exception as e:
            print(f"Schedule build failed: {e}")
    else:
        print(f"FAIL: {html_len:,} bytes, title: {title[:60]}")
        sys.exit(1)


def update_readme(now_str, entry, success, status, html_len, title, source_file):
    """Update README.md with latest fetch result."""
    if os.path.exists(README_PATH):
        with open(README_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ""

    if not content:
        content = """# ani.gamer.com.tw 抓取记录

每日通过 GitHub Action 使用 [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) 抓取 [ani.gamer.com.tw](https://ani.gamer.com.tw/) 源码，绕过 Cloudflare Challenge。

## 最新状态

(待更新)

## 历史记录

| 日期 | 状态 | HTTP | 大小 | 标题 |
|------|------|------|------|------|
"""
    # Update "最新状态" section
    status_text = "PASS - 成功获取页面" if success else "FAIL - CF 挑战未通过"
    lines = content.split('\n')
    new_lines = []
    in_status = False
    for line in lines:
        if "## 最新状态" in line:
            in_status = True
            new_lines.append(line)
            new_lines.append("")
            new_lines.append(f"**{now_str}** — {status_text}")
            new_lines.append(f"- HTTP Status: {status}")
            new_lines.append(f"- 页面大小: {html_len:,} bytes")
            new_lines.append(f"- 标题: {title[:80]}")
            new_lines.append(f"- 源码: [source/{today}.html](source/{today}.html)")
            new_lines.append("")
            continue
        if in_status and line.startswith("## "):
            in_status = False
        if in_status and (line.startswith("**2") or line.startswith("- ")):
            continue
        new_lines.append(line)

    content = '\n'.join(new_lines)

    # Add entry to history table
    if "| 日期 |" in content:
        content = content.replace(
            "| 日期 | 状态 | HTTP | 大小 | 标题 |\n|------|",
            f"| 日期 | 状态 | HTTP | 大小 | 标题 |\n{entry}\n|------|"
        )

    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__ == '__main__':
    main()
