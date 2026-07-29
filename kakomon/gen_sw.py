#!/usr/bin/env python3
"""Service Worker のバージョンを、配信するファイルの内容から決める。

バージョンが変わらないと古いキャッシュが残り、私が更新したものが届かない。
手で書き換えると忘れるので、内容のハッシュから自動で入れる。
"""
import hashlib, os, re

DIR = "../drill"
TARGET = os.path.join(DIR, "sw.js")

# 配信対象の中身をすべて混ぜてハッシュを取る
h = hashlib.sha256()
files = [os.path.join(DIR, "index.html"), os.path.join(DIR, "manifest.webmanifest")]
files += sorted(os.path.join(DIR, "data", f) for f in os.listdir(os.path.join(DIR, "data"))
                if f.endswith(".js"))
files += sorted(os.path.join(DIR, "icon", f) for f in os.listdir(os.path.join(DIR, "icon")))
for p in files:
    with open(p, "rb") as f:
        h.update(f.read())
ver = h.hexdigest()[:12]

src = open(TARGET).read()
src = re.sub(r'const VERSION = "[^"]*";', f'const VERSION = "{ver}";', src)
open(TARGET, "w").write(src)
print(f"→ {TARGET}  VERSION={ver}（{len(files)}ファイルの内容から算出）")
