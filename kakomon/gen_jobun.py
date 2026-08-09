#!/usr/bin/env python3
"""過去問が挙げている条文の本文を、法令XMLから抜き出して表にする。

本試験の過去問には解説が付いていない（3,381問）。作り話の解説を足すより、
**その肢が引いている条文の原文**を並べて見せるほうが確かめられる。
誤り肢はたいてい条文の一語を書き換えて作られているので、原文と見比べれば
どこが違うかは自分で分かる。

  出力: ../drill/data/jobun.js
    JOBUN = { "労働基準法第32条": ["労働時間", "使用者は、労働者に、休憩時間を除き…"], ... }
             （見出し, 本文）。本文は長すぎるものを切り詰める。
"""
import os, re, json, glob, ast, collections
import xml.etree.ElementTree as ET

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.dirname(HERE)
DATA   = os.path.join(ROOT, "drill", "data")
HOUREI = os.path.join(HERE, "hourei")
OUT    = os.path.join(DATA, "jobun.js")
LIMIT  = 420          # 1条あたりの文字数の上限。長い条は頭だけで足りる

LAWS = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})",
        open(os.path.join(HERE, "gen_anaume2.py"), encoding="utf-8").read(), re.S).group(1))
ALIAS = {"労災保険法": "労働者災害補償保険法",
         "労働保険の保険料の徴収等に関する法律": "労働保険徴収法"}

CITE = re.compile(r"([一-鿿ぁ-んァ-ヴ・]{2,20}?(?:法|規則|令))\s*第\s*([0-9０-９]{1,3})\s*条"
                  r"(?:\s*の\s*([0-9０-９]{1,2}))?")
Z = str.maketrans("０１２３４５６７８９", "0123456789")

def cited():
    """過去問・自作問題が挙げている (法令名, 条ラベル) を数える。"""
    c = collections.Counter()
    for f in sorted(glob.glob(os.path.join(DATA, "*.js"))):
        s = open(f, encoding="utf-8").read()
        try:
            arr = json.loads(s[s.index("["):s.rindex("]") + 1])
        except Exception:
            continue
        for q in arr:
            if q.get("type") == "ana":       # 条文穴埋めは元から原文なので要らない
                continue
            body = " ".join(str(q.get(k, "")) for k in ("q", "stem", "head", "tail"))
            body += " ".join(str(x) for x in (q.get("choices") or []))
            for g in (q.get("groups") or []):
                body += " ".join(map(str, g))
            for m in CITE.finditer(body):
                law = ALIAS.get(m.group(1), m.group(1))
                lab = f"第{int(m.group(2).translate(Z))}条" + \
                      (f"の{int(m.group(3).translate(Z))}" if m.group(3) else "")
                c[(law, lab)] += 1
    return c

_tree = {}
def articles(law):
    """法令名 → {条ラベル: (見出し, 本文)}。本則を優先し、附則は採らない。"""
    if law in _tree:
        return _tree[law]
    lid = next((k for k, v in LAWS.items() if v == law), None)
    p = os.path.join(HOUREI, f"{lid}.xml") if lid else None
    out = {}
    if p and os.path.exists(p):
        root = ET.parse(p).getroot()
        main = root.find(".//MainProvision") or root
        for a in main.iter("Article"):
            q = a.get("Num", "").split(":")[0].split("_")
            if not q[0].isdigit():
                continue
            lab = f"第{int(q[0])}条" + (f"の{int(q[1])}" if len(q) > 1 and q[1].isdigit() else "")
            if lab in out:
                continue
            cap = a.find("ArticleCaption")
            head = re.sub(r"[（）]", "", "".join(cap.itertext()).strip()) if cap is not None else ""
            # 項ごとに番号を振って並べる。号は本文が長くなるので入れない。
            paras = []
            for i, pa in enumerate(a.findall("Paragraph"), 1):
                sent = pa.find("ParagraphSentence")
                if sent is None:
                    continue
                t = re.sub(r"\s+", "", "".join(sent.itertext()))
                if t:
                    paras.append((f"{i}　" if len(a.findall("Paragraph")) > 1 else "") + t)
            body = "\n".join(paras)
            if len(body) > LIMIT:
                body = body[:LIMIT].rstrip("、。") + "…"
            out[lab] = (head, body)
    _tree[law] = out
    return out

def from_qref():
    """gen_qref.py が割り出した根拠の条も、本文を用意する対象に入れる。"""
    p = os.path.join(DATA, "qref.js")
    if not os.path.exists(p):
        return []
    raw = open(p, encoding="utf-8").read()
    try:
        d = json.loads(raw.split("=", 1)[1].rsplit(";", 1)[0])
    except Exception:
        return []
    out = []
    for ks in d.values():
        for k in ks:
            m = re.match(r"^(.+?)(第\d+条(?:の\d+)?)$", k)
            if m:
                out.append((m.group(1), m.group(2)))
    return out

def main():
    c = cited()
    for k in from_qref():
        c[k] += 0            # 数は増やさず、対象にだけ加える
    got, miss = {}, collections.Counter()
    for (law, lab), n in c.most_common():
        arts = articles(law)
        if lab in arts and arts[lab][1]:
            got[f"{law}{lab}"] = list(arts[lab])
        else:
            miss[law] += 1
    size = sum(len(k) + len(v[0]) + len(v[1]) for k, v in got.items())
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("/* 過去問が挙げている条文の本文。kakomon/gen_jobun.py が法令XMLから作る。 */\n")
        f.write("window.JOBUN = " + json.dumps(got, ensure_ascii=False, indent=0) + ";\n")
    print(f"→ {OUT}  {len(got)}条 / 約{size:,}字 / {os.path.getsize(OUT):,} bytes")
    if miss:
        print("   本文を取れなかった法令: " +
              "、".join(f"{k}{v}" for k, v in miss.most_common(8)))

if __name__ == "__main__":
    main()
