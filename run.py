import asyncio
import aiohttp
import json
import hashlib
from datetime import datetime
from playwright.async_api import async_playwright
import os
import re
import shutil
import argparse

today = datetime.now().strftime('%Y-%m-%d')

data_file_path = 'data.json'
image_directory = 'covers'


async def get_cookies_from_browser():
    """Use Playwright to visit the manga page, solve JS challenge, and extract cookies."""
    print("[1/3] Launching browser to bypass bot protection...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("[1/3] Navigating to prhcomics.com...")
        await page.goto("https://prhcomics.com/", wait_until="domcontentloaded", timeout=30000)

        # Wait for JS challenge to resolve
        await page.wait_for_timeout(5000)

        cookies = await context.cookies()
        print(f"[1/3] Got {len(cookies)} cookies from browser")
        await browser.close()

    # Convert Playwright cookie format to aiohttp cookie format
    cookie_dict = {}
    for c in cookies:
        cookie_dict[c['name']] = c['value']
    return cookie_dict


async def get_nonce(session):
    """Fetch nonce via GET request."""
    print("[2/3] Fetching nonce...")
    url = 'https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce'
    async with session.get(url) as response:
        text = await response.text()
        data = json.loads(text)
        nonce = data['nonce']
        print(f"[2/3] Nonce: {nonce}")
        return nonce


async def fetch_product_list(session, nonce, start, rows=36):
    """Fetch one page of product list."""
    url = "https://prhcomics.com/wp/wp-admin/admin-ajax.php"
    post_data = {
        'product_load_nonce': nonce,
        'action': 'get_product_list',
        'postType': 'page',
        'postId': '11538',
        'isbns': '[]',
        'params': '{"source-page":"category-landing-page"}',
        'filters': json.dumps({
            "l1_category": "all-categories-manga",
            "filters": {
                "category": [],
                "sale-status": [{"label": "Coming Soon", "filterId": "sale-status", "key": "onSaleFrom", "value": "tomorrow"}],
                "format": [],
                "age": [],
                "grade": [],
                "guides": [],
                "publisher": [],
                "comics_publisher": []
            }
        }),
        'layout': 'grid-lg',
        'start': str(start),
        'rows': str(rows),
        'sort': 'frontlistiest_onsale:desc',
    }

    async with session.post(url, data=post_data) as response:
        text = await response.text()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            print(f"  [WARN] JSON decode failed at start={start}, response: {text[:200]}")
            return [], 0, False

        if not data.get('success'):
            print(f"  [WARN] API returned success=false at start={start}")
            return [], 0, False

        content = data.get('data', {}).get('content', '')
        total = data.get('data', {}).get('total', 0)
        has_more = data.get('data', {}).get('more', False)

        isbn_pattern = r'data-isbn="(\d+)"'
        isbns = re.findall(isbn_pattern, content)

        # Also try the isbns array directly from response
        isbns_from_array = data.get('data', {}).get('isbns', [])
        if isbns_from_array:
            isbns = isbns_from_array

        return isbns, total, has_more


async def fetch_cover_md5(session, isbn, semaphore):
    async with semaphore:
        cover_url = f"https://images2.penguinrandomhouse.com/cover/{isbn}?height=1"
        try:
            async with session.get(cover_url) as response:
                if response.status == 200:
                    data = await response.read()
                    return hashlib.md5(data).hexdigest()
                else:
                    return None
        except Exception:
            return None


async def download_cover_image(session, isbn, semaphore):
    async with semaphore:
        cover_url = f"https://images2.penguinrandomhouse.com/cover/tif/{isbn}"
        try:
            async with session.get(cover_url) as response:
                if response.status == 200:
                    data = await response.read()
                    file_path = f"{image_directory}/{isbn}.tif.{today}"
                    with open(file_path, 'wb') as f:
                        f.write(data)
                    return True
                else:
                    return False
        except Exception:
            return False


async def main():
    # Step 1: Get cookies from browser
    cookies = await get_cookies_from_browser()

    if not os.path.exists(image_directory):
        os.makedirs(image_directory)

    if os.path.exists(data_file_path):
        with open(data_file_path, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    # Create aiohttp session with browser cookies
    cookie_jar = aiohttp.CookieJar()
    cookie_morsel = {}
    for name, value in cookies.items():
        cookie_morsel[name] = value

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://prhcomics.com',
        'referer': 'https://prhcomics.com/themes/?catUri=all-categories-manga',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    async with aiohttp.ClientSession(cookies=cookie_morsel, headers=headers) as session:
        # Step 2: Get nonce
        nonce = await get_nonce(session)

        # Step 3: Fetch all ISBNs with pagination
        print("[3/3] Fetching all ISBNs...")
        all_isbns = []
        start = 0
        rows = 36
        total = None

        while True:
            isbns, page_total, has_more = await fetch_product_list(session, nonce, start, rows)

            if not isbns:
                print(f"  No ISBNs at start={start}, stopping.")
                break

            if total is None:
                total = page_total
                print(f"  Total available: {total}")

            all_isbns.extend(isbns)
            print(f"  Fetched {len(isbns)} ISBNs at start={start}, cumulative: {len(all_isbns)}/{total}")

            if not has_more:
                print("  No more pages.")
                break

            start += rows

        # Deduplicate while preserving order
        seen = set()
        unique_isbns = []
        for isbn in all_isbns:
            if isbn not in seen:
                seen.add(isbn)
                unique_isbns.append(isbn)
        all_isbns = unique_isbns
        print(f"Total unique ISBNs: {len(all_isbns)}")

        if not all_isbns:
            print("No ISBNs found. Exiting.")
            return

        # Step 4: Fetch MD5 for all ISBNs
        print("Fetching cover MD5 hashes...")
        semaphore = asyncio.Semaphore(100)
        md5_tasks = [fetch_cover_md5(session, isbn, semaphore) for isbn in all_isbns]
        md5_results = await asyncio.gather(*md5_tasks)
        print("MD5 fetch complete.")

        # Step 5: Update data and track changes
        changed_isbns = set()
        for isbn, md5 in zip(all_isbns, md5_results):
            if md5:
                if isbn not in data:
                    data[isbn] = [{'date': today, 'md5': md5}]
                    changed_isbns.add(isbn)
                elif data[isbn][-1]['md5'] != md5:
                    data[isbn].append({'date': today, 'md5': md5})
                    changed_isbns.add(isbn)

        # Save data
        with open(data_file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data saved to {data_file_path}")

        # Step 6: Download changed covers
        if changed_isbns:
            print(f"Downloading {len(changed_isbns)} changed covers...")
            download_tasks = [download_cover_image(session, isbn, semaphore) for isbn in changed_isbns]
            await asyncio.gather(*download_tasks)
            print("Cover download complete.")
        else:
            print("No changed covers to download.")

    print("Done.")


# Run main
asyncio.run(main())

# HuggingFace upload
parser = argparse.ArgumentParser()
parser.add_argument('--token', type=str, help='HuggingFace token')
args = parser.parse_args()

if args.token:
    import subprocess
    os.environ["HF_TOKEN"] = args.token
    subprocess.run(f'huggingface-cli login --token={os.environ["HF_TOKEN"]}', shell=True)

    from huggingface_hub import HfApi

    def upload_folder_to_huggingface(folder_path, model_repo_name, repo_type="model"):
        api = HfApi()
        path_in_repo = ""
        if os.path.exists("path_in_repo.txt"):
            with open("path_in_repo.txt", "r") as file:
                path_in_repo = file.read().strip()

        files = api.list_repo_files(repo_id=model_repo_name, repo_type=repo_type)
        count = sum(1 for file in files if file.startswith(path_in_repo))

        if count > 9000:
            num = int(re.search(r"\d+", path_in_repo).group()) if path_in_repo else 0
            new_path_in_repo = f"{num + 1}pengui/"
            with open("path_in_repo.txt", "w") as file:
                file.write(new_path_in_repo)
            path_in_repo = new_path_in_repo

        api.upload_folder(
            folder_path=folder_path,
            repo_id=model_repo_name,
            repo_type=repo_type,
            path_in_repo=path_in_repo
        )

    model_repo_name = "haibaraconan/tiff"
    upload_folder_to_huggingface(image_directory, model_repo_name)
    shutil.rmtree(image_directory)
    print("HuggingFace upload complete.")
