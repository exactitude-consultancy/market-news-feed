# -*- coding: utf-8 -*-
"""
News fetcher for exactitudeconsultancy.com -- runs on GitHub Actions (8 machines in parallel), never on the
website server, so the server's IP never contacts Google News.

  python collector/news_fetch.py <shard> <shards>     -> out/shard-<k>.json.gz

The server publishes the day's work list in queue/today.json (company id + search name, industry search terms).
Each machine takes every <shards>-th item and, ONE request at a time:
  - asks Google News RSS for '"<name>" when:30d'   (the same query the server used to make)
  - keeps items not older than the cutoff whose headline names the company (match_rules.names_company --
    generated from the server's own code); industry terms keep all recent items
Politeness: 1.0-2.0 s random gap; on HTTP 429/503 wait 60 s and try once more; a second refusal trips the
STOP SWITCH -- this machine makes no further requests and lists the rest as not fetched (they go first tomorrow).
The server re-applies its full rules (publishers, story de-duplication, per-company limits) before storing.
"""
import datetime, email.utils, gzip, html, json, os, random, re, sys, time, urllib.parse
import requests
from match_rules import names_company

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def fetch(q):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(f'"{q}" when:30d') + "&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, headers=UA, timeout=25)
        return r.status_code, r.text
    except requests.RequestException:
        return 0, ""


def parse(xml):                                   # same parsing as the server's company_news.parse()
    items = []
    for blk in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def tag(t):
            m = re.search(rf"<{t}[^>]*>(.*?)</{t}>", blk, re.S)
            return html.unescape(m.group(1)).strip() if m else ""
        title, link, pub, src = tag("title"), tag("link"), tag("pubDate"), tag("source")
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3].strip()
        try:
            dt = email.utils.parsedate_to_datetime(pub).astimezone(datetime.timezone.utc).replace(tzinfo=None)
        except Exception:
            continue
        if title and link:
            items.append((title, link, src, dt))
    return items


def main():
    k, n = int(sys.argv[1]), int(sys.argv[2])
    q = json.load(open(os.path.join(ROOT, "queue", "today.json"), encoding="utf-8"))
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=int(q.get("cutoff_days", 45)))
    jobs = [("co", c[0], c[1]) for c in q.get("companies", [])] + [("ind", i[0], i[1]) for i in q.get("industry", [])]
    mine = jobs[k::n]
    out = {"stamp": q["stamp"], "mode": q.get("mode"), "shard": k, "companies": {}, "industry": {}, "failed": [], "not_fetched": [],
           "stats": {"requests": 0, "kept": 0, "seen": 0}, "stopped": ""}
    last = 0.0
    for idx, (kind, key, name) in enumerate(mine):
        if out["stopped"]:
            out["not_fetched"].append([kind, key]); continue
        d = random.uniform(1.0, 2.0) - (time.time() - last)
        if d > 0: time.sleep(d)
        last = time.time()
        s, xml = fetch(name); out["stats"]["requests"] += 1
        if s in (429, 503):
            time.sleep(60)
            s, xml = fetch(name); out["stats"]["requests"] += 1
            if s in (429, 503):
                out["stopped"] = f"HTTP {s} twice at item {idx + 1}/{len(mine)}"
                print(f"STOP SWITCH shard {k}: {out['stopped']}", flush=True)
                out["not_fetched"].append([kind, key]); continue
        if s != 200:
            out["failed"].append([kind, key]); continue
        items = parse(xml)
        out["stats"]["seen"] += len(items)
        keep = [it for it in items if it[3] >= cutoff and (kind == "ind" or names_company(it[0], name))]
        if keep:
            rows = [[t, l, src, dt.strftime("%Y-%m-%d %H:%M:%S")] for t, l, src, dt in keep]
            (out["companies"] if kind == "co" else out["industry"]).setdefault(str(key), []).extend(rows)
            out["stats"]["kept"] += len(rows)
        if (idx + 1) % 250 == 0:
            print(f"shard {k}: {idx + 1}/{len(mine)} done, kept {out['stats']['kept']}", flush=True)
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    with gzip.open(os.path.join(ROOT, "out", f"shard-{k}.json.gz"), "wt", encoding="utf-8") as fo:
        json.dump(out, fo, ensure_ascii=False)
    print(json.dumps({"shard": k, "items": len(mine), **out["stats"], "failed": len(out["failed"]),
                      "not_fetched": len(out["not_fetched"]), "stopped": out["stopped"]}))


if __name__ == "__main__":
    main()
