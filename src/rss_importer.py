# -*- coding: utf-8 -*-
import re, sys, os, json, hashlib, time
from datetime import datetime
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SOURCES = {
  "卡兹克(待wewe-rss)": {"type":"pending","note":"微信公众号，需we we-rss + 微信读书","todo":"git clone wewe-rss → npm install → node src/index.js"},
  "卡兹克替代(已发文章合集)": {"type":"rss","url":"https://rsshub.app/wechat/mp/profile/6874625?token=placeholder"},
  "量子位": {"type":"rss","url":"https://www.qbitai.com/feed"},
  "Karpathy": {"type":"rss","url":"https://karpathy.github.io/feed.xml"},
  "Sam Altman": {"type":"rss","url":"https://blog.samaltman.com/posts.atom"},
  "Greg Brockman": {"type":"rss","url":"https://blog.gregbrockman.com/feed"},
  "机器之心": {"type":"api",
    "url":"https://www.jiqizhixin.com/api/article_library/articles.json",
    "params":{"sort":"time","page":1,"per":20}},
}
DEDUP = PROJECT_ROOT / "data" / "rss_dedup.json"
QUEUE = PROJECT_ROOT / "data" / "rss_queue.json"
HDR = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def load(p):
  if p.exists(): return json.loads(p.read_text(encoding="utf-8"))
  return {}
def save(p,d):
  p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")

def fetch_rss(url):
  import feedparser, re as re2
  f = feedparser.parse(url, agent=HDR["User-Agent"])
  r = []
  for e in f.entries:
    t = e.get("title","").strip()
    if not t or t == "-":
      s = (e.get("summary") or "").strip()
      s = re2.sub(r"<[^>]+>","",s).strip()
      t = s.split("\n")[0][:80] if s else f"文章 {datetime.now():%m-%d}"
    r.append({"title":t,"url":e.get("link",""),"source":getattr(e,"author","")})
  return r

def fetch_jqzx():
  import urllib.request
  p = "&".join(f"{k}={v}" for k,v in SOURCES["机器之心"]["params"].items())
  r = urllib.request.Request(SOURCES["机器之心"]["url"]+"?"+p, headers=HDR)
  d = json.loads(urllib.request.urlopen(r,timeout=15).read().decode())
  return [{"title":a["title"],"url":f"https://www.jiqizhixin.com/articles/{a[chr(105)+chr(100)]}",
    "source":a.get("author","") or "机器之心"} for a in d.get("articles",[])]

def fetch(n,c):
  if c["type"]=="rss": return fetch_rss(c["url"])
  if c["type"]=="api": return fetch_jqzx()
  return []

def run():
  d=load(DEDUP); q=load(QUEUE); n=0
  for name,cfg in SOURCES.items():
    if cfg["type"] not in ("rss","api"): continue
    print(f"📡 {name}...")
    try: items=fetch(name,cfg)
    except Exception as e: print(f"   ❌ {e}"); continue
    print(f"   {len(items)} 篇")
    for a in items:
      u=a["url"]; t=a["title"]
      k=hashlib.md5(f"{u}|{t}".encode()).hexdigest()
      if k in d: continue
      d[k]={"title":t,"url":u,"added":datetime.now().isoformat()}
      u_norm = u.rstrip("/").lower()
      qk=hashlib.md5(u_norm.encode()).hexdigest()
      if qk not in q:
        q[qk]={"title":t,"url":u,"source":a.get("source",""),"status":"待处理"}; n+=1
  save(DEDUP,d); save(QUEUE,q)
  p=sum(1 for v in q.values() if v["status"]=="待处理")
  print(f"\n📊 新:{n} | 去重:{len(d)} | 队列待:{p}")
  return n

def proc(limit=None):
  q=load(QUEUE)
  p={k:v for k,v in q.items() if v.get("status")=="待处理"}
  if not p: print("✅ 队列为空"); return 0
  batch=len(p) if limit is None else min(limit,len(p))
  keys=list(p.keys())[:batch]; done=0
  for k in keys:
    a=p[k]; t=a["title"]; print(f"   🔄 {t[:40]}... ",end="",flush=True)
    try:
      from src.main import process_url
      r=process_url(a["url"])  # 去重由队列保证
      time.sleep(2); q[k]["status"]="已完成"; q[k]["done_at"]=datetime.now().isoformat()
      q[k]["result"]=str(r)[:100]; print("✅"); done+=1
    except Exception as e:
      q[k]["status"]="失败"; q[k]["error"]=str(e)[:200]; print(f"❌ {e}")
  save(QUEUE,q); rem=sum(1 for v in q.values() if v.get("status")=="待处理")
  print(f"\n📊 处理:{done} | 剩余:{rem}"); return done

def qview():
  q=load(QUEUE)
  if not q: print("📋 队列为空"); return
  s={}
  for v in q.values():
    st=v.get("status","未知"); s[st]=s.get(st,0)+1
  print("📋 队列状态:")
  for st,n in sorted(s.items()): print(f"   {st}: {n}")
  print(f"   总计: {len(q)}")

if __name__=="__main__":
  import argparse
  p=argparse.ArgumentParser()
  p.add_argument("mode",nargs="?",default="queue")
  a=p.parse_args()
  print(f"\n📡 RSS 导入器 — {a.mode}")
  if a.mode=="run": run()
  elif a.mode in ("proc","process"): proc()
  else: qview()

def fetch_zhihu(column_id):
    """从知乎专栏获取文章并加入队列"""
    import json, requests, hashlib, datetime
    from pathlib import Path

    api_url = f"https://zhuanlan.zhihu.com/api/columns/{column_id}/articles?limit=20"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        r = requests.get(api_url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception:
        # Fallback: try hotlist API
        try:
            alt_url = f"https://www.zhihu.com/api/v4/members/{column_id}/articles?limit=20"
            r = requests.get(alt_url, headers=headers, timeout=15)
            r.raise_for_status()
        except Exception as e:
            raise Exception(f"知乎获取失败: {e}")

    articles = r.json().get("data", [])
    if not articles:
        return 0

    qpath = Path(__file__).resolve().parent.parent / "data" / "rss_queue.json"
    if qpath.exists():
        q = json.loads(qpath.read_text(encoding="utf-8"))
    else:
        q = {}

    new_count = 0
    dpath = Path(__file__).resolve().parent.parent / "data" / "rss_dedup.json"
    if dpath.exists():
        d = json.loads(dpath.read_text(encoding="utf-8"))
    else:
        d = {}
    for a in articles:
        url = a.get("url", "")
        # Convert zhuanlan URL or article URL to standard form
        if not url.startswith("http"):
            url = f"https://zhuanlan.zhihu.com/p/{a.get('id', '')}"
        url_norm = url.rstrip("/").lower()
        uid = hashlib.md5(url_norm.encode()).hexdigest()
        # Also check DEDUP (跨扫描去重)
        t = a.get("title", "无标题")
        dk = hashlib.md5(f"{url_norm}|{t}".encode()).hexdigest()
        if dk in d:
            continue  # DEDUP 已有
        d[dk] = {"title":t, "url":url_norm, "added": datetime.datetime.now().isoformat()}
        if uid not in q:
            q[uid] = {
                "url": url_norm,
                "title": t,
                "source": f"知乎/{column_id}",
                "time": a.get("publishedTime", a.get("created", "")),
                "status": "待处理",
                "added": datetime.datetime.now().isoformat()
            }
            new_count += 1
    dpath.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    qpath.parent.mkdir(parents=True, exist_ok=True)
    qpath.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_count

