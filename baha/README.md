# 巴哈姆特動畫瘋 週期表抓取

每日通过 GitHub Action 使用 [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) 抓取 [ani.gamer.com.tw](https://ani.gamer.com.tw/) 源码，绕过 Cloudflare Challenge，提取新番週期表（每周 1-7 的更新时间表）。

## 最新状态

**2026-07-01 04:09:16** — PASS - 成功获取页面
- HTTP Status: 200
- 页面大小: 361,416 bytes
- 标题: 巴哈姆特動畫瘋
- 源码: [source/2026-07-01.html](source/2026-07-01.html)

















































## 产出文件

| 文件 | 说明 |
|------|------|
| [schedule.html](schedule.html) | 暗色主题周表格，可独立嵌入 iframe |
| [schedule.json](schedule.json) | 机器可读的 JSON 数据 |
| [schedule.txt](schedule.txt) | 纯文本格式，方便 cron/系统读取 |
| [source/{date}.html](source/) | 每日原始页面源码 |
| [build_schedule.py](build_schedule.py) | 从源 HTML 提取週期表并生成以上文件 |

## 週期表数据 (2026-06-10)

本季共 **58** 部番劇

| 週一 | 週二 | 週三 | 週四 | 週五 | 週六 | 週日 |
|------|------|------|------|------|------|------|
| 4 | 6 | 9 | 8 | 10 | 6 | 15 |

### 示例 (週三)

| 時間 | 番名 |
|------|------|
| 00:00 | 左撇子艾倫 |
| 01:35 | 我回來了，他又來打擾了！ |
| 02:05 | 女神「異世界轉生想成為什麼」我「勇者的肋骨」 |
| 08:00 | 假面騎士 ZEZTZ |
| 19:00 | 從前從前有隻貓！世界喵童話 |
| 20:30 | 歡迎來到實力至上主義的教室 第四季 2年級篇 第一學期 |
| 21:00 | 出租女友 第五季 |
| 22:00 | Re：從零開始的異世界生活 第四季 |
| 23:30 | 溜掉的大魚比不上自己釣到的魚 |

## 架构

```
GitHub Action (每日 cron 18:00 UTC / 02:00 CST)
  │
  ├── docker run FlareSolverr (CF 挑战代理)
  │
  ├── fetch.py
  │   ├── FlareSolverr → 绕过 CF → 获取 HTML 源码
  │   ├── 保存 source/{date}.html
  │   ├── 自动调用 build_schedule.py
  │   └── 更新 README.md 状态
  │
  └── build_schedule.py
      ├── 从源 HTML 提取週期表 (週一~週日, 時間+番名)
      ├── 生成 schedule.html (暗色主题周表格)
      ├── 生成 schedule.json (机器可读)
      └── 生成 schedule.txt (纯文本)
```

## 嵌入使用

### iframe 嵌入
```html
<iframe src="https://map9876.github.io/pengui/baha/schedule.html"
        width="100%" height="600" frameborder="0"></iframe>
```

### 读取 schedule.txt 作为 cron 时间表
```bash
# 读取今天是周几，获取对应的更新时间
DAY=$(date +%u)  # 1=周一, 7=周日
grep -A 50 "== 週${DAY}" baha/schedule.txt | head -20
```

## 历史记录

| 日期 | 状态 | HTTP | 大小 | 标题 |
| 2026-06-10 | PASS | 200 | 371,401 | 巴哈姆特動畫瘋 |
|------|------|------|------|------|
| 2026-06-10 | PASS | 200 | 371,283 | 巴哈姆特動畫瘋 |
