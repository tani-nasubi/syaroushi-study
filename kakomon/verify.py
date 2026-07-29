#!/usr/bin/env python3
"""生成済みドリルデータを、原典PDFから独立に再解析した結果と突き合わせて検証する。

各ラウンドでランダムに問題を抽出し、次を確認する:
  1. 問題文・選択肢が、PDF抽出テキストに実在するか（捏造・欠落・混入の検出）
  2. 正答が、正答PDFを再解析した結果と一致するか
  3. 派生した肢別○×の正誤が、親設問の設問文（正しいものは/誤っているものは）と
     正答から論理的に導かれる値と一致するか
"""
import json, random, re, sys, collections
import parse_seitou, parse_mondai

SUB = parse_mondai.SUB
NOSP = lambda s: re.sub(r"[\s　]", "", s)


def norm(s):
    return NOSP(str(s).translate(SUB))


# ---- 原典（PDF抽出テキスト）を1本の文字列として読み込む ----
# ページ区切り・ページ番号・縦組みの脚注はPDF由来の体裁ノイズなので取り除く
# （load_lines が行うのはこの除去のみ。設問の分割・選択肢の切り出し・正答の対応付けと
#   いった、検証したいロジックは一切通していない）
RAW = {}
for kai in range(49, 58):
    for kind, suffix in [("takuitsu", "takuitusiki"), ("sentaku", "sentakusiki")]:
        RAW[(kai, kind)] = norm("".join(parse_mondai.load_lines(f"txt/{kai}-{suffix}.txt")))

# ---- 正答PDFを再解析（生成時とは別に、この場で解析し直す） ----
SEITOU = {k: parse_seitou.parse(f"pdf/{k}-kijyun-seitou.pdf") for k in range(49, 58)}

# ---- 生成済みJSデータを読み込む ----
def load_js():
    qs = []
    import glob, os
    for f in sorted(glob.glob("../drill/data/kako-*.js")):
        txt = open(f).read()
        body = txt[txt.index("[\n"): txt.rindex("]);") + 1]
        qs += json.loads(body)
    return qs


ALL = load_js()
BY_SRC = collections.defaultdict(list)
for q in ALL:
    BY_SRC[q["src"]].append(q)

SRC_RE = re.compile(r"第(\d+)回\) (\S+) (択一 問(\d+)|選択式)")
POS, NEG = parse_mondai.__dict__.get("POS"), parse_mondai.__dict__.get("NEG")
import gen_data
POS, NEG = gen_data.POS, gen_data.NEG


def check(q):
    """1問を検証し、問題があれば理由の一覧を返す。"""
    bad = []
    m = SRC_RE.search(q["src"])
    kai, subj = int(m.group(1)), m.group(2)
    kind = "sentaku" if m.group(3) == "選択式" else "takuitsu"
    raw = RAW[(kai, kind)]

    if q["type"] == "abc":
        if norm(q["q"])[:30] not in raw:
            bad.append("問題文が原典に存在しない")
        for i, c in enumerate(q["choices"]):
            if norm(c)[:25] not in raw:
                bad.append(f"肢{'ABCDE'[i]}が原典に存在しない")
        exp = SEITOU[kai]["takuitsu"][subj][int(m.group(4)) - 1]
        if q["a"] != exp:
            bad.append(f"正答不一致 生成={q['a']} 再解析={exp}")

    elif q["type"] in ("sel20", "selpb"):
        # 原典では空欄が全角ＡＢＣＤＥとして残っているため、単に【A】を除去すると
        # 前後が繋がって一致しなくなる。空欄で分割し、各断片の実在を確認する。
        for frag in re.split(r"【[A-E]】", q["q"]):
            f = norm(frag)
            if len(f) >= 10 and f[:30] not in raw:
                bad.append(f"本文の断片「{frag.strip()[:16]}」が原典に存在しない")
                break
        opts = q["choices"] if q["type"] == "sel20" else [c for g in q["groups"] for c in g]
        for c in opts:
            if c and norm(c)[:20] not in raw:
                bad.append(f"語群「{c[:14]}」が原典に存在しない")
        exp = [(v[0] if isinstance(v, list) else v) - 1 for v in SEITOU[kai]["sentaku"][subj]]
        if q["a"] != exp:
            bad.append(f"正答不一致 生成={q['a']} 再解析={exp}")
        if len(set(re.findall(r"【([A-E])】", q["q"]))) != 5:
            bad.append("空欄がA〜Eの5個でない")

    elif q["type"] == "ox":
        if norm(q["q"])[:25] not in raw:
            bad.append("肢が原典に存在しない")
        # 親設問を引き当てて、正誤が論理的に導かれるか確認
        psrc = q["src"].rsplit(" 肢", 1)[0]
        idx = "ABCDE".index(q["src"][-1])
        parent = next((x for x in BY_SRC[psrc] if x["type"] == "abc"), None)
        if parent is None:
            bad.append("親設問が見つからない")
        else:
            if parent["choices"][idx] != q["q"]:
                bad.append("親設問の肢と本文が一致しない")
            if POS.search(parent["q"]):
                want = (idx == parent["a"])
            elif NEG.search(parent["q"]):
                want = (idx != parent["a"])
            else:
                bad.append("正誤を確定できない設問から派生している"); want = None
            if want is not None and q["a"] != want:
                bad.append(f"○×不一致 生成={q['a']} 論理値={want}")
    return bad


if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    total_bad, checked = [], 0
    print(f"収録 {len(ALL)} 問から、{rounds}ラウンド × {per}問 を無作為抽出して原典と照合\n")
    for r in range(1, rounds + 1):
        random.seed(r * 7919)
        # 形式が偏らないよう層化抽出
        pools = {t: [q for q in ALL if q["type"] == t] for t in ("abc", "sel20", "selpb", "ox")}
        sample = []
        for t, w in (("abc", .4), ("sel20", .2), ("selpb", .05), ("ox", .35)):
            n = max(1, int(per * w))
            sample += random.sample(pools[t], min(n, len(pools[t])))
        bad = []
        for q in sample:
            e = check(q)
            if e:
                bad.append((q["src"], q["type"], e))
        checked += len(sample)
        total_bad += bad
        mark = "OK  " if not bad else "NG  "
        print(f"  round {r:2d}  {mark}{len(sample)}問検証 / 不一致 {len(bad)}件")
        for src, t, e in bad[:3]:
            print(f"           - [{t}] {src}: {'; '.join(e[:2])}")
    print(f"\n═══ 合計 {checked}問を検証 / 不一致 {len(total_bad)}件 ═══")
    if total_bad:
        kinds = collections.Counter(e for _, _, es in total_bad for e in es)
        for k, v in kinds.most_common(10):
            print(f"  {v:4d}  {k}")
        sys.exit(1)
    print("  すべて原典と一致")
