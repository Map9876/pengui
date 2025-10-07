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
    print(f"检查点1: 开始获取产品列表，work_id={work_id}")
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
        print(f"检查点2: 准备发送POST请求，work_id={work_id}")
        
        try:
            async with session.post(product_list_url, data=post_data) as response:
                print(f"检查点3: 收到响应，状态码={response.status}，work_id={work_id}")
                text_content = await response.text()
                print(f"检查点4: 获取响应文本完成，长度={len(text_content)}，work_id={work_id}")
                
                # 打印前500个字符以便调试
                print(f"检查点5: 响应内容前500字符: {text_content[:500]}，work_id={work_id}")

                # 尝试解析响应为JSON
                try:
                    print(f"检查点6: 开始解析JSON，work_id={work_id}")
                    parsed_json = json.loads(text_content)
                    print(f"检查点7: JSON解析成功，work_id={work_id}")
                except json.JSONDecodeError as e:
                    print(f"检查点8: JSON解析错误: {e}，work_id={work_id}")
                    print(f"检查点9: 原始响应内容: {text_content}，work_id={work_id}")
                    parsed_json = None

                # 如果解析成功，使用正则表达式查找所有ISBN
                if parsed_json:
                    print(f"检查点10: 开始提取content字段，work_id={work_id}")
                    content = parsed_json.get('data', {}).get('content', '')
                    print(f"检查点11: content字段长度={len(content)}，work_id={work_id}")
                    
                    isbn_pattern = r'data-isbn="(\d+)"'
                    isbns = re.findall(isbn_pattern, content)
                    if isbns:
                        print(f"检查点12: 找到ISBNs: {isbns}，work_id={work_id}")
                        return isbns
                    else:
                        print(f"检查点13: 在响应中未找到ISBN，work_id={work_id}")
                        return None
                else:
                    print(f"检查点14: 解析JSON失败，work_id={work_id}")
                    return None
        except Exception as e:
            print(f"检查点15: 请求过程中发生异常: {e}，work_id={work_id}")
            return None

async def fetch_cover_md5(session, isbn, semaphore):
    print(f"检查点16: 开始获取封面MD5，ISBN={isbn}")
    async with semaphore:
        cover_url = f"https://images2.penguinrandomhouse.com/cover/{isbn}?height=1"
        try:
            async with session.get(cover_url) as response:
                print(f"检查点17: 封面MD5请求响应状态码={response.status}，ISBN={isbn}")
                if response.status == 200:
                    data = await response.read()
                    md5_hash = hashlib.md5(data).hexdigest()
                    print(f"检查点18: 计算MD5完成: {md5_hash}，ISBN={isbn}")
                    return md5_hash
                else:
                    print(f"检查点19: 封面MD5请求失败，状态码={response.status}，ISBN={isbn}")
                    return None
        except Exception as e:
            print(f"检查点20: 封面MD5请求异常: {e}，ISBN={isbn}")
            return None

async def download_cover_image(session, isbn, semaphore):
    print(f"检查点21: 开始下载封面图片，ISBN={isbn}")
    async with semaphore:
        cover_url = f"https://images2.penguinrandomhouse.com/cover/tif/{isbn}"
        try:
            async with session.get(cover_url) as response:
                print(f"检查点22: 封面下载响应状态码={response.status}，ISBN={isbn}")
                if response.status == 200:
                    data = await response.read()
                    file_path = f"{image_directory}/{isbn}.tif.{today}"
                    with open(file_path, 'wb') as f:
                        f.write(data)
                    print(f"检查点23: 封面下载完成，保存路径={file_path}，ISBN={isbn}")
                    return True
                else:
                    print(f"检查点24: 封面下载失败，状态码={response.status}，ISBN={isbn}")
                    return False
        except Exception as e:
            print(f"检查点25: 封面下载异常: {e}，ISBN={isbn}")
            return False

async def main():
    print("检查点26: 开始主函数")
    
    print("检查点27: 开始获取nonce")
    nonce_url = 'https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce'
    try:
        response = requests.get(nonce_url)
        print(f"检查点28: nonce请求响应状态码={response.status_code}")
        nonce = response.text.strip()
        print(f"检查点29: nonce原始响应: {nonce}")
        nonce = json.loads(nonce)
        nonce = nonce['nonce']  # 假设响应内容是直接包含nonce的文本
        print(f"检查点30: 获取nonce成功: {nonce}")
    except Exception as e:
        print(f"检查点31: 获取nonce失败: {e}")
        return

    if not os.path.exists(image_directory):
        print(f"检查点32: 创建图片目录: {image_directory}")
        os.makedirs(image_directory)
    else:
        print(f"检查点33: 图片目录已存在: {image_directory}")

    if os.path.exists(data_file_path):
        print(f"检查点34: 加载现有数据文件: {data_file_path}")
        with open(data_file_path, 'r') as f:
            data = json.load(f)
    else:
        print(f"检查点35: 创建新数据文件: {data_file_path}")
        data = {}

    semaphore = asyncio.Semaphore(100)  # 限制并发量为100

    async with aiohttp.ClientSession() as session:
        start = 0
        changed_isbns = set()  #
        all_valid_isbns = []  # 用于存储所有有效的ISBN
        finished = False  # 标记是否应该停止遍历

        while not finished:
            print(f"检查点36: 开始第{start//36 + 1}轮产品列表获取，start={start}")
            tasks = []
            # 创建任务时，确保 work_id 每次增加36
            for i in range(100):
                work_id = start + i * 36
                tasks.append(fetch_product_list(session, nonce, work_id, semaphore))

            print(f"检查点37: 等待所有产品列表请求完成")
            isbns_lists = await asyncio.gather(*tasks)
            print(f"检查点38: 所有产品列表请求完成，结果数量={len(isbns_lists)}")

            # 合并并过滤出有效的ISBN列表
            valid_isbns = [isbn for sublist in isbns_lists for isbn in sublist if sublist]
            print(f"检查点39: 有效ISBN数量={len(valid_isbns)}")
            all_valid_isbns.extend(valid_isbns)  # 将找到的ISBN添加到所有ISBN列表中

            # 如果这次没有找到任何ISBN，则停止遍历
            if not valid_isbns:
                print(f"检查点40: 本轮未找到有效ISBN，停止遍历")
                finished = True
            else:
                # 增加 start 值，准备下一次循环
                start += 36 * 100  # 注意：这里应该是 36 * 100 吗？原代码有疑问
                print(f"检查点41: 更新start值为{start}，准备下一轮")

        print(f"检查点42: 产品列表获取完成，总共找到{len(all_valid_isbns)}个ISBN")

        # 在循环结束后，下载所有找到的ISBN的封面和MD5
        if all_valid_isbns:
            print(f"检查点43: 开始获取所有ISBN的MD5")
            md5_tasks = [fetch_cover_md5(session, isbn, semaphore) for isbn in all_valid_isbns if isbn]
            md5_results = await asyncio.gather(*md5_tasks)
            print(f"检查点44: MD5获取完成")
            
            # 更新数据字典
            print(f"检查点45: 开始更新数据字典")
            for isbn, md5 in zip(all_valid_isbns, md5_results):
                if md5:
                    if isbn not in data:
                        print(f"检查点46: 新增ISBN {isbn}")
                        data[isbn] = [{'date': today, 'md5': md5}]
                        changed_isbns.add(isbn)
                    else:
                        # Check if the last entry for the isbn has a different md5
                        if data[isbn][-1]['md5'] != md5:
                            print(f"检查点47: ISBN {isbn} MD5有变化，添加新记录")
                            data[isbn].append({'date': today, 'md5': md5})
                            changed_isbns.add(isbn)
                        else:
                            print(f"检查点48: ISBN {isbn} MD5无变化")

            # 保存更新后的数据
            print(f"检查点49: 保存数据到文件")
            with open(data_file_path, 'w') as f:
                json.dump(data, f, indent=4)
                print(f"检查点50: 数据保存完成到 {data_file_path}")

            # 下载变化的封面
            if changed_isbns:
                print(f"检查点51: 开始下载{len(changed_isbns)}个变化的封面")
                download_tasks = [download_cover_image(session, isbn, semaphore) for isbn in changed_isbns]
                await asyncio.gather(*download_tasks)
                print(f"检查点52: 封面下载完成")
            else:
                print(f"检查点53: 没有变化的封面需要下载")
        else:
            print(f"检查点54: 没有找到任何有效的ISBN")

        print(f"检查点55: 主函数执行完成")

# 运行主函数
print("检查点56: 启动异步主函数")
asyncio.run(main())
print(f"检查点57: 异步主函数执行完成")

import getpass
import os
import subprocess

print("检查点58: 开始处理命令行参数")
parser = argparse.ArgumentParser(description='Process some integers.')
# 添加 --token 参数
parser.add_argument('--token', type=str, help='The token to be used')

# 解析命令行参数
args = parser.parse_args()

# 获取命令行传入的 token 参数值
account_name = args.token
print(f"检查点59: 获取到token参数: {account_name}")

# note: to automate this step, inject this env var into your container from a k8s Secret
os.environ["HF_TOKEN"] = account_name

print("检查点60: 开始HuggingFace登录")
subprocess.run(f'huggingface-cli login --token={os.environ["HF_TOKEN"]}', 
               shell=True)
print("检查点61: HuggingFace登录完成")

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
    print(f"检查点62: 开始上传文件夹到HuggingFace")
    api = HfApi()
    # 检查是否有txt文件，如果有，则读取内容作为path_in_repo参数
    path_in_repo = ""
    if os.path.exists("path_in_repo.txt"):
        with open("path_in_repo.txt", "r") as file:
            path_in_repo = file.read().strip()
        print(f"检查点63: 从文件读取path_in_repo: {path_in_repo}")
    
    # 获取当前仓库的文件列表
    print(f"检查点64: 获取仓库文件列表")
    files = api.list_repo_files(model_repo_name, repo_type=repo_type)
    print(f"检查点65: 仓库文件数量: {len(files)}")
    
    # 计算以path_in_repo开头的文件数量，防止huggingface单个文件夹超过最大1万文件
    count = sum(1 for file in files if file.startswith(path_in_repo))
    print(f"检查点66: 当前路径下文件数量: {count}")
    
    # 如果当前子目录下的文件数量超过9000，则更新path_in_repo
    if count > 9000:
        # 从path_in_repo中提取数字，并增加1
        num = int(re.search(r"\d+", path_in_repo).group()) if path_in_repo else 0
        new_path_in_repo = f"{num + 1}pengui/"
        # 更新txt文件
        with open("path_in_repo.txt", "w") as file:
            file.write(new_path_in_repo)
        path_in_repo = new_path_in_repo
        print(f"检查点67: 更新path_in_repo为: {path_in_repo}")
    
    # 上传文件夹
    print(f"检查点68: 开始上传文件夹")
    api.upload_folder(
        folder_path=folder_path,
        repo_id=model_repo_name,
        repo_type=repo_type,
        path_in_repo=path_in_repo
    )
    print(f"检查点69: 文件夹上传完成")

# 使用示例
print("检查点70: 准备上传图片目录")
image_directory = image_directory
model_repo_name = "haibaraconan/tif"  # Format of Input  <Profile Name > / <Model Repo Name> 
upload_folder_to_huggingface(image_directory, model_repo_name)

print("检查点71: 删除本地图片目录")
shutil.rmtree(image_directory)
print(f"检查点72: 全部流程完成")
