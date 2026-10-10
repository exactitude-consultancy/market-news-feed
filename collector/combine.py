# -*- coding: utf-8 -*-
"""Merge the 8 shard files of one run into results/latest.json.gz (the server downloads it from branch 'data')."""
import datetime, glob, gzip, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parts = [json.load(gzip.open(f, "rt", encoding="utf-8")) for f in sorted(glob.glob(os.path.join(ROOT, "out", "**", "shard-*.json.gz"), recursive=True))]
if not parts:
    print("no shard output"); sys.exit(1)
stamps = {p["stamp"] for p in parts}
if len(stamps) != 1:
    print("shards from different queues:", stamps); sys.exit(1)
res = {"stamp": parts[0]["stamp"], "mode": parts[0].get("mode"), "generated_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
       "companies": {}, "industry": {}, "failed": [], "not_fetched": [], "shards": {}}
for p in parts:
    res["companies"].update(p["companies"])
    for k, v in p["industry"].items(): res["industry"].setdefault(k, []).extend(v)
    res["failed"] += p["failed"]; res["not_fetched"] += p["not_fetched"]
    res["shards"][str(p["shard"])] = dict(p["stats"], stopped=p["stopped"], failed=len(p["failed"]), not_fetched=len(p["not_fetched"]))
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
with gzip.open(os.path.join(ROOT, "results", "latest.json.gz"), "wt", encoding="utf-8") as fo:
    json.dump(res, fo, ensure_ascii=False)
print(json.dumps({"stamp": res["stamp"], "shards": len(parts), "companies_with_news": len(res["companies"]),
                  "failed": len(res["failed"]), "not_fetched": len(res["not_fetched"])}))
