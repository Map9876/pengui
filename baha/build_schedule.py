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
    """Build standalone HTML page with light theme like itv6.jp."""
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

    # Current day and time for auto-scroll
    now = datetime.now()
    weekday_map = {0: '週一', 1: '週二', 2: '週三', 3: '週四', 4: '週五', 5: '週六', 6: '週日'}
    today_day = weekday_map.get(now.weekday(), '')
    now_time = now.strftime('%H:%M')
    # Find closest time slot
    closest_time = time_slots[0] if time_slots else '00:00'
    for t in time_slots:
        if t <= now_time:
            closest_time = t
    today_col_idx = DAYS.index(today_day) + 1 if today_day in DAYS else -1

    # Build table rows
    rows_html = ""
    for t in time_slots:
        is_current = (t == closest_time and today_day)
        row_cls = ' class="current-row"' if is_current else ''
        rows_html += f'<tr{row_cls} id="t{t.replace(":", "")}"><td class="time-cell">{t}</td>'
        for day in DAYS:
            anime_list = grid.get(t, {}).get(day, [])
            if anime_list:
                names = '<br>'.join(f'<span class="anime-tag">{n}</span>' for n in anime_list)
                rows_html += f'<td class="has-anime">{names}</td>'
            else:
                rows_html += '<td class="empty-cell"></td>'
        rows_html += '</tr>\n'

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
  font-family: "Microsoft JhengHei", "PingFang TC", "Hiragino Kaku Gothic Pro", -apple-system, sans-serif;
  background: #f5f5f5;
  color: #333;
  padding: 12px;
}}
h1 {{
  text-align: center;
  font-size: 18px;
  margin-bottom: 2px;
  color: #222;
}}
.meta {{
  text-align: center;
  font-size: 11px;
  color: #999;
  margin-bottom: 8px;
}}
.summary {{
  text-align: center;
  font-size: 12px;
  color: #666;
  margin-bottom: 10px;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
}}
.summary b {{ color: #1a73e8; }}
.table-wrap {{
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  max-height: calc(100vh - 100px);
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  min-width: 650px;
}}
thead th {{
  background: #fafafa;
  color: #333;
  padding: 6px 4px;
  position: sticky;
  top: 0;
  z-index: 10;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 2px solid #ccc;
}}
thead th.today-col {{
  background: #e8f0fe;
  color: #1a73e8;
}}
.time-cell {{
  background: #fafafa;
  color: #555;
  font-weight: 600;
  font-size: 12px;
  padding: 4px 6px;
  text-align: center;
  white-space: nowrap;
  border-right: 1px solid #ddd;
  position: sticky;
  left: 0;
  z-index: 5;
  width: 45px;
  min-width: 45px;
}}
td {{
  padding: 3px 5px;
  vertical-align: top;
  border: 1px solid #e8e8e8;
  min-width: 80px;
}}
.has-anime {{
  background: #fff;
}}
.has-anime.today-cell {{
  background: #f0f7ff;
}}
.empty-cell {{
  background: #fafafa;
}}
.anime-tag {{
  display: inline-block;
  background: #f0f0f0;
  color: #333;
  padding: 1px 5px;
  margin: 1px 0;
  border-radius: 2px;
  font-size: 11px;
  line-height: 1.5;
  border-left: 3px solid #1a73e8;
}}
.has-anime:hover {{
  background: #f5f5f5;
}}
.current-row {{
  background: #fff8e1;
}}
.current-row .time-cell {{
  background: #fff8e1;
  color: #e65100;
  font-weight: 700;
}}
.current-marker {{
  display: inline-block;
  background: #e65100;
  color: #fff;
  font-size: 9px;
  padding: 0 4px;
  border-radius: 2px;
  margin-left: 4px;
  vertical-align: middle;
}}
@media (max-width: 600px) {{
  table {{ font-size: 11px; min-width: 550px; }}
  .time-cell {{ font-size: 11px; padding: 3px 4px; width: 40px; min-width: 40px; }}
  .anime-tag {{ font-size: 10px; padding: 1px 3px; }}
}}
</style>
</head>
<body>
<h1>新番時間表</h1>
<div class="meta">更新: {updated} | 來源: ani.gamer.com.tw</div>
<div class="summary">
  本季共 <b>{total}</b> 部番劇 | {day_summary}
</div>
<div class="table-wrap" id="tableWrap">
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
<script>
// Auto-scroll to current time
(function() {{
  var wrap = document.getElementById('tableWrap');
  var target = document.getElementById('t{closest_time.replace(":", "")}');
  if (target && wrap) {{
    var offset = target.offsetTop - wrap.offsetTop - 60;
    wrap.scrollTop = Math.max(0, offset);
  }}
}})();
</script>
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
