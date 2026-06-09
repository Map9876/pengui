import asyncio
import json
import hashlib
from datetime import datetime
from playwright.async_api import async_playwright
import os
import re
import shutil
import argparse
import requests

today = datetime.now().strftime('%Y-%m-%d')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
data_file_path = os.path.join(SCRIPT_DIR, 'data.json')
image_directory = os.path.join(SCRIPT_DIR, 'covers')


async def main():
    print("[1/4] Launching browser to bypass bot protection...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("[1/4] Navigating to prhcomics.com...")
        await page.goto("https://prhcomics.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)

        # Fetch nonce via browser context
        print("[2/4] Fetching nonce via browser...")
        nonce_resp = await context.request.get(
            "https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce"
        )
        nonce_text = await nonce_resp.text()
        if not nonce_text.startswith('{'):
            print("[2/4] Got challenge page, waiting and retrying...")
            await page.wait_for_timeout(5000)
            nonce_resp = await context.request.get(
                "https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce"
            )
            nonce_text = await nonce_resp.text()

        nonce_data = json.loads(nonce_text)
        nonce = nonce_data['nonce']
        print(f"[2/4] Nonce: {nonce}")

        # Fetch all ISBNs via browser context (POST requests)
        print("[3/4] Fetching all ISBNs via browser...")
        all_isbns = []
        start = 0
        rows = 36
        total = None

        filters_json = json.dumps({
            "l1_category": "all-categories-manga",
            "filters": {
                "category": [],
                "sale-status": [{"label": "Coming Soon", "filterId": "sale-status", "key": "onSaleFrom", "value": "tomorrow"}],
                "format": [], "age": [], "grade": [], "guides": [], "publisher": [], "comics_publisher": []
            }
        })

        while True:
            form_data = (
                f"product_load_nonce={nonce}"
                f"&action=get_product_list"
                f"&postType=page"
                f"&postId=11538"
                f"&isbns=%5B%5D"
                f"&params=%7B%22source-page%22%3A%22category-landing-page%22%7D"
                f"&filters={requests.utils.quote(filters_json)}"
                f"&layout=grid-lg"
                f"&start={start}"
                f"&rows={rows}"
                f"&sort=frontlistiest_onsale%3Adesc"
            )

            resp = await context.request.post(
                "https://prhcomics.com/wp/wp-admin/admin-ajax.php",
                data=form_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://prhcomics.com/themes/?catUri=all-categories-manga",
                }
            )
            text = await resp.text()

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                print(f"  [WARN] JSON decode failed at start={start}, response: {text[:200]}")
                break

            if not data.get('success'):
                print(f"  [WARN] API returned success=false at start={start}")
                break

            isbns = data.get('data', {}).get('isbns', [])
            if not isbns:
                content = data.get('data', {}).get('content', '')
                isbns = re.findall(r'data-isbn="(\d+)"', content)

            page_total = data.get('data', {}).get('total', 0)
            has_more = data.get('data', {}).get('more', False)

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

        # Deduplicate
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
            await browser.close()
            return

        # Fetch MD5 for all ISBNs (images2 domain doesn't need prhcomics cookies)
        print(f"[4/4] Fetching cover MD5 hashes for {len(all_isbns)} ISBNs...")

        if not os.path.exists(image_directory):
            os.makedirs(image_directory)

        if os.path.exists(data_file_path):
            with open(data_file_path, 'r') as f:
                data = json.load(f)
        else:
            data = {}

        semaphore = asyncio.Semaphore(50)
        md5_results = [None] * len(all_isbns)

        async def fetch_md5(idx, isbn):
            async with semaphore:
                try:
                    resp = await context.request.get(
                        f"https://images2.penguinrandomhouse.com/cover/{isbn}?height=1"
                    )
                    if resp.status == 200:
                        body = await resp.body()
                        md5_results[idx] = hashlib.md5(body).hexdigest()
                except Exception:
                    pass

        tasks = [fetch_md5(i, isbn) for i, isbn in enumerate(all_isbns)]
        await asyncio.gather(*tasks)

        md5_ok = sum(1 for m in md5_results if m is not None)
        md5_fail = sum(1 for m in md5_results if m is None)
        print(f"MD5 fetch complete: {md5_ok} ok, {md5_fail} failed")

        # Update data
        changed_isbns = set()
        new_isbns = 0
        updated_isbns = 0
        for isbn, md5 in zip(all_isbns, md5_results):
            if md5:
                if isbn not in data:
                    data[isbn] = [{'date': today, 'md5': md5}]
                    changed_isbns.add(isbn)
                    new_isbns += 1
                elif data[isbn][-1]['md5'] != md5:
                    data[isbn].append({'date': today, 'md5': md5})
                    changed_isbns.add(isbn)
                    updated_isbns += 1
        print(f"Data update: {new_isbns} new, {updated_isbns} changed, {len(changed_isbns)} total changed")

        # Save data
        with open(data_file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data saved to {data_file_path}")

        # Download changed covers
        if changed_isbns:
            print(f"Downloading {len(changed_isbns)} changed covers...")
            async def download_cover(isbn):
                async with semaphore:
                    try:
                        resp = await context.request.get(
                            f"https://images2.penguinrandomhouse.com/cover/tif/{isbn}"
                        )
                        if resp.status == 200:
                            body = await resp.body()
                            file_path = os.path.join(image_directory, f"{isbn}.tif.{today}")
                            with open(file_path, 'wb') as f:
                                f.write(body)
                    except Exception:
                        pass

            await asyncio.gather(*[download_cover(isbn) for isbn in changed_isbns])
            print("Cover download complete.")
        else:
            print("No changed covers to download.")

        await browser.close()

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
    subprocess.run(f'hf auth login --token={os.environ["HF_TOKEN"]}', shell=True)

    from huggingface_hub import HfApi

    def upload_folder_to_huggingface(folder_path, model_repo_name, repo_type="model"):
        api = HfApi()
        path_in_repo = ""
        if os.path.exists(os.path.join(SCRIPT_DIR, "path_in_repo.txt")):
            with open(os.path.join(SCRIPT_DIR, "path_in_repo.txt"), "r") as file:
                path_in_repo = file.read().strip()

        files = api.list_repo_files(repo_id=model_repo_name, repo_type=repo_type)
        count = sum(1 for file in files if file.startswith(path_in_repo))

        if count > 9000:
            num = int(re.search(r"\d+", path_in_repo).group()) if path_in_repo else 0
            new_path_in_repo = f"{num + 1}pengui/"
            with open(os.path.join(SCRIPT_DIR, "path_in_repo.txt"), "w") as file:
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
