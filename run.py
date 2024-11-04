import asyncio
import aiohttp
import json
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os
import nest_asyncio
import re
import requests
import shutil
import sys
import argparse

nest_asyncio.apply()

today = datetime.now().strftime('%Y-%m-%d')

data_file_path = 'data.json'
image_directory = 'covers'

async def fetch_product_list(session, nonce, work_id, semaphore):
    async with semaphore:
        product_list_url = f"https://prhcomics.com/wp/wp-admin/admin-ajax.php"
        post_data = {
            'product_load_nonce': nonce,
            'action': 'get_product_list',
            'postType': 'page',
            'postId': '11538',
            'isbns': '[]',
            'filters': '{"l1_category":"all-categories-manga","filters":{"category":[],"sale-status":[{"label":"Coming Soon","filterId":"sale-status","key":"onSaleFrom","value":"tomorrow"}],"format":[],"age":[],"grade":[],"guides":[],"publisher":[],"comics_publisher":[]}}',
            'layout': 'grid-lg',
            'start': work_id,  # 使用work_id作为start值
            'rows': 36,
            'sort': 'frontlistiest_onsale:desc',
            'params': '%7B%22source-page%22%3A%22category-landing-page%22%7D'
        }
       # print(work_id)
        async with session.post(product_list_url, data=post_data) as response:
            text_content = await response.text()
        #   print(text_content)

            # 尝试解析响应为JSON
            try:
                parsed_json = json.loads(text_content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                parsed_json = None

            # 如果解析成功，使用正则表达式查找所有ISBN
            if parsed_json:
                content = parsed_json.get('data', {}).get('content', '')
                isbn_pattern = r'data-isbn="(\d+)"'
                isbns = re.findall(isbn_pattern, content)
                if isbns:
                    print("ISBNs found:")
                    for isbn in isbns:
                        print(isbn)
                    return isbns
                else:
                    print("No ISBNs found in the response.")
                    return None, False
            else:
                print("Failed to parse JSON.")
                return None, False

            # 返回ISBN列表
            return isbns if isbns else None

async def fetch_cover_md5(session, isbn, semaphore):
  async with semaphore:
    cover_url = f"https://images2.penguinrandomhouse.com/cover/{isbn}?height=1"
    async with session.get(cover_url) as response:
        if response.status == 200:
            data = await response.read()
            return hashlib.md5(data).hexdigest()
        else:
            return None

async def download_cover_image(session, isbn, semaphore):
  async with semaphore:
    cover_url = f"https://images2.penguinrandomhouse.com/cover/tif/{isbn}"
    async with session.get(cover_url) as response:
        if response.status == 200:
            data = await response.read()
            with open(f"{image_directory}/{isbn}.tif.{today}", 'wb') as f:
                print(f"ok")
                f.write(data)
            return True
        else:
            return False

async def main():
    nonce_url = 'https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce'
    response = requests.get(nonce_url)
    nonce = response.text.strip()
    nonce = json.loads(nonce)
    nonce = nonce['nonce']  # 假设响应内容是直接包含nonce的文本

    if not os.path.exists(image_directory):
        os.makedirs(image_directory)

    if os.path.exists(data_file_path):
        with open(data_file_path, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    semaphore = asyncio.Semaphore(100)  # 限制并发量为100

    async with aiohttp.ClientSession() as session:
        start = 0
        changed_isbns = set()  #
        all_valid_isbns = []  # 用于存储所有有效的ISBN
        finished = False  # 标记是否应该停止遍历

        while not finished:
            tasks = []
            # 创建任务时，确保 work_id 每次增加36
            for i in range(100):
                work_id = start + i * 36
                tasks.append(fetch_product_list(session, nonce, work_id, semaphore))

            isbns_lists = await asyncio.gather(*tasks)

            # 合并并过滤出有效的ISBN列表
            valid_isbns = [isbn for sublist in isbns_lists for isbn in sublist if sublist]
            all_valid_isbns.extend(valid_isbns)  # 将找到的ISBN添加到所有ISBN列表中

            # 如果这次没有找到任何ISBN，则停止遍历
            if not valid_isbns:
                finished = True
            else:
                # 增加 start 值，准备下一次循环
                start += 36

        # 在循环结束后，下载所有找到的ISBN的封面和MD5
            md5_tasks = [fetch_cover_md5(session, isbn, semaphore) for isbn in all_valid_isbns if isbn]
            md5_results = await asyncio.gather(*md5_tasks)
            # 更新数据字典
            for isbn, md5 in zip(all_valid_isbns, md5_results):
                if md5:
                 if isbn not in data:
                  data[isbn] = [{'date': today, 'md5': md5}]
                  changed_isbns.add(isbn)  # 如果MD5改变，添加到集合中
                 else:
        # Check if the last entry for the isbn has a different md5
                   if data[isbn][-1]['md5'] != md5:
                    data[isbn].append({'date': today, 'md5': md5})
                    changed_isbns.add(isbn)  # 如果MD5改变，添加到集合中


            # 保存更新后的数据
            with open(data_file_path, 'w') as f:
                json.dump(data, f, indent=4)
                print(f"dump to {data_file_path}")
            for isbn in changed_isbns:
    #            file_count = len([f for f in os.listdir(image_directory) if f.startswith(isbn)])
     #           if data[isbn][-1]['date'] == today and file_count < len(data[isbn]):
                    await download_cover_image(session, isbn, semaphore)

            # 增加 start 值，准备下一次循环
         #  start += 36 * 36
            break

# 运行主函数
asyncio.run(main())
print(f"ok")

import getpass
import os
import subprocess

parser = argparse.ArgumentParser(description='Process some integers.')
# 添加 --token 参数
parser.add_argument('--token', type=str, help='The token to be used')

# 解析命令行参数
args = parser.parse_args()

# 获取命令行传入的 token 参数值
account_name = args.token


# note: to automate this step, inject this env var into your container from a k8s Secret
os.environ["HF_TOKEN"] = account_name

subprocess.run(f'huggingface-cli login --token={os.environ["HF_TOKEN"]}', 
               shell=True)

from huggingface_hub import HfApi
from huggingface_hub import list_repo_files

"""
api = HfApi()
model_repo_name = "haibaraconan/tif"  # Format of Input  <Profile Name > / <Model Repo Name> 

#Create Repo in Hugging Face
folder_path = image_directory
#Upload Model folder from Local to HuggingFace 
api.upload_folder(
    folder_path=folder_path,
    repo_id=model_repo_name,
    repo_type="dataset"
)

# Publish Model Tokenizer on Hugging Face
"""

from huggingface_hub import HfApi, list_repo_files
import os
import re

def upload_folder_to_huggingface(folder_path, model_repo_name, repo_type="dataset"):
    api = HfApi()
    # 检查是否有txt文件，如果有，则读取内容作为path_in_repo参数
    path_in_repo = ""
    if os.path.exists("path_in_repo.txt"):
        with open("path_in_repo.txt", "r") as file:
            path_in_repo = file.read().strip()
    
    # 获取当前仓库的文件列表
    files = api.list_repo_files(model_repo_name, repo_type=repo_type)
    
    # 计算以path_in_repo开头的文件数量，防止huggingface单个文件夹超过最大1万文件
    count = sum(1 for file in files if file.startswith(path_in_repo))
    
    # 如果当前子目录下的文件数量超过9000，则更新path_in_repo
    if count > 9000:
        # 从path_in_repo中提取数字，并增加1
        num = int(re.search(r"\d+", path_in_repo).group()) if path_in_repo else 0
        new_path_in_repo = f"{num + 1}pengui/"
        # 更新txt文件
        with open("path_in_repo.txt", "w") as file:
            file.write(new_path_in_repo)
        path_in_repo = new_path_in_repo
    
    # 上传文件夹
    api.upload_folder(
        folder_path=folder_path,
        repo_id=model_repo_name,
        repo_type=repo_type,
        path_in_repo=path_in_repo
    )

# 使用示例
image_directory = image_directory
model_repo_name = "haibaraconan/tif"  # Format of Input  <Profile Name > / <Model Repo Name> 
upload_folder_to_huggingface(image_directory, model_repo_name)


shutil.rmtree(image_directory)
print(f"success")
