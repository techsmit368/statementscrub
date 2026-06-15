# -*- coding: utf-8 -*-
"""Add a concise seo_title (<=60 chars) to any post whose title exceeds 60 chars.
The visible H1 (post.title) is left unchanged; only the <title> tag uses seo_title.
Files are rewritten as plain UTF-8 (no BOM)."""
import glob, json, os, collections

SEPS = [(": ", ""), ("? ", "?"), ("! ", "!"), (" (", ""), (" — ", ""), (" - ", ""), (". ", ".")]

def derive(title):
    if len(title) <= 60:
        return None
    for sep, keep in SEPS:
        if sep in title:
            prefix = title.split(sep)[0] + keep
            if 20 <= len(prefix) <= 60:
                return prefix.rstrip(" ,—-:")
    # fallback: trim at word boundary <= 60
    out = ""
    for w in title.split():
        if len(out) + len(w) + 1 > 60:
            break
        out = (out + " " + w).strip()
    return (out or title[:60]).rstrip(" ,—-:")

changed = []
for f in sorted(glob.glob("app/data/posts/*.json")):
    d = json.load(open(f, encoding="utf-8-sig"))
    st = derive(d.get("title", ""))
    if not st:
        continue
    # rebuild dict with seo_title right after title, preserving everything else
    new = collections.OrderedDict()
    for k, v in d.items():
        new[k] = v
        if k == "title":
            new["seo_title"] = st
    if "title" not in d:  # safety: title missing
        new["seo_title"] = st
    with open(f, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(new, fh, ensure_ascii=False, indent=2)
    changed.append((os.path.basename(f), len(st), st))

print(f"Added seo_title to {len(changed)} posts")
over = [c for c in changed if c[1] > 60]
print("Any seo_title still >60:", len(over))
print("--- sample (first 12) ---")
for name, n, st in changed[:12]:
    print(f"  {n:2} | {st}")
