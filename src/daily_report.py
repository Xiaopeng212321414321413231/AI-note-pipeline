"""每日流水线日报 — 自动汇总今天处理了多少文件"""
import os
import json
import glob
from datetime import date, datetime

today = date.today()
datestr = today.strftime("%Y-%m-%d")
weekday_cn = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][today.weekday()]

log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "daily", f"{datestr}.jsonl")
out_dir = os.path.join("G:/ai软件/obsidian/ai新闻", "流水线日报")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, f"流水线日报_{datestr}.md")

if not os.path.exists(log_path):
    print(f"今天 ({datestr}) 还没有处理过文件")
    with open(out_path, "w", encoding="utf-8") as f:
        nl = chr(10)
        head = f"---{nl}created: {datestr}{nl}tags: [流水线日报]{nl}---{nl}{nl}# 流水线日报 | {datestr}（{weekday_cn}）{nl}{nl}今天没有任何文件被处理。{nl}"
        f.write(head)
    print(f"已保存: {out_path}")
    exit()

entries = []
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

total = len(entries)
web_count = sum(1 for e in entries if e.get("url"))
local_count = total - web_count

nl = chr(10)
out_lines = [f"---{nl}created: {datestr}{nl}tags: [流水线日报, daily]{nl}---{nl}{nl}"]
out_lines.append(f"# 流水线日报 | {datestr}（{weekday_cn}）{nl}{nl}")
top = f"**今日处理：{total} 个文件**（📡 网页 {web_count} 篇 | 📁 本地 {local_count} 篇）{nl}{nl}"
out_lines.append(top)

out_lines.append("| # | 时间 | 文件 | 来源 | 字数 |" + nl)
out_lines.append("|---|------|------|------|------|" + nl)
for i, e in enumerate(entries, 1):
    fname = e.get("file", "?")
    link = e.get("path", "").replace("\\", "/")
    url = e.get("url", "")
    if url:
        sc = f"[🔗 网页]({url})"
    else:
        sc = "📁 本地"
    t = e.get("time", "?")
    c = e.get("chars", 0)
    row = f"| {i} | {t} | [{fname}]({link}) | {sc} | {c} |" + nl
    out_lines.append(row)

with open(out_path, "w", encoding="utf-8") as f:
    f.writelines(out_lines)

print(f"✅ 日报已生成: {out_path}")
print(f"   今日处理 {total} 个文件（网页 {web_count} 篇，本地 {local_count} 篇）")