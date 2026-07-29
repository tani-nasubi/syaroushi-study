#!/usr/bin/env python3
"""法令XMLから条文を引く。資料を書くときに原文を確かめるための道具。

    python3 art.py 労働基準法 64条の3 65
    python3 art.py 雇用保険法 22 --list        # 見出しだけ一覧
"""
import sys, os, re, ast
import xml.etree.ElementTree as ET

HERE   = os.path.dirname(os.path.abspath(__file__))
HOUREI = os.path.join(HERE, "hourei")
LAWS = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})",
        open(os.path.join(HERE, "gen_anaume2.py"), encoding="utf-8").read(), re.S).group(1))

def path_of(law):
    hit = [k for k, v in LAWS.items() if v == law] or \
          [k for k, v in LAWS.items() if law in v]
    if not hit:
        sys.exit(f"法令が見つからない: {law}\n候補: " + "、".join(sorted(set(LAWS.values())))[:400])
    return os.path.join(HOUREI, hit[0] + ".xml"), LAWS[hit[0]]

def label(num):
    # Num は "32_2"（第32条の2）のほか "29:31"（第29条〜第31条）の形もある
    p = num.split(":")[0].split("_")
    if not p[0].isdigit():
        return num
    s = f"第{int(p[0])}条"
    for x in p[1:]:
        s += f"の{int(x)}" if x.isdigit() else ""
    return s

def text_of(node):
    return "".join(node.itertext())

def main():
    law = sys.argv[1]
    want = [a.replace("第", "").replace("条", "") for a in sys.argv[2:] if not a.startswith("-")]
    listing = "--list" in sys.argv
    p, name = path_of(law)
    root = ET.parse(p).getroot()
    norm = lambda w: "第" + w.split("の")[0] + "条" + ("の" + w.split("の")[1] if "の" in w else "")
    targets = {norm(w) for w in want}
    for a in root.iter("Article"):
        lab = label(a.get("Num", ""))
        if targets and lab not in targets:
            continue
        cap = a.find("ArticleCaption")
        head = f"── {name} {lab}" + (f"　{text_of(cap)}" if cap is not None else "")
        print(head)
        if listing:
            continue
        for i, para in enumerate(a.findall("Paragraph"), 1):
            body = para.find("ParagraphSentence")
            if body is not None:
                print(f"  {i}　{text_of(body).strip()}")
            for it in para.findall("Item"):
                t = it.find("ItemTitle"); s = it.find("ItemSentence")
                print(f"    {text_of(t) if t is not None else ''}　"
                      f"{text_of(s).strip() if s is not None else ''}")
        print()

if __name__ == "__main__":
    main()
