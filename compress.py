"""
Compress changed cover images to AVIF format for the gallery site.

Reads data.json to find ISBNs whose MD5 changed today (or on a specified date),
downloads the cover, compresses to AVIF 800px width, and saves to site/img/.

Also generates site/data.json with only the ISBNs that have compressed images.
"""

import json
import os
import sys
import hashlib
from datetime import datetime
from io import BytesIO
import requests

try:
    from PIL import Image
    import pillow_avif
    HAS_AVIF = True
except ImportError:
    HAS_AVIF = False
    print("WARNING: pillow-avif-plugin not installed, falling back to WebP")

from datetime import timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
today = datetime.now().strftime('%Y-%m-%d')

data_file_path = os.path.join(SCRIPT_DIR, 'data.json')
site_dir = os.path.join(SCRIPT_DIR, 'site')
img_dir = os.path.join(site_dir, 'img')
site_data_path = os.path.join(site_dir, 'data.json')

IMG_WIDTH = 800


def get_subdir(isbn):
    """Distribute files into subdirs 000-999 to avoid single-folder limits."""
    h = 0
    for c in isbn:
        h = (h * 31 + ord(c)) & 0x7fffffff
    return str(h % 1000).zfill(3)


def find_changed_isbns(data, target_date=None):
    """Find ISBNs whose MD5 changed on the target date."""
    if target_date is None:
        target_date = today

    changed = []
    for isbn, entries in data.items():
        for entry in entries:
            if entry['date'] == target_date:
                changed.append(isbn)
                break
    return changed


def find_all_isbns_with_dates(data):
    """Find all ISBNs that ever had a change, with their change dates."""
    result = {}
    for isbn, entries in data.items():
        dates = [e['date'] for e in entries]
        result[isbn] = dates
    return result


def download_and_compress(isbn, target_date=None):
    """Download cover image and compress to AVIF."""
    if target_date is None:
        target_date = today

    subdir = get_subdir(isbn)
    out_dir = os.path.join(img_dir, subdir)
    os.makedirs(out_dir, exist_ok=True)

    ext = 'avif' if HAS_AVIF else 'webp'
    out_path = os.path.join(out_dir, f'{isbn}.{ext}')

    # Skip if already exists
    if os.path.exists(out_path):
        return True

    # Download cover at higher resolution for quality
    cover_url = f"https://images.penguinrandomhouse.com/cover/{isbn}?width={IMG_WIDTH * 2}"
    try:
        resp = requests.get(cover_url, timeout=30)
        if resp.status_code != 200:
            print(f"  [WARN] Failed to download {isbn}: HTTP {resp.status_code}")
            return False

        img = Image.open(BytesIO(resp.content))

        # Resize to target width maintaining aspect ratio
        w, h = img.size
        if w > IMG_WIDTH:
            ratio = IMG_WIDTH / w
            new_h = int(h * ratio)
            img = img.resize((IMG_WIDTH, new_h), Image.LANCZOS)

        # Convert to RGB if necessary (AVIF doesn't support CMYK/palette)
        if img.mode in ('CMYK', 'P', 'LA'):
            img = img.convert('RGB')
        elif img.mode == 'RGBA':
            # Keep RGBA for AVIF (supports alpha)
            pass
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Save as AVIF or WebP
        if HAS_AVIF:
            img.save(out_path, 'AVIF', quality=50, speed=6)
        else:
            img.save(out_path, 'WEBP', quality=70)

        size_kb = os.path.getsize(out_path) / 1024
        print(f"  {isbn} -> {subdir}/{isbn}.{ext} ({size_kb:.0f} KB)")
        return True

    except Exception as e:
        print(f"  [ERROR] {isbn}: {e}")
        return False


def generate_site_data(data):
    """Generate site/data.json with all ISBNs that have images."""
    site_data = {}
    ext = 'avif' if HAS_AVIF else 'webp'

    for isbn, entries in data.items():
        subdir = get_subdir(isbn)
        img_path = os.path.join(img_dir, subdir, f'{isbn}.{ext}')
        if os.path.exists(img_path):
            site_data[isbn] = entries

    with open(site_data_path, 'w') as f:
        json.dump(site_data, f, indent=2)

    print(f"Site data: {len(site_data)} ISBNs with images -> {site_data_path}")
    return site_data


def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else None

    if not os.path.exists(data_file_path):
        print(f"Error: {data_file_path} not found")
        return

    with open(data_file_path, 'r') as f:
        data = json.load(f)

    os.makedirs(img_dir, exist_ok=True)

    if target_date:
        # Compress only for a specific date
        isbns = find_changed_isbns(data, target_date)
        print(f"Compressing {len(isbns)} covers changed on {target_date}...")
        for isbn in isbns:
            download_and_compress(isbn, target_date)
    else:
        # Compress ALL changed covers (initial setup)
        # Find the most recent date with changes
        all_dates = set()
        for entries in data.values():
            for e in entries:
                all_dates.add(e['date'])

        latest_dates = sorted(all_dates)[-7:]  # Last 7 days
        print(f"Compressing covers from last 7 days: {latest_dates}")

        isbns_to_compress = set()
        for isbn, entries in data.items():
            for e in entries:
                if e['date'] in latest_dates:
                    isbns_to_compress.add(isbn)
                    break

        print(f"Total ISBNs to compress: {len(isbns_to_compress)}")
        success = 0
        for i, isbn in enumerate(sorted(isbns_to_compress)):
            if download_and_compress(isbn):
                success += 1
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{len(isbns_to_compress)}")
        print(f"Compressed: {success}/{len(isbns_to_compress)}")

    # Generate site data
    generate_site_data(data)

    # Count total images
    total_images = 0
    for root, dirs, files in os.walk(img_dir):
        for f in files:
            if f.endswith(('.avif', '.webp')):
                total_images += 1
    print(f"Total images in site/img/: {total_images}")
    print("Done.")


if __name__ == '__main__':
    main()
