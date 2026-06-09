"""Build a standalone HTML schedule page from baha source."""

import re
import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(SCRIPT_DIR, 'source')
OUTPUT = os.path.join(SCRIPT_DIR, 'schedule.html')
SCHEDULE_JSON = os.path.join(SCRIPT_DIR, 'schedule.json')

DAYS = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
DAY_COLORS = {
    '週一': '#e74c3c', '週二': '#e67e22', '週三': '#f1c40f',
    '週四': '#2ecc71', '週五': '#3498db', '週六': '#9b59b6', '週日': '#e91e63'
}


def extract_schedule(html):
    """Extract schedule data from baha HTML."""
    schedule = {}
    for day in DAYS:
        idx = html.find(f'<h3 class="day-title">{day}</h3>')
        if idx == -1:
            continue
        next_day_idx = len(html)
        for d2 in DAYS:
            i = html.find(f'<h3 class="day-title">{d2}</h3>', idx + 10)
            if i != -1 and i < next_day_idx:
                next_day_idx = i
        block = html[idx:next_day_idx]
        pattern = r'<span class="text-anime-time">(\d+:\d+)</span>.*?<p class="text-anime-name">(.*?)</p>'
        matches = re.findall(pattern, block, re.DOTALL)
        schedule[day] = [{'time': t, 'name': n.strip()} for t, n in matches]
    return schedule


def build_html(schedule, updated):
    """Build standalone HTML page."""
    # Build time slots (all unique times sorted)
    all_times = set()
    for entries in schedule.values():
        for e in entries:
            all_times.add(e['time'])
    time_slots = sorted(all_times)

    # Build grid data: time -> day -> [anime names]
    grid = {}
    for day in DAYS:
        for entry in schedule.get(day, []):
            t = entry['time']
            if t not in grid:
                grid[t] = {}
            if day not in grid[t]:
                grid[t][day] = []
            grid[t][day].append(entry['name'])

    # Build table rows
    rows_html = ""
    for t in time_slots:
        rows_html += f'<tr><td class="time-cell">{t}</td>'
        for day in DAYS:
            anime_list = grid.get(t, {}).get(day, [])
            if anime_list:
                names = '<br>'.join(f'<span class="anime-tag">{n}</span>' for n in anime_list)
                rows_html += f'<td class="has-anime" style="border-left: 3px solid {DAY_COLORS[day]}">{names}</td>'
            else:
                rows_html += '<td class="empty-cell"></td>'
        rows_html += '</tr>\n'

    # Summary
    total = sum(len(v) for v in schedule.values())
    day_summary = ' | '.join(f'{d}: {len(schedule.get(d, []))}' for d in DAYS)

    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>巴哈姆特動畫瘋 - 新番時間表</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: "Microsoft JhengHei", "PingFang TC", -apple-system, sans-serif;
  background: #1a1a2e;
  color: #eee;
  padding: 16px;
}}
h1 {{
  text-align: center;
  font-size: 20px;
  margin-bottom: 4px;
  color: #fff;
}}
.meta {{
  text-align: center;
  font-size: 12px;
  color: #888;
  margin-bottom: 12px;
}}
.summary {{
  text-align: center;
  font-size: 13px;
  color: #aaa;
  margin-bottom: 16px;
  padding: 8px;
  background: #16213e;
  border-radius: 6px;
}}
.summary b {{ color: #3498db; }}
.table-wrap {{
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 700px;
}}
thead th {{
  background: #16213e;
  color: #fff;
  padding: 8px 4px;
  position: sticky;
  top: 0;
  z-index: 10;
  font-size: 14px;
  font-weight: 600;
  border-bottom: 2px solid #333;
}}
thead th.today {{
  background: #e74c3c;
}}
.time-cell {{
  background: #16213e;
  color: #3498db;
  font-weight: 700;
  font-size: 14px;
  padding: 6px 8px;
  text-align: center;
  white-space: nowrap;
  border-right: 2px solid #333;
  position: sticky;
  left: 0;
  z-index: 5;
}}
td {{
  padding: 4px 6px;
  vertical-align: top;
  border: 1px solid #2a2a4a;
  min-width: 90px;
}}
.has-anime {{
  background: #16213e;
}}
.empty-cell {{
  background: #111;
}}
.anime-tag {{
  display: inline-block;
  background: #0f3460;
  color: #e0e0e0;
  padding: 2px 6px;
  margin: 2px 0;
  border-radius: 3px;
  font-size: 12px;
  line-height: 1.4;
}}
.has-anime:hover {{
  background: #1a3a6a;
}}
@media (max-width: 600px) {{
  table {{ font-size: 11px; min-width: 600px; }}
  .time-cell {{ font-size: 12px; padding: 4px; }}
  .anime-tag {{ font-size: 10px; padding: 1px 4px; }}
}}
</style>
</head>
<body>
<h1>巴哈姆特動畫瘋 新番時間表</h1>
<div class="meta">更新: {updated} | 來源: ani.gamer.com.tw</div>
<div class="summary">
  本季共 <b>{total}</b> 部番劇<br>
  {day_summary}
</div>
<div class="table-wrap">
<table>
<thead>
<tr>
  <th>時間</th>
  {"".join(f'<th>{d}</th>' for d in DAYS)}
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
</body>
</html>'''


def main():
    # Find latest source file
    source_files = sorted([f for f in os.listdir(SOURCE_DIR) if f.endswith('.html') and not f.endswith('_cookies.json')])
    if not source_files:
        print("No source files found")
        return

    latest = source_files[-1]
    source_path = os.path.join(SOURCE_DIR, latest)
    updated = latest.replace('.html', '')

    print(f"Using source: {latest}")
    with open(source_path, 'r', encoding='utf-8') as f:
        html = f.read()

    schedule = extract_schedule(html)
    if not schedule:
        print("No schedule data found in source")
        return

    # Save JSON
    with open(SCHEDULE_JSON, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    print(f"Schedule JSON saved: {SCHEDULE_JSON}")

    # Build HTML
    html_out = build_html(schedule, updated)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html_out)
    print(f"Schedule HTML saved: {OUTPUT}")

    total = sum(len(v) for v in schedule.values())
    print(f"Total: {total} anime across {len(schedule)} days")


if __name__ == '__main__':
    main()
