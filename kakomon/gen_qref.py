#!/usr/bin/env python3
"""解説のない過去問について、その肢の根拠になっている条を割り出す。

過去問には解説が付いていない（3,381問）。作り話を足すより、その肢が
基づいている条文の原文を見せるほうが確かめられる。割り出し方は2つ。

  1. 肢に「労働基準法第32条」と書かれていれば、それを採る
  2. 書かれていなければ、肢の文と条文本文を突き合わせ、16字以上そのまま
     一致する条を探す。誤り肢は条文の一語を書き換えて作られるので、
     書き換えられていない部分がそのまま残っている

  出力: ../drill/data/qref.js   { 問題ID: ["労働基準法第32条", ...] }
"""
import os, re, json, glob, ast, collections
import xml.etree.ElementTree as ET

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.dirname(HERE)
DATA   = os.path.join(ROOT, "drill", "data")
HOUREI = os.path.join(HERE, "hourei")
OUT    = os.path.join(DATA, "qref.js")
WIN    = 16          # 一致とみなす長さ
STRIDE = 4           # 肢の側をずらす幅

LAWS = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})",
        open(os.path.join(HERE, "gen_anaume2.py"), encoding="utf-8").read(), re.S).group(1))
ALIAS = {"労災保険法": "労働者災害補償保険法",
         "労働保険の保険料の徴収等に関する法律": "労働保険徴収法"}

# 出題枠 → 突き合わせる法令。関係のない法令まで見ると取り違える。
FRAME = {
 "労基安衛": ["労働基準法", "労働安全衛生法", "労働基準法施行規則", "労働安全衛生規則"],
 "労災":     ["労働者災害補償保険法", "労災保険法施行規則", "労働保険徴収法"],
 "雇用":     ["雇用保険法", "雇用保険法施行規則", "労働保険徴収法"],
 "徴収":     ["労働保険徴収法", "労働保険徴収法施行規則"],
 "一般常識": ["労働契約法", "労働組合法", "労働関係調整法", "最低賃金法", "労働者派遣法",
              "男女雇用機会均等法", "育児・介護休業法", "高年齢者雇用安定法",
              "障害者雇用促進法", "職業安定法", "労働施策総合推進法",
              "社会保険労務士法", "国民健康保険法", "介護保険法", "高齢者医療確保法",
              "確定拠出年金法", "確定給付企業年金法", "船員保険法", "児童手当法"],
 "健保":     ["健康保険法", "健康保険法施行規則"],
 "国年":     ["国民年金法", "国民年金法施行規則"],
 "厚年":     ["厚生年金保険法", "厚生年金保険法施行規則"],
}

_arts = {}
def arts_of(law):
    """法令名 → [(条ラベル, 本文)]。本則だけを見る。"""
    if law in _arts:
        return _arts[law]
    lid = next((k for k, v in LAWS.items() if v == law), None)
    p = os.path.join(HOUREI, f"{lid}.xml") if lid else None
    out = []
    if p and os.path.exists(p):
        root = ET.parse(p).getroot()
        main = root.find(".//MainProvision") or root
        for a in main.iter("Article"):
            q = a.get("Num", "").split(":")[0].split("_")
            if not q[0].isdigit():
                continue
            lab = f"第{int(q[0])}条" + (f"の{int(q[1])}" if len(q) > 1 and q[1].isdigit() else "")
            out.append((lab, norm("".join(a.itertext()))))
    _arts[law] = out
    return out

def norm(s):
    return re.sub(r"[\s　、。「」（）｢｣]", "", str(s))

CITE = re.compile(r"(?:([一-鿿ぁ-んァ-ヴ・]{2,20}?(?:法|規則|令))\s*)?"
                  r"第\s*([0-9０-９]{1,3})\s*条(?:\s*の\s*([0-9０-９]{1,2}))?")
Z = str.maketrans("０１２３４５６７８９", "0123456789")

def frame_of(src, subject):
    hay = f"{src} {subject}".replace("・", "")
    m = re.search(r"(労災|雇用)\s*択一\s*問\s*(\d+)", str(src))
    if m and int(m.group(2)) >= 8:
        return "徴収"
    for k in ("労基安衛", "一般常識", "労災", "雇用", "徴収", "健保", "国年", "厚年"):
        if k in hay:
            return k
    for k, v in (("労一", "一般常識"), ("社一", "一般常識")):
        if k in hay:
            return v
    return None

def exists(key):
    """「労働基準法第32条」が本則に実在するか。"""
    m = re.match(r"^(.+?)(第\d+条(?:の\d+)?)$", key)
    if not m:
        return False
    return any(lab == m.group(2) for lab, _ in arts_of(m.group(1)))

def by_citation(body, frame):
    """肢に書かれた条文をそのまま採る。名前が省かれたものは直前の法令とみなす。"""
    laws = FRAME.get(frame, [])
    last = laws[0] if laws else None
    out = []
    for m in CITE.finditer(body):
        if m.group(1):
            last = ALIAS.get(m.group(1), m.group(1))
        law = last
        if not law:
            continue
        key = f"{law}第{int(m.group(2).translate(Z))}条" + \
              (f"の{int(m.group(3).translate(Z))}" if m.group(3) else "")
        if key not in out and exists(key):
            out.append(key)
        if len(out) >= 3:
            break
    return out

def by_text(body, frame):
    """条文本文とそのまま一致する部分を探す。書き換えられていない所が残る。"""
    t = norm(body)
    if len(t) < WIN:
        return []
    wins = [t[i:i + WIN] for i in range(0, len(t) - WIN, STRIDE)]
    best, bestn = None, 0
    for law in FRAME.get(frame, []):
        for lab, art in arts_of(law):
            n = sum(1 for w in wins if w in art)
            if n > bestn:
                best, bestn = f"{law}{lab}", n
    return [best] if bestn >= 1 else []

def js_array(src):
    """コメントや引用符なしのキーが混じったJSの配列を、素朴に読む。"""
    t = re.sub(r"/\*.*?\*/", "", src, flags=re.S)          # ブロックコメント
    t = re.sub(r"(?m)^\s*//.*$", "", t)                     # 行コメント
    t = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', t)   # キーを引用符で囲む
    t = re.sub(r",(\s*[}\]])", r"\1", t)                    # 末尾のコンマ
    try:
        return json.loads(t)
    except Exception:
        return None

def main():
    ref, stat = {}, collections.Counter()
    for f in sorted(glob.glob(os.path.join(DATA, "*.js"))):
        s = open(f, encoding="utf-8").read()
        m = re.search(r'DRILL\.register\(\s*"([^"]+)"', s)
        if not m:
            continue
        subject = m.group(1)
        # 自作問題のファイルは JSON ではなく、コメント付きのJSリテラルで
        # 書かれている。ブラウザと同じ読み方をするため、生成側と同じ
        # 素朴な取り出しを使う（失敗したものは飛ばす）。
        tail = s[m.end():]
        try:
            arr = json.loads(tail[tail.index("["):tail.rindex("]") + 1])
        except Exception:
            arr = js_array(tail[tail.index("["):tail.rindex("]") + 1])
        if arr is None:
            continue
        for i, q in enumerate(arr):
            if q.get("type") == "ana" or q.get("exp"):
                continue
            stat["対象"] += 1
            frame = frame_of(q.get("src", ""), subject)
            if not frame:
                continue
            body = " ".join(str(q.get(k, "")) for k in ("q", "stem", "head", "tail"))
            body += " ".join(str(x) for x in (q.get("choices") or []))
            for g in (q.get("groups") or []):
                body += " ".join(map(str, g))
            keys = by_citation(body, frame)
            if keys:
                stat["条文の引用から"] += 1
            else:
                keys = by_text(body, frame)
                if keys:
                    stat["本文の一致から"] += 1
            if keys:
                ref[f"{subject}#{i}"] = keys
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("/* 問題 → 根拠の条。kakomon/gen_qref.py が条文XMLとの突き合わせで作る。 */\n")
        f.write("window.QREF = " + json.dumps(ref, ensure_ascii=False, indent=0) + ";\n")
    t = stat["対象"]
    print(f"→ {OUT}  {len(ref):,}問に根拠を付けた / {os.path.getsize(OUT):,} bytes")
    print(f"   解説のない問題 {t:,} のうち "
          f"引用から {stat['条文の引用から']:,}・本文の一致から {stat['本文の一致から']:,} "
          f"（合わせて {len(ref)/t*100:.0f}%）")

if __name__ == "__main__":
    main()
