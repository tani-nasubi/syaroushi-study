#!/usr/bin/env python3
"""本試験の全設問を、年度・科目ごとに資料と突き合わせて抜けを洗い出す。

観点を1つずつ足していくやり方だと取りこぼす。年度ごとに区切って語を
拾うと、9年分をまとめたときには埋もれる語が浮かぶ（令和7年度で
「介護支援専門員」が見つかったのがこの形）。それを全年度に広げる。
"""
import json, re, os, sys, collections, unicodedata

M = json.load(open("mondai.json"))
NOTES_DIR = "../notes"
def notes_text():
    s = "".join(open(os.path.join(NOTES_DIR, f), encoding="utf-8").read()
                for f in sorted(os.listdir(NOTES_DIR)) if f.endswith(".md"))
    s = re.sub(r"<!-- TREND:BEGIN -->.*?<!-- TREND:END -->", "", s, flags=re.S)
    return unicodedata.normalize("NFKC", re.sub(r"[\s*`>|#]", "", s))
FLAT = notes_text()
# 法令XMLに出てくる語だけを「制度用語」とみなす。設問の地の文
#（「勤務先会社」「日常業務」など作問者が書いた説明）を落とすため。
def law_vocab():
    import xml.etree.ElementTree as ET, ast, glob
    src = open("gen_anaume2.py", encoding="utf-8").read()
    laws = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})", src, re.S).group(1))
    buf = []
    for lid in laws:
        p = os.path.join("hourei", lid + ".xml")
        if os.path.exists(p):
            buf.append("".join(ET.parse(p).getroot().itertext()))
    return unicodedata.normalize("NFKC", re.sub(r"\s+", "", "".join(buf)))
LAWTEXT = law_vocab()
LOOSE = re.sub(r"(の|及び|又は|並びに|若しくは|に係る|における|等|、|・)", "", FLAT)

# 設問の言い回しであって制度名ではないもの
NOISE = re.compile(
    r"^(当該|同条|同項|同法|同号|前条|前項|次項|各号|本問|上記|前記|以下|なお|ただし|"
    r"厚生労働省令|厚生労働大臣|都道府県|市町村|事業主|被保険者|労働者|使用者|保険者|"
    r"については|における|に関する|とされている|しなければ|することができ)")
TAIL = re.compile(r"(及|又|若|並|並び|等|の|に|は|が|を|で|と|も|し|する|され|られ)$")
HEAD = re.compile(r"^(当該|同一|前記|上記|本件|なお|また|その|この|次の)")

def terms(text):
    t = unicodedata.normalize("NFKC", re.sub(r"\s+", "", text))
    out = collections.Counter()
    for m in re.finditer(r"[一-鿿]{4,18}", t):
        w = HEAD.sub("", m.group(0))
        w = TAIL.sub("", w)
        if len(w) < 4 or NOISE.match(w):
            continue
        out[w] += 1
    # カタカナの制度名も拾う
    for m in re.finditer(r"[ァ-ヴー]{4,20}", t):
        out[m.group(0)] += 1
    return out

def missing(w):
    """資料に無いか。複合語の切れ目で拾った断片を落とすため、
       語をずらしながら部分一致も見る（「報酬支払基礎日数」は
       資料の「支払基礎日数」で足りている、と判断する）。"""
    lo = re.sub(r"(の|及び|又は|並びに|若しくは|に係る|における|等|、|・)", "", w)
    if w in FLAT or lo in LOOSE:
        return False
    # 語の一部（4字以上）が資料にあれば、扱いはあるとみなす
    for n in range(len(w) - 1, 3, -1):
        for i in range(0, len(w) - n + 1):
            if w[i:i + n] in FLAT:
                return False
    return True

def body_of(q):
    return (str(q.get("stem", "")) + str(q.get("body", "")) +
            "".join(map(str, q.get("choices", []) if isinstance(q.get("choices"), list) else [])))

def main():
    minn = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    found = collections.defaultdict(list)
    for kai, v in sorted(M.items(), key=lambda x: -int(x[0])):
        per = collections.defaultdict(collections.Counter)
        for q in v.get("takuitsu", []) + v.get("sentaku", []):
            per[str(q.get("subject", "?"))] += terms(body_of(q))
        for subj, c in per.items():
            for w, n in c.items():
                # 条文に出てこない語は、作問者が書いた地の文とみなす
                if n >= minn and w in LAWTEXT and missing(w):
                    found[w].append((kai, subj, n))
    rows = sorted(found.items(), key=lambda x: (-sum(t[2] for t in x[1]), x[0]))
    print(f"年度×科目で{minn}回以上出て資料に無い語: {len(rows)}件\n")
    for w, hits in rows[:60]:
        tot = sum(t[2] for t in hits)
        yrs = "/".join(sorted({f"第{k}回" for k, _, _ in hits}))[:34]
        sub = "/".join(sorted({s for _, s, _ in hits}))[:16]
        print(f"   {w:22} 計{tot:3d}　{sub}　{yrs}")

if __name__ == "__main__":
    main()
