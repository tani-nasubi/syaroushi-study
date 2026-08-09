#!/usr/bin/env python3
"""過去問に出てくる数値を、科目ごとに資料と突き合わせる。

条でも語でもなく**数値**を単位にした総当たり。誤り肢は数値の書き換えで
作られることが多いので、過去問に出た数値が資料のどこにも無ければ、
その数値をめぐる論点を扱っていない疑いがある。

  1. 肢から「数＋単位」を拾う（円・日・月・年・時間・人・％・分の◯ など）
  2. その科目の資料（生成節を除く）に同じ表記が出るか見る
  3. 出ないものだけ残す。表記ゆれを潰すため、漢数字・桁区切り・全角も見る
"""
import json, re, os, sys, glob, collections
sys.argv = ["numgap"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cover_all as C
from gen_qref import js_array

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "drill", "data")

# 問題の枠 → cover_all の科目キー
FRAME2SUBJ = {"労基安衛": ("労基", "安衛"), "労災": ("労災",), "雇用": ("雇用",),
              "徴収": ("徴収",), "一般常識": ("労一", "社一"),
              "健保": ("健保",), "国年": ("国年",), "厚年": ("厚年",)}

# 条・号は artgap.py が条単位で見る。年・月・年度は日付を拾うので入れない。
UNIT = r"(?:円|日|時間|人|歳|％|%|割|倍|週|箇月|か月|ヶ月|メートル|平方メートル|ルクス)"
NUM  = re.compile(r"(?<![0-9０-９，,.])([0-9０-９]{1,3}(?:[，,][0-9０-９]{3})*(?:[.．][0-9０-９]+)?)\s*(" + UNIT + ")")
BUN  = re.compile(r"([0-9０-９]{1,4})\s*分の\s*([0-9０-９]{1,4})")
Z    = str.maketrans("０１２３４５６７８９，．％", "0123456789,.%")

def variants(n, u):
    """桁区切り・全角・漢数字まじりの書き方を並べる。"""
    plain = n.replace(",", "").replace("，", "")
    out = {n + u, plain + u}
    if plain.isdigit() and len(plain) > 3:
        out.add(f"{int(plain):,}" + u)
    out.add(n)                       # 単位を伴わない書き方も一応見る
    out.add(plain)
    return {v for v in out if len(v) >= 2}

_law = []
def lawtext():
    """全法令XMLの本文をつないだもの。数値が制度のものかを見分けるのに使う。"""
    if not _law:
        import xml.etree.ElementTree as ET
        buf = []
        for p in sorted(glob.glob(os.path.join(HERE, "hourei", "*.xml"))):
            try:
                buf.append(re.sub(r"\s", "", "".join(ET.parse(p).getroot().itertext())))
            except Exception:
                pass
        _law.append("".join(buf))
    return _law[0]

K = "〇一二三四五六七八九"
def k2n(s):
    """1234 → 千二百三十四 のような、条文の書き方に寄せた形。"""
    s = s.replace(",", "").replace("，", "")
    if not s.isdigit() or len(s) > 4:
        return s
    n, out = int(s), ""
    for v, u in ((1000, "千"), (100, "百"), (10, "十")):
        d, n = divmod(n, v)
        if d:
            out += ("" if d == 1 else K[d]) + u
    return (out + (K[n] if n else "")) or "〇"

def main():
    minn = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    txt = {s: C.notes_text(s) for s in C.SUBJ}
    law = lawtext()
    hit = collections.Counter()
    where = {}
    for f in sorted(glob.glob(os.path.join(DATA, "*.js"))):
        s = open(f, encoding="utf-8").read()
        m = re.search(r'DRILL\.register\(\s*"([^"]+)"', s)
        if not m:
            continue
        tail = s[m.end():]
        try:
            arr = json.loads(tail[tail.index("["):tail.rindex("]") + 1])
        except Exception:
            arr = js_array(tail[tail.index("["):tail.rindex("]") + 1])
        if arr is None:
            continue
        for q in arr:
            src = str(q.get("src", ""))
            if "過去問" not in f and "年度" not in src:   # 本試験の肢だけを見る
                continue
            frame = next((k for k in FRAME2SUBJ if k in src or k in m.group(1)), None)
            if not frame:
                continue
            body = " ".join(str(q.get(k, "")) for k in ("q", "stem", "head", "tail"))
            body += " ".join(str(x) for x in (q.get("choices") or []))
            for g in (q.get("groups") or []):
                body += " ".join(map(str, g))
            body = body.translate(Z)
            got = {(a, b) for a, b in NUM.findall(body)}
            got |= {(f"{a}分の{b}", "") for a, b in BUN.findall(body)}
            for a, b in got:
                key = (frame, a, b)
                hit[key] += 1
                where.setdefault(key, src)

    miss = []
    for (frame, a, b), n in hit.items():
        if n < minn:
            continue
        subjs = FRAME2SUBJ[frame]
        if any(any(v in txt[s] for v in variants(a, b)) for s in subjs):
            continue
        # 作問者が挙げた事例の数値や過去年度の額を落とす。条文に出る数値だけを
        # 制度の数値とみなす（漢数字での書き方も見る）。
        if not any(v in law for v in variants(a, b) | {k2n(a) + b}):
            continue
        miss.append((n, frame, a + b, where[(frame, a, b)]))
    miss.sort(key=lambda x: -x[0])
    print(f"本試験の肢に出る数値 {len(hit)}通り（{minn}回以上に絞る）")
    print(f"合計 その科目の資料に見当たらない {len(miss)}件")
    for n, frame, v, src in miss:
        print(f"   {n}回 [{frame}] {v}　{src[:44]}")

if __name__ == "__main__":
    main()
