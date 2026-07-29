#!/usr/bin/env python3
"""科目別ノート（notes/*.md）を、本試験過去問9年分と突き合わせて改善点を洗い出す。

思いつきで「もっと書けそう」と言うのではなく、
「過去問で実際に問われているのにノートに無い」ものを機械的に見つける。
"""
import json, re, collections, os, sys

NOTES_DIR = "../notes"
MONDAI = json.load(open("mondai.json"))
SEITOU = json.load(open("seitou.json"))

# 過去問の科目 → 対応するノート
MAP = {
    "労基安衛": ["01-労働基準法.md", "02-労働安全衛生法.md"],
    "労災":     ["03-労災保険法.md", "05-徴収法.md"],
    "雇用":     ["04-雇用保険法.md", "05-徴収法.md"],
    "一般常識": ["06-労働一般常識.md", "07-社会保険一般常識.md"],
    "労一":     ["06-労働一般常識.md"],
    "社一":     ["07-社会保険一般常識.md"],
    "健保":     ["08-健康保険法.md"],
    "厚年":     ["10-厚生年金保険法.md"],
    "国年":     ["09-国民年金法.md"],
}
ALL_NOTES = sorted(f for f in os.listdir(NOTES_DIR) if f.endswith(".md"))
BODY = {f: open(f"{NOTES_DIR}/{f}").read() for f in ALL_NOTES}
NOSP = lambda s: re.sub(r"[\s　,，]", "", str(s))
FLAT = {f: NOSP(b) for f, b in BODY.items()}
SRC_RE = re.compile(r"第(\d+)回\)")

def note_text(subj):
    return "".join(FLAT[f] for f in MAP.get(subj, []))

# ---- 過去問の本文を科目別に集める ----
QS = collections.defaultdict(list)          # 科目 -> [問題テキスト]
SEL_ANS = collections.defaultdict(list)     # 科目 -> [(回, 空欄, 正答語)]
for kai, v in MONDAI.items():
    for q in v["takuitsu"]:
        QS[q["subject"]].append(q["stem"] + "".join(q["choices"]))
    for q in v["sentaku"]:
        QS[q["subject"]].append(q["body"] + "".join(
            q["choices"] if q["format"] == "pool20" else [c for g in q["choices"] for c in g]))
        raw = SEITOU[kai]["sentaku"][q["subject"]]
        for i, a in enumerate(raw):
            a = a[0] if isinstance(a, list) else a
            if a is None: continue
            word = (q["choices"][a-1] if q["format"] == "pool20"
                    else (q["choices"][i][a-1] if a-1 < len(q["choices"][i]) else ""))
            if word: SEL_ANS[q["subject"]].append((int(kai), "ABCDE"[i], word))

# 除外する一般語
STOP = set("""労働者使用者事業主被保険者厚生労働大臣厚生労働省令都道府県場合とき規定法律施行日本
第一第二第三次のうち記述正しい誤っているものどれかいくつあるか本問において以下同じ""")
TERM = re.compile(r"[一-鿿ヲ-ヴー]{3,12}")

def terms(texts, min_df=3):
    df = collections.Counter()
    for t in texts:
        for w in set(TERM.findall(NOSP(t))):
            if w in STOP or len(w) < 3: continue
            df[w] += 1
    return {w: c for w, c in df.items() if c >= min_df}

R = []
def report(n, title, lines, summary=""):
    R.append((n, title, lines))
    print(f"\n【{n:2d}】{title}")
    if summary: print(f"      {summary}")
    for l in lines[:14]: print("      " + l)
    if len(lines) > 14: print(f"      … 他 {len(lines)-14} 件")
    if not lines: print("      → 指摘なし")

print("═" * 74)
print(f" 科目別ノート レビュー（過去問 {sum(len(v) for v in QS.values())} 問と突き合わせ）")
print("═" * 74)

# 1 ─ 過去問で頻出なのにノートに無い用語
lines = []
for subj in ["労基安衛","労災","雇用","一般常識","健保","厚年","国年"]:
    nt = note_text(subj)
    miss = [(w,c) for w,c in sorted(terms(QS[subj]).items(), key=lambda x:-x[1]) if w not in nt]
    if miss: lines.append(f"{subj}：" + "、".join(f"{w}({c}問)" for w,c in miss[:8]))
report(1, "過去問で頻出（3問以上）なのにノートに無い用語", lines,
       "頻出用語の取りこぼし。多いほど加筆余地あり")

# 2 ─ 選択式の正答語がノートにあるか（最重要）
lines = []
for subj, arr in SEL_ANS.items():
    nt = note_text(subj)
    miss = [(k,b,w) for k,b,w in arr if len(NOSP(w)) >= 3 and NOSP(w) not in nt]
    if miss:
        lines.append(f"{subj}：{len(miss)}/{len(arr)}語が未収録 → " +
                     "、".join(f"「{w[:16]}」(第{k}回{b})" for k,b,w in miss[:4]))
report(2, "過去問・選択式で実際に正答となった語のうちノートに無いもの", lines,
       "選択式は基準点割れの主因。正答語の収録率が対策の質を左右する")

# 3 ─ 法改正論点が各科目ノートに反映されているか
kaisei = BODY["00-法改正-令和8年度.md"]
KEY = ["拘禁刑","教育訓練休暇給付金","出生後休業支援給付金","育児時短就業給付金","在職老齢年金",
       "支給停止調整額","えるぼし","カスタマーハラスメント","子ども・子育て支援金","柔軟な働き方",
       "子の看護等休暇","女性管理職比率","マクロ経済スライド","年金分割"]
lines = []
for k in KEY:
    where = [f for f in ALL_NOTES if f[:2] not in ("00","90","91") and NOSP(k) in FLAT[f]]
    if not where: lines.append(f"「{k}」… 科目別ノートに記載なし（法改正資料のみ）")
report(3, "令和8年度の改正キーワードが科目別ノートに落ちているか", lines,
       "法改正資料だけでなく、該当科目のノートにも書いてあるのが理想")

# 4 ─ 横断整理と各科目ノートで数値が食い違っていないか
NUM = re.compile(r"([一-鿿ァ-ヶー]{2,10})(?:は|＝|=|…)?\s*([0-9０-９]{1,4}(?:年|月|日|時間|人|円|％|分の[0-9]))")
cross = collections.defaultdict(set)
for m in NUM.finditer(NOSP(BODY["90-横断整理.md"])): cross[m.group(1)].add(m.group(2))
lines = []
for f in ALL_NOTES:
    if f[:2] in ("90","91"): continue
    for m in NUM.finditer(FLAT[f]):
        k, v = m.group(1), m.group(2)
        if k in cross and v not in cross[k] and len(cross[k]) == 1:
            lines.append(f"{f[:2]} 「{k}」= {v} ／ 横断整理では {list(cross[k])[0]}")
lines = sorted(set(lines))
report(4, "横断整理と科目別ノートで数値が食い違う箇所", lines,
       "同じ論点を2か所に書いているので、片方だけ直すと矛盾する")

# 5 ─ 過去問に出る判例がノートにあるか
HANREI = re.compile(r"([一-鿿ァ-ヶA-Za-z]{2,12})事件")
lines = []
for subj in QS:
    if subj not in MAP: continue
    nt = note_text(subj)
    names = collections.Counter(HANREI.findall(NOSP("".join(QS[subj]))))
    miss = [(n,c) for n,c in names.most_common() if n+"事件" not in nt and c >= 1]
    if miss: lines.append(f"{subj}：" + "、".join(f"{n}事件({c})" for n,c in miss[:6]))
report(5, "過去問で言及される判例のうちノートに無いもの", lines,
       "労基・労一は判例からの出題が多い")

# 6 ─ 条文番号の網羅（過去問が参照する条文）
ART = re.compile(r"第([0-9０-９]{1,3})条")
lines = []
for subj in ["労基安衛","労災","雇用","健保","厚年","国年"]:
    nt = note_text(subj)
    arts = collections.Counter(ART.findall(NOSP("".join(QS[subj]))))
    miss = [(a,c) for a,c in arts.most_common(40)
            if f"第{a}条" not in nt and f"{a}条" not in nt and c >= 4]
    if miss: lines.append(f"{subj}：" + "、".join(f"{a}条({c}回)" for a,c in miss[:8]))
report(6, "過去問が4回以上参照しているのに条番号が無い条文（表記ゆれ吸収後）", lines,
       "条番号があると選択式で条文を思い出しやすい")

# 7 ─ 直前チェックリストの分量
lines = []
for f in ALL_NOTES:
    if f[:2] in ("00","90","91"): continue
    n = len(re.findall(r"^- \[ \]", BODY[f], re.M))
    h2 = len(re.findall(r"^## ", BODY[f], re.M))
    if n == 0: lines.append(f"{f}：チェックリストなし")
    elif n < h2: lines.append(f"{f}：チェック{n}項目に対し節が{h2}個（節あたり1項目未満）")
report(7, "直前チェックリストが本文の分量に見合っているか", lines)

# 8 ─ 配点と分量のバランス
# 択一の配点 ＋ 選択式の配点（選択式は1科目でも割れると即不合格なので1.5倍に重み付け）
WEIGHT = {"01-労働基準法.md":7+2.5*1.5,"02-労働安全衛生法.md":3+2.5*1.5,
          "03-労災保険法.md":7+5*1.5,"04-雇用保険法.md":7+5*1.5,"05-徴収法.md":6.0,
          "06-労働一般常識.md":5+5*1.5,"07-社会保険一般常識.md":5+5*1.5,
          "08-健康保険法.md":10+5*1.5,"09-国民年金法.md":10+5*1.5,"10-厚生年金保険法.md":10+5*1.5}
tot_c = sum(len(BODY[f]) for f in WEIGHT); tot_w = sum(WEIGHT.values())
lines = []
for f, w in sorted(WEIGHT.items(), key=lambda x: len(BODY[x[0]])/x[1]):
    ratio = (len(BODY[f])/tot_c) / (w/tot_w)
    if ratio < 0.8: lines.append(f"{f}：配点{w}点に対し分量比 {ratio:.2f}（薄い）")
    elif ratio > 1.5: lines.append(f"{f}：配点{w}点に対し分量比 {ratio:.2f}（厚い）")
report(8, "配点（択一＋選択式×1.5）に対する分量バランス", lines,
       f"総字数 {tot_c:,}字／重み付け配点 {tot_w:.1f}")

# 9 ─ 数値暗記資料との連携
num_doc = FLAT["91-数値暗記.md"]
lines = []
for f in ALL_NOTES:
    if f[:2] in ("90","91"): continue
    warns = len(re.findall(r"⚠️", BODY[f]))
    if warns and "91-数値暗記" not in BODY[f]:
        lines.append(f"{f}：要確認マーク{warns}個あるが数値暗記資料へのリンクなし")
report(9, "要確認の数値がある科目から数値暗記資料へ誘導しているか", lines)

# 10 ─ ノート間の相互参照
lines = []
for f in ALL_NOTES:
    if f[:2] in ("00","90","91"): continue
    refs = len(re.findall(r"[0-9]{2}-[^\s`）)]+\.md", BODY[f]))
    if refs == 0: lines.append(f"{f}：他の資料への参照が0件")
report(10, "科目別ノートから横断整理・法改正資料への導線", lines,
       "科目を読んだあと横断整理に進む導線があると回転しやすい")

print("\n" + "═"*74)
n_issue = sum(1 for _,_,l in R if l)
print(f" 10観点中 {n_issue} 観点で改善余地あり（指摘 {sum(len(l) for _,_,l in R)} 件）")
print("═"*74)
