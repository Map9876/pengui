"""
Fetch ani.gamer.com.tw page source via Playwright (bypasses CF challenge).
Results are logged to README.md in this directory.
"""

import asyncio
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, 'README.md')
SOURCE_DIR = os.path.join(SCRIPT_DIR, 'source')

today = datetime.now().strftime('%Y-%m-%d')
now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


async def main():
    os.makedirs(SOURCE_DIR, exist_ok=True)

    print("[1/3] Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("[2/3] Navigating to ani.gamer.com.tw...")
        try:
            resp = await page.goto("https://ani.gamer.com.tw/", wait_until="domcontentloaded", timeout=30000)
            status = resp.status if resp else "no response"
        except Exception as e:
            status = f"error: {e}"

        # Wait for CF challenge
        await page.wait_for_timeout(10000)

        # Check if we got past CF
        title = await page.title()
        url = page.url
        html = await page.content()
        html_len = len(html)

        # Check for CF challenge indicators
        cf_blocked = "challenge" in html.lower()[:2000] or "just a moment" in title.lower()

        print(f"[3/3] Result: status={status}, title={title[:80]}, html={html_len} bytes, cf_blocked={cf_blocked}")

        # Save source
        source_file = os.path.join(SOURCE_DIR, f"{today}.html")
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Source saved to {source_file}")

        # Extract some useful info from the page
        try:
            anime_items = await page.query_selector_all('.anime-card, .newanime, .theme-list-main-block, [class*="anime"]')
            item_count = len(anime_items)
        except Exception:
            item_count = 0

        await browser.close()

    # Update README
    success = not cf_blocked and html_len > 5000
    status_icon = "PASS" if success else "FAIL"
    # Clean status for table (single line)
    status_clean = str(status).split('\n')[0][:80]
    title_clean = title.replace('\n', ' ')[:50]
    entry = f"| {today} | {status_icon} | {status_clean} | {html_len:,} | {title_clean} |"

    update_readme(now_str, entry, success, status, html_len, title, source_file)

    if success:
        print(f"SUCCESS: Got {html_len:,} bytes, title: {title[:60]}")
    else:
        print(f"FAIL: CF blocked or empty page, {html_len:,} bytes, title: {title[:60]}")
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

每日通过 GitHub Action 使用 Playwright 抓取 [ani.gamer.com.tw](https://ani.gamer.com.tw/) 源码，绕过 Cloudflare Challenge。

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


asyncio.run(main())
