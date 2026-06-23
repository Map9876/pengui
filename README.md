<!-- /resume 6d0df6d8-8873-4f9e-9bfe-47999134577b penguin漫画下载 -->

# penguinrandom-manga-cover-scraper

所有漫画tiff封面文件储存在
 https://huggingface.co/haibaraconan/tiff 仓库
 
从 `2024-07-24 至 2025-08-03` 都有。
然后由于原网站更新，代码没有维护，导致 `2025-08-03 - 2026-06-09` 大概10个月间没有爬到图片，之后恢复正常。后续考虑怎么用cnb.cool的ai api去每日定时看action日志自行维护，或者用github自带的ai维护

**Gallery: https://map9876.github.io/pengui/**

Penguin Random House Comics 漫画封面变更追踪器。每日 GitHub Action 自动抓取即将发售的漫画 ISBN，检测封面 MD5 变化，压缩为 AVIF 并部署到 GitHub Pages 画廊。

## 技术报告

### 断更与修复

| 项目 | 日期 |
|------|------|
| 断更日期 | 2025-08-03 (原项目 [Map987/pengui](https://github.com/Map987/pengui) 最后一次成功更新) |
| 修复日期 | 2026-06-09 |
| 断更时长 | 约 11 个月 |
| 断更原因 | prhcomics.com 部署了 Fastly 客户端 JS 挑战 (反爬虫保护)，所有纯 HTTP 请求 (curl/requests/aiohttp) 被 403 拒绝 |

### 修复方案

**核心思路**: Playwright 只用于反爬虫保护的 AJAX 请求，图片域名不需要反爬用普通 requests。

| 请求类型 | 方法 | 说明 |
|----------|------|------|
| nonce 获取 | Playwright `context.request.get()` | prhcomics.com 域名，有 JS 挑战 |
| ISBN 列表 (POST) | Playwright `context.request.post()` | prhcomics.com 域名，有 JS 挑战 |
| MD5 检测 (1000+) | `requests` + 100 线程并发 | images2 域名，无反爬，约 1 分钟 |
| 封面下载 | `requests` + 50 线程并发 | images2 域名，无反爬 |

**为什么不用 Playwright 做所有请求**: Playwright 的 `context.request` 是串行的 HTTP 客户端，处理 1000+ 请求需要 30-50 分钟。`requests` + 线程池只需 1-2 分钟。

### 性能对比

| 版本 | Fetch data | Compress | 总耗时 |
|------|-----------|----------|--------|
| 旧版 (全部 Playwright) | 50+ 分钟 (未完成) | - | 超时 |
| 新版 (混合方案) | 2m 47s | 8m 7s | **约 11 分钟** |

### 运行数据 (2026-06-09 首次成功)

- ISBN 总数: 1180 (Coming Soon 筛选)
- 去重后唯一 ISBN: 1084
- MD5 获取: 1084 ok, 0 failed
- 数据更新: 1030 新增, 38 变更
- AVIF 压缩: 1160 张封面
- 画廊图片: 1165 张

## 架构

```
GitHub Action (每日 cron 16:00 UTC)
  │
  ├── run.py
  │   ├── Playwright → 绕过 JS 挑战 → 获取 nonce + ISBN 列表
  │   ├── requests (100线程) → MD5 检测
  │   ├── requests (50线程) → 下载变更封面 TIF
  │   ├── data.json 更新
  │   └── HuggingFace 上传 (haibaraconan/tiff)
  │
  ├── compress.py
  │   ├── 下载变更封面 → 缩放 800px → 压缩 AVIF
  │   └── 生成 site/data.json + site/img/
  │
  ├── GitHub Pages 部署 site/
  └── cnb.cool 推送 → EdgeOne Pages 部署
```

## 画廊功能

- iOS Photos 风格: 白色背景，日期分组，3 列网格
- 按日期分组展示封面变更 (最新在上)
- 响应式: 手机 3 列 / 平板 4 列 / 桌面 5 列
- 2px 间距，直角，`object-fit: cover`
- 日期标题 sticky 吸顶，毛玻璃效果

## 变更记录 (2026-06-09)

### run.py
- 新增 Playwright 绕过 Fastly 反爬虫保护 (仅用于 ISBN 列表)
- MD5/封面下载改用 requests + ThreadPoolExecutor (100/50 并发)
- 修复分页逻辑: 循环 `start += 36` 直到 `more=false`
- 添加 `params` 字段 (`source-page: category-landing-page`)
- `huggingface-cli` → `hf auth login`
- 添加详细日志: MD5 成功/失败计数，数据更新统计

### compress.py
- AVIF 压缩 800px 宽，quality=50
- 源图: `images2.penguinrandomhouse.com/cover/{isbn}?width=1600`
- 图片分散到 1000 个子目录 (000-999)，避免单文件夹超限

### site/ (画廊前端)
- index.html: iOS Photos 风格主页
- style.css: 白色主题响应式样式
- app.js: 日期分组 + 网格渲染

### .github/workflows/main.yml
- Playwright + Chromium 安装
- GitHub Pages 部署 (`environment: github-pages`)
- cnb.cool 推送 (EdgeOne Pages 部署)

### HuggingFace 存储
- 仓库: `haibaraconan/tiff` (model 类型)

## 数据源 API

### 1. 获取 nonce
```
GET https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce
```

### 2. 获取产品列表 (分页)
```
POST https://prhcomics.com/wp/wp-admin/admin-ajax.php
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
```

| 字段 | 值 |
|------|-----|
| action | get_product_list |
| product_load_nonce | {nonce} |
| postType | page |
| postId | 11538 |
| filters | Coming Soon (onSaleFrom=tomorrow) |
| start | 0 (分页递增, 每页 36) |
| rows | 36 |
| sort | frontlistiest_onsale:desc |

### 3. 封面图片 (无反爬)
- MD5 检测: `https://images2.penguinrandomhouse.com/cover/{isbn}?height=1`
- 高清源图: `https://images2.penguinrandomhouse.com/cover/{isbn}?width=1600`
- TIF 下载: `https://images2.penguinrandomhouse.com/cover/tif/{isbn}`

## 部署链接

| 平台 | 链接 |
|------|------|
| GitHub Pages | https://map9876.github.io/pengui/ |
| GitHub 仓库 | https://github.com/Map9876/pengui |
| HuggingFace | https://huggingface.co/haibaraconan/tiff |
| cnb.cool | https://cnb.cool/kfc50/penguin-edgeone-pages |

## 相关项目

- 原项目: https://github.com/Map987/pengui
- LNRelease: https://github.com/LNRelease/lnrelease.github.io
