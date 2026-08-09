#!/usr/bin/env python3
"""過去問の「正しい肢」を一つずつ、資料が扱っているか採点する。

条・語・数値の総当たりで残らなかったものを拾うための、肢そのものを単位にした
見方。誤り肢は条文を書き換えて作られるので当てにならないが、**正しい肢**は
そのまま覚えるべき内容なので、それが資料に無ければ穴とみなせる。

  1. 「正しいものはどれか」なら正解の肢、「誤っているものはどれか」なら
     正解以外の肢を、正しい記述として集める
  2. 肢から4字以上の語（漢字・カタカナの連なり）を取り出す
  3. その科目の資料に何割の語が出るかを数える。割合の低い肢だけ残す
"""
import json, re, os, sys, glob
_ARG = sys.argv[1:]          # cover_all が argv を見るので先に取っておく
sys.argv = ["stmtgap"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cover_all as C
from gen_qref import js_array

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "drill", "data")
FRAME = {"労基安衛": ("労基", "安衛"), "労災": ("労災", "徴収"), "雇用": ("雇用", "徴収"),
         "徴収": ("徴収",), "一般常識": ("労一", "社一"), "労一": ("労一",), "社一": ("社一",),
         "健保": ("健保",), "国年": ("国年",), "厚年": ("厚年",)}
WORD = re.compile(r"[一-鿿]{4,12}|[ァ-ヴー]{4,12}")
WRONG = re.compile(r"誤(っ|つ)ているもの|正しくないもの|適切でないもの")
RIGHT = re.compile(r"正しいもの|適切なもの")

def main():
    thr = float(_ARG[0]) if _ARG else 0.34
    txt = {s: C.notes_text(s) for s in C.SUBJ}
    out, n_stmt = [], 0
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
            if "年度" not in src or "自作" in src or "選択式" in src:
                continue
            ch = [str(x) for x in (q.get("choices") or [])]
            a = q.get("a")
            if len(ch) < 4 or not isinstance(a, int) or not (0 <= a < len(ch)):
                continue
            stem = str(q.get("q") or q.get("stem") or "")
            if WRONG.search(stem):
                good = [c for i, c in enumerate(ch) if i != a]
            elif RIGHT.search(stem):
                good = [ch[a]]
            else:
                continue                      # 個数・組合せは正誤を切り分けられない
            frame = next((k for k in FRAME if k in src or k in m.group(1)), None)
            if not frame:
                continue
            hay = "".join(txt[x] for x in FRAME[frame])
            for c in good:
                ws = sorted(set(WORD.findall(re.sub(r"\s+", "", c))))
                if len(ws) < 6:
                    continue
                n_stmt += 1
                hit = sum(1 for w in ws if w in hay)
                r = hit / len(ws)
                if r <= thr:
                    out.append((r, hit, len(ws), src, re.sub(r"\s+", "", c),
                                [w for w in ws if w not in hay]))
    out.sort(key=lambda x: x[0])
    print(f"正しい肢 {n_stmt}件 / 語の{int(thr*100)}%以下しか資料に無いもの {len(out)}件\n")
    for r, hit, tot, src, c, ng in out[:40]:
        print(f"[{r*100:4.0f}% {hit}/{tot}] {src[:30]}\n   {c[:118]}\n   資料に無い語: {'、'.join(ng[:9])}\n")

if __name__ == "__main__":
    main()
