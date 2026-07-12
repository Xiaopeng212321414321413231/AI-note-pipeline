"""每日流水线日报 — 自动汇总今天处理了多少文件"""
import os
import json
import glob
from datetime import date

today = date.today()
datestr = today.strftime("%Y-%m-%d")
weekday_cn = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][today.weekday()]

log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'daily', f'{datestr}.jsonl')
out_dir = os.path.join('G:/ai软件/obsidian/ai新闻', '流水线日报')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, f'流水线日报_{datestr}.md')

if not os.path.exists(log_path):
    print(f"今天 ({datestr}) 还没有处理过文件")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"---\ncreated: {datestr}\ntags: [流水线日报]\n---\n\n# 流水线日报 | {datestr}（{weekday_cn}）\n\n今天没有任何文件被处理。\n")
    print(f"已保存: {out_path}")
    exit()

entries = []
with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

total = len(entries)
lines = [f"---\ncreated: {datestr}\ntags: [流水线日报, daily]\n---\n\n"]
lines.append(f"# 流水线日报 | {datestr}（{weekday_cn}）\n\n")
lines.append(f"**今日处理：{total} 个文件**\n\n")

lines.append("| # | 时间 | 文件 | 字符数 |\n")
lines.append("|---|------|------|--------|\n")
for i, e in enumerate(entries, 1):
    fname = e.get('file', '?')
    link = e.get('path', '').replace('\\', '/')
    lines.append(f"| {i} | {e.get('time','?')} | [{fname}]({link}) | {e.get('chars',0)} |\n")

with open(out_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✅ 日报已生成: {out_path}")
print(f"   今日处理 {total} 个文件")