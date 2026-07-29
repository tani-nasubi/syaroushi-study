#!/usr/bin/env python3
"""条番号ではなく「中身」で資料の漏れを探す。

cover_all.py は問題文に書かれた根拠条文を突き合わせるが、条文を挙げずに
論点だけ問う出題も多い。ここでは次の3つを見る。

  1. 選択式の正答語（空欄に入った語）が資料に載っているか
  2. 過去問に出た判例名が資料にあるか
  3. 択一の設問文に頻出する用語が資料にあるか
"""
import os, re, json, glob, ast, collections, sys, unicodedata

HERE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(HERE)
DATA  = os.path.join(ROOT, "drill", "data")
NOTES = os.path.join(ROOT, "notes")

DOCS = {os.path.basename(p): open(p, encoding="utf-8").read()
        for p in sorted(glob.glob(os.path.join(NOTES, "*.md")))}
ALL  = "\n".join(DOCS.values())
FLAT = re.sub(r"[\s*`>|\-#]", "", ALL)      # 記号を落として素の文字列にする
# 「労災保険の暫定任意適用事業」と「労災保険暫定任意適用事業」を同じとみなすため、
# 助詞・接続詞を落とした版も作る
def loose(t):
    return re.sub(r"(の|及び|又は|並びに|若しくは|に係る|における|、|・)", "", t)
LOOSE = loose(FLAT)

def norm(t):
    """全角と読点のゆれをならす。資料は半角、本試験PDFは全角で書かれる。"""
    return re.sub(r"[、，．・,\.\s　]", "", unicodedata.normalize("NFKC", t))
NORM = norm(FLAT)

sys.path.insert(0, HERE)
from cover_all import subj_of, SUBJ, notes_text     # 科目の判定を共有する

def load():
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "kako-*.js"))):
        s = open(f, encoding="utf-8").read()
        for q in json.loads(s[s.index("["):s.rindex("]") + 1]):
            out.append(q)
    return out

QS = load()

# ── 1. 選択式の正答語 ────────────────────────────────────────
def v_sel():
    miss, tot = [], 0
    for q in QS:
        if q.get("type") != "sel20":
            continue
        ch = q.get("choices") or []
        for a in (q.get("a") or []):          # a は正答の選択肢の添字（0始まり）
            if not (isinstance(a, int) and 0 <= a < len(ch)):
                continue
            w = re.sub(r"[\s　]", "", str(ch[a]))
            if len(w) < 2:
                continue
            tot += 1
            # 長い文の空欄は語ではなく判示なので、判示の核だけを見る
            if len(w) > 14:          # 長い空欄は判示そのもの。語の照合には向かない
                continue
            if norm(w) not in NORM:
                miss.append((q.get("src", ""), w))
    return tot, miss

# ── 2. 判例名 ────────────────────────────────────────────────
def v_jirei():
    """本試験は事件名を書かず事案を説明する。判示が問われた選択式について、
       その判示の核となる語句が資料にあるかを見る。"""
    miss, tot = [], 0
    for q in QS:
        if q.get("type") != "sel20":
            continue
        body = str(q.get("q", ""))
        if "最高裁判所" not in body:
            continue
        tot += 1
        # 「〜事件」と書かれていれば資料側にあるか確かめる
        for m in re.finditer(r"[一-鿿ァ-ヴA-Za-z0-9]{2,16}事件", body):
            if m.group(0) not in FLAT and "本問" not in m.group(0):
                miss.append((q.get("src", ""), m.group(0)))
    return tot, miss

# ── 3. 択一に頻出する用語 ────────────────────────────────────
# 制度名らしい2〜12字の漢字語を拾い、資料に出てこないものを挙げる
TERM = re.compile(r"[一-鿿]{3,12}")
NOISE = set("""場合 規定 とき 労働者 使用者 事業主 被保険者 保険者 厚生労働大臣 厚生労働省令
政令 当該 前項 次項 各号 前条 本条 期間 日数 金額 支給 支払 事業場 事業所 都道府県労働局長
所轄労働基準監督署長 公共職業安定所長 市町村長 内容 方法 事項 必要 以上 以下 未満 以内
問題 記述 正しい 誤っている 選択 解答 空欄 本問 出題 試験""".split())
def v_term():
    cnt = collections.Counter()
    for q in QS:
        body = " ".join(str(q.get(k, "")) for k in ("q", "head", "tail", "stem"))
        body += " " + " ".join(str(c) for c in (q.get("choices") or []))
        for m in TERM.finditer(body):
            t = m.group(0)
            # 「当該〜」「〜及」「〜又」は文中の切れ目であって用語ではない
            t = re.sub(r"^(当該|同一|前記|上記|本件)", "", t)
            t = re.sub(r"(及|又|若|並|並び)$", "", t)
            if t in NOISE or len(t) < 4:
                continue
            cnt[t] += 1
    miss = [(t, n) for t, n in cnt.items()
            if n >= 4 and t not in FLAT and loose(t) not in LOOSE]
    return len(cnt), sorted(miss, key=lambda x: -x[1])

def main():
    tot, miss = v_sel()
    print(f"\n══ 選択式の正答語　{tot}語 / 資料に無い {len(miss)}語")
    for src, w in miss[:25]:
        print(f"   {w}　（{src[:34]}）")
    if len(miss) > 25:
        print(f"   … 他{len(miss)-25}語")

    n, miss = v_jirei()
    print(f"\n══ 判例が題材の選択式　{n}問 / 事件名が資料に無い {len(miss)}件")
    for src, k in miss[:25]:
        print(f"   {k}　（{src[:34]}）")
    if len(miss) > 25:
        print(f"   … 他{len(miss)-25}件")

    n, miss = v_term()
    print(f"\n══ 択一の頻出用語（4回以上）　{n}語 / 資料に無い {len(miss)}語")
    for t, c in miss[:35]:
        print(f"   {t}×{c}")
    if len(miss) > 35:
        print(f"   … 他{len(miss)-35}語")

if __name__ == "__main__":
    main()
