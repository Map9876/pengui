# pengui

Penguin Random House Comics manga data tracker. Daily GitHub Action fetches all "Coming Soon" manga ISBNs from [prhcomics.com](https://prhcomics.com), computes MD5 of cover images to detect changes, and uploads covers to HuggingFace.

## Status

- **断更日期**: 2025-08-03 (原项目 [Map987/pengui](https://github.com/Map987/pengui) 最后一次成功更新)
- **修复日期**: 2026-06-09
- **断更原因**: prhcomics.com 部署了 Fastly 客户端 JS 挑战 (反爬虫保护)，所有纯 HTTP 请求 (curl/requests/aiohttp) 被 403 拒绝

## 修复方案

使用 Playwright (无头 Chromium) 绕过 JS 挑战：
1. Playwright 访问 prhcomics.com → 通过 JS 挑战 → 获取 session cookies
2. 用 cookies + aiohttp 发送异步 API 请求 (快速、可并发)
3. 修复了原代码分页逻辑 bug (原来 `break` 只取一页就退出)

## 变更记录 (2026-06-09)

### run.py
- 新增 Playwright 绕过 Fastly 反爬虫保护
- 修复分页逻辑：循环 `start += 36` 直到 `more=false`
- 添加 `params` 字段 (`source-page: category-landing-page`)
- nonce 改为 GET 请求 (原代码用 GET，正确)
- 保留原有逻辑：MD5 比对、封面下载、HuggingFace 上传

### .github/workflows/main.yml
- 新增 `playwright install chromium` 和 `playwright install-deps chromium`
- 移除不再需要的 `nest_asyncio`、`beautifulsoup4`、`lxml` 依赖

### HuggingFace 存储
- 仓库变更: `haibaraconan/tif` (dataset) → `haibaraconan/tiff` (model)

## 数据源 API

### 1. 获取 nonce
```
GET https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce
```
响应:
```json
{"nonce":"xxxxxxxxxx","nonceNewsletter":"xxxxxxxxxx","nonceFilters":"xxxxxxxxxx","nonceDownloads":"xxxxxxxxxx"}
```

### 2. 获取产品列表 (分页)
```
POST https://prhcomics.com/wp/wp-admin/admin-ajax.php
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
```

参数:
| 字段 | 值 |
|------|-----|
| action | get_product_list |
| product_load_nonce | {nonce} |
| postType | page |
| postId | 11538 |
| isbns | [] |
| params | {"source-page":"category-landing-page"} |
| filters | {"l1_category":"all-categories-manga","filters":{"category":[],"sale-status":[{"label":"Coming Soon","filterId":"sale-status","key":"onSaleFrom","value":"tomorrow"}],"format":[],"age":[],"grade":[],"guides":[],"publisher":[],"comics_publisher":[]}} |
| layout | grid-lg |
| start | 0 (分页递增, 每页 36) |
| rows | 36 |
| sort | frontlistiest_onsale:desc |

响应关键字段:
- `data.total`: 总数 (约 1000-1200)
- `data.isbns`: ISBN 数组
- `data.more`: 是否有下一页
- `data.content`: HTML 内容 (含 `data-isbn` 属性)

### 3. 封面图片
- MD5 检测: `https://images2.penguinrandomhouse.com/cover/{isbn}?height=1`
- TIF 下载: `https://images2.penguinrandomhouse.com/cover/tif/{isbn}`

## 相关项目

- 原项目: https://github.com/Map987/pengui
- LNRelease: https://github.com/LNRelease/lnrelease.github.io
