#!/usr/bin/env python3
"""科目をまたぐ食い違いと、改正の反映漏れを探す。

同じ論点を別々の資料に書くと数字がずれる。深掘りページを全科目に広げた
あとはとくに起きやすいので、横断で照合する。
"""
import os, re, glob, collections

NOTES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notes")
DOCS = {os.path.basename(p): open(p, encoding="utf-8").read()
        for p in sorted(glob.glob(os.path.join(NOTES, "*.md")))}

hits = collections.defaultdict(list)
def bad(n, m): hits[n].append(m)

# ── 1. 同じ論点の数値が資料間でずれていないか ───────────────
#    (論点, 拾う正規表現, 正しい値)
NUM = [
 ("延滞金（健保・厚年・国年）", r"年\*{0,2}(14[\.．]6)\*{0,2}[％%]?", {"14.6"}),
 ("督促状の指定期限",           r"発する日から起算して\*{0,2}(\d+)日以上", {"10"}),
 ("傷病手当金の支給期間",       r"通算して\*{0,2}(1年6か月)", {"1年6か月"}),
 ("介護休業の通算日数",         r"1人につき\*{0,2}通算\*{0,2}(\d+)日", {"93"}),
 ("障害等級 年金と一時金の境",   r"第?\*{0,2}(1級〜7級|7級)\*{0,2}", {"1級〜7級", "7級"}),
 ("遺族補償一時金の日数",       r"給付基礎日額の\*{0,2}([\d,]+)日分\*{0,2}[^。]{0,6}(?:を支給|です)", None),
 ("厚年の保険料率",             r"1000分の\*{0,2}(183(?:\.00)?)", {"183", "183.00"}),
 ("健保の標準賞与額の上限",     r"年度[^。]{0,12}(573)万円", {"573"}),
 ("厚年の標準賞与額の上限",     r"1回につき\*{0,2}(150)万円", {"150"}),
 ("出産育児一時金",             r"出産育児一時金[^。]{0,40}?(\d{2})万円", {"50"}),
 ("埋葬料",                     r"埋葬料[^。]{0,30}?(\d)万円", {"5"}),
 ("繰上げの減額率",             r"1月あたり\*{0,2}(0\.4)[％%]", {"0.4"}),
 ("繰下げの増額率",             r"1月あたり\*{0,2}(0\.7)[％%]", {"0.7"}),
 ("特別加入の給付基礎日額",     r"給付基礎日額[^。]{0,30}?([\d,]+)円〜[\d,]+円", {"3,500"}),
]
def v_num():
    for label, rx, want in NUM:
        seen = collections.defaultdict(list)
        for f, s in DOCS.items():
            for m in re.finditer(rx, s):
                seen[m.group(1).replace("．", ".")].append(f)
        if want is not None:
            for v, fs in seen.items():
                if v not in want:
                    bad(1, f"{label}: 「{v}」が {sorted(set(fs))[:3]} にある（想定 {sorted(want)}）")
        elif len(seen) > 1:
            bad(1, f"{label}: 値が割れている {dict((k, sorted(set(v))[:2]) for k, v in seen.items())}")

# ── 2. 改正前の記述が残っていないか ─────────────────────────
STALE = [
 ("自己都合の給付制限2か月", r"自己都合[^。]{0,30}2か月(?!→|から|、従来)"),
 ("高年齢雇用継続給付15%",   r"高年齢雇用継続[^。]{0,40}15[％%](?!→|から|。令和7年3月)"),
 ("就業手当が現存する書き方", r"就業手当(?![はをのが]?\*{0,2}(?:は)?\*{0,2}令和7年4月1日に廃止|・|）)"),
 # 遺族基礎年金・寡婦年金の要件は25年のままなので、老齢の受給資格期間だけを見る
 ("受給資格期間25年（老齢）", r"老齢基礎年金の受給資格期間[^。]{0,20}25年"),
 ("障害者の法定雇用率2.3%",   r"法定雇用率[^。]{0,20}2\.3[％%]"),
 ("特定適用事業所100人超",   r"特定適用事業所[^。]{0,30}100人"),
 ("在職老齢年金28万円",       r"(?:支給停止調整額|在職老齢年金)[^。]{0,30}28万円"),
 ("労働契約法20条が現存",     r"労働契約法(?:第)?20条(?!（|は|の規定は、平成|は削除|は、平成|により不合理)"),
]
# 改正前後を並べて書いている箇所は指摘しない
CONTRAST = re.compile(r"従来|→|改正前|まで|廃止|引下げ|引上げ|創設|以前|旧")
def v_stale():
    for label, rx in STALE:
        for f, s in DOCS.items():
            if f in ("00-法改正-令和8年度.md", "95-条文素読（選択式の原文）.md",
                     "A0-正文集（択一の正しい肢）.md"):
                continue          # 改正まとめと本試験原文はそのままにしておく
            for m in re.finditer(rx, s):
                ctx = s[max(0, m.start()-40):m.end()+40]
                if CONTRAST.search(ctx):
                    continue
                bad(2, f"{label}: {f} … {ctx}".replace("\n", " "))

# ── 3. 深掘りページの相互リンク ──────────────────────────────
def v_link():
    deep = [f for f in DOCS if re.match(r"^[B-L]\d-", f)]
    for f in deep:
        s = DOCS[f]
        n = len(re.findall(r"\]\([^)]+\.md\)", s))
        if n < 3:
            bad(3, f"リンクが少ない {f}（{n}本）")

# ── 4. 同じ見出しの重複（コピー時の取り違え）─────────────────
# 年度ごとに同じ見出しが並ぶ資料は設計どおり
DUPOK = {"95-条文素読（選択式の原文）.md", "A0-正文集（択一の正しい肢）.md",
         "96-得点源リスト.md", "97-引っかけの型.md", "91-数値暗記.md"}
def v_dup():
    for f, s in DOCS.items():
        if f in DUPOK:
            continue
        heads = re.findall(r"^#{2,4} (.+)$", s, re.M)
        c = collections.Counter(heads)
        for h, n in c.items():
            if n > 1:
                bad(4, f"同じ見出しが{n}回 {f}: {h[:40]}")

# ── 5. 深掘りページの科目と内容が合っているか ────────────────
OWNER = {"B": "労働基準法", "C": "労働基準法", "D": "労働安全衛生法",
         "E": "労災", "F": "雇用保険", "G": "徴収", "H": "労働", "I": "社会保険",
         "J": "健康保険", "K": "国民年金", "L": "厚生年金"}
FOOTLINK = {"B": "01-労働基準法.md", "C": "01-労働基準法.md", "D": "02-労働安全衛生法.md",
            "E": "03-労災保険法.md", "F": "04-雇用保険法.md", "G": "05-徴収法.md",
            "H": "06-労働一般常識.md", "I": "07-社会保険一般常識.md",
            "J": "08-健康保険法.md", "K": "09-国民年金法.md", "L": "10-厚生年金保険法.md"}
def v_owner():
    for f, s in DOCS.items():
        if not re.match(r"^[B-L]\d-", f):
            continue
        want = FOOTLINK[f[0]]
        if want not in s:
            bad(5, f"科目の本体へ戻れない {f}（{want} へのリンクなし）")

TITLES = ["科目間の数値の食い違い", "改正前の記述", "深掘りページのリンク",
          "見出しの重複", "科目の対応"]

def main():
    for fn in (v_num, v_stale, v_link, v_dup, v_owner):
        fn()
    ng = 0
    for i, t in enumerate(TITLES, 1):
        h = hits[i]
        print(f"【{i}】{t}　{'■ ' + str(len(h)) + '件' if h else 'OK'}")
        for m in h[:10]:
            print("     " + m)
        if len(h) > 10:
            print(f"     … 他{len(h)-10}件")
        ng += bool(h)
    print(f"\n要改善: {ng}観点 / 指摘 {sum(len(v) for v in hits.values())}件")

if __name__ == "__main__":
    main()
