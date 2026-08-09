#!/usr/bin/env python3
"""過去問で問われた条文が資料に載っているかを科目ごとに突き合わせる。

本試験の問題文には「労働基準法第32条の2」「法第7条」のように根拠条文が
書かれていることが多い。そこを拾って、資料側に同じ条の記載があるかを見る。

条番号の誤検出を避けるため、拾った条が実在するかを e-Gov の法令XMLで
確かめる。「民法第623条」を労基法の条と取り違える類の事故を防ぐ。
資料に条番号が無くても論点として扱っていることはあるので、最後は人が
目で確かめる前提の候補出しとして使う。
"""
import re, json, glob, os, sys, collections
import xml.etree.ElementTree as ET

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA   = os.path.join(ROOT, "drill", "data")
NOTES  = os.path.join(ROOT, "notes")
HOUREI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hourei")

# gen_anaume2 は読み込むだけで生成処理が走るので、LAWS の定義だけを取り出す
import ast
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_anaume2.py"),
            encoding="utf-8").read()
LAWS = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})", _src, re.S).group(1))

# ── 科目 → 主法令・資料の接頭辞 ─────────────────────────────
SUBJ = {
  "労基": dict(law="労働基準法",           note="01-労働基準法.md",     pre=("B", "C")),
  "安衛": dict(law="労働安全衛生法",       note="02-労働安全衛生法.md", pre=("D",)),
  "労災": dict(law="労働者災害補償保険法", note="03-労災保険法.md",     pre=("E",)),
  "雇用": dict(law="雇用保険法",           note="04-雇用保険法.md",     pre=("F",)),
  "徴収": dict(law="労働保険徴収法",       note="05-徴収法.md",         pre=("G",)),
  # 一般常識は出題側で労一・社一の切り分けが曖昧なため、両方の深掘りを共有する
  "労一": dict(law=None,                   note="06-労働一般常識.md",   pre=("H", "I")),
  "社一": dict(law=None,                   note="07-社会保険一般常識.md", pre=("I", "H")),
  "健保": dict(law="健康保険法",           note="08-健康保険法.md",     pre=("J",)),
  "国年": dict(law="国民年金法",           note="09-国民年金法.md",     pre=("K",)),
  "厚年": dict(law="厚生年金保険法",       note="10-厚生年金保険法.md", pre=("L",)),
}

# 資料をまたいで参照される横断ページ。条番号の有無はここも見る。
CROSS = ["90-横断整理.md", "91-数値暗記.md", "93-判例.md", "96-得点源リスト.md",
         "97-引っかけの型.md", "95-条文素読（選択式の原文）.md", "A0-正文集（択一の正しい肢）.md",
         "00-法改正-令和8年度.md"]

# ── 法令名の言い換え ─────────────────────────────────────────
ALIAS = {
  "労基法": "労働基準法", "安衛法": "労働安全衛生法", "労災法": "労働者災害補償保険法",
  "労災保険法": "労働者災害補償保険法", "徴収法": "労働保険徴収法",
  "労働保険の保険料の徴収等に関する法律": "労働保険徴収法",
  "健保法": "健康保険法", "厚年法": "厚生年金保険法", "国年法": "国民年金法",
  "労契法": "労働契約法", "均等法": "男女雇用機会均等法", "派遣法": "労働者派遣法",
  "高年法": "高年齢者雇用安定法", "社労士法": "社会保険労務士法",
  "育介法": "育児・介護休業法", "パート・有期法": "パートタイム・有期雇用労働法",
  "最賃法": "最低賃金法", "国保法": "国民健康保険法", "介保法": "介護保険法",
}
KNOWN = set(LAWS.values()) | set(ALIAS) | {"民法", "日本国憲法", "憲法", "刑法", "会社法",
                                           "行政不服審査法", "行政事件訴訟法", "税法", "所得税法"}

def resolve(raw):
    """拾った文字列の末尾から、知っている法令名の最長一致を取り出す。
       「使用者による労働基準法」→「労働基準法」のように余計な前置きを落とす。"""
    raw = raw.strip()
    best = None
    for k in KNOWN:
        if raw.endswith(k) and (best is None or len(k) > len(best)):
            best = k
    if best is None:
        return None
    return ALIAS.get(best, best)

# ── 実在する条のあつまり（法令XMLから）────────────────────────
_ARTS = {}
def arts_of(law):
    """法令名 → 実在する条ラベルの集合。XMLが無ければ None。"""
    if law in _ARTS:
        return _ARTS[law]
    lid = next((k for k, v in LAWS.items() if v == law), None)
    p = os.path.join(HOUREI, f"{lid}.xml") if lid else None
    if not p or not os.path.exists(p):
        _ARTS[law] = None
        return None
    got = set()
    for a in ET.parse(p).getroot().iter("Article"):
        num = a.get("Num", "")
        parts = num.split("_")
        if not parts[0].isdigit():
            continue
        lab = f"第{int(parts[0])}条"
        if len(parts) > 1 and parts[1].isdigit():
            lab += f"の{int(parts[1])}"
        got.add(lab)
    _ARTS[law] = got
    return got

# ── 過去問の読み込み ─────────────────────────────────────────
Z2H = str.maketrans("０１２３４５６７８９", "0123456789")
CITE = re.compile(r"(?:([一-鿿ぁ-んァ-ヴ・]{1,24}?(?:法|規則|令|憲法))\s*)?"
                  r"第\s*([0-9０-９]{1,3})\s*条(?:\s*の\s*([0-9０-９]{1,2}))?")

def subj_of(src):
    """出題元の表記から科目を決める。労災・雇用の択一 問8〜10 は徴収。"""
    if "労基安衛" in src:
        return ["労基", "安衛"]
    m = re.search(r"(労災|雇用)\s*択一\s*問(\d+)", src)
    if m:
        return ["徴収"] if int(m.group(2)) >= 8 else [m.group(1)]
    for k in ("労災", "雇用", "徴収", "労一", "社一", "健保", "国年", "厚年"):
        if k in src:
            return [k]
    if "一般常識" in src:
        return ["労一", "社一"]
    return []

def load_questions():
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "kako-*.js"))):
        s = open(f, encoding="utf-8").read()
        arr = json.loads(s[s.index("["):s.rindex("]") + 1])
        for q in arr:
            src = q.get("src", "")
            ss = subj_of(src)
            if not ss:
                continue
            body = " ".join(str(q.get(k, "")) for k in ("q", "head", "tail", "stem"))
            body += " " + " ".join(str(c) for c in (q.get("choices") or []))
            out.append((ss, src, body))
    return out

def cites(text, default_law):
    """本文から (法令名, 条ラベル) を拾う。実在しない条は捨てる。"""
    got, last = set(), default_law
    for m in CITE.finditer(text):
        raw, art, sub = m.group(1), m.group(2).translate(Z2H), m.group(3)
        if raw:
            if raw.strip() in ("同法", "本法", "この法", "当該法"):
                name = last
            else:
                name = resolve(raw)
                if name:
                    last = name
        else:
            name = last
        if not name:
            continue
        lab = f"第{int(art)}条" + (f"の{int(sub.translate(Z2H))}" if sub else "")
        real = arts_of(name)
        if real is not None and lab not in real:
            continue                       # その法律に存在しない条 → 拾い間違い
        got.add((name, lab))
    return got

# ── 資料側 ───────────────────────────────────────────────────
def notes_files(subj):
    d = SUBJ[subj]
    fs = [d["note"]]
    for p in sorted(glob.glob(os.path.join(NOTES, "*.md"))):
        b = os.path.basename(p)
        if re.match(r"^[" + "".join(d["pre"]) + r"]\d-", b):
            fs.append(b)
    return fs

def notes_text(subj, cross=True):
    fs = notes_files(subj) + (CROSS if cross else [])
    buf = []
    for n in fs:
        p = os.path.join(NOTES, n)
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read()
            # 自動生成の「出題傾向」節は、出題された条をそのまま並べている。
            # これを数に入れると、解説が無くても「載っている」ことになってしまう。
            t = re.sub(r"<!-- TREND:BEGIN -->.*?<!-- TREND:END -->", "", t, flags=re.S)
            buf.append(t)
    return "\n".join(buf)

def arts_in(text):
    """資料に出てくる条番号。「56条〜64条」のような範囲表記は間を埋める。"""
    got = set()
    for m in re.finditer(r"第?\s*([0-9]{1,3})\s*条(?:\s*の\s*([0-9]{1,2}))?", text):
        got.add(f"第{int(m.group(1))}条" + (f"の{int(m.group(2))}" if m.group(2) else ""))
    for m in re.finditer(r"第?\s*([0-9]{1,3})\s*条(?:の([0-9]{1,2}))?\s*[〜～~－ー-]\s*"
                         r"第?\s*([0-9]{1,3})\s*条", text):
        a, b = int(m.group(1)), int(m.group(3))
        if 0 < b - a < 60:
            for i in range(a, b + 1):
                got.add(f"第{i}条")
                for j in range(1, 30):        # 枝番も範囲に含まれるとみなす
                    got.add(f"第{i}条の{j}")
    return got


# ── 「触れているだけ」を見分ける ────────────────────────────
# 条番号がどこかに1回出てくるだけでも「資料にある」と数えてしまうと、
# 解説が無い論点を見逃す。実際、寄宿舎（96条）は自動生成の傾向表に
# 条番号が載っていたせいで、解説が無いまま素通りしていた。
_CAPS = {}
def captions(law):
    if law in _CAPS:
        return _CAPS[law]
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
            cap = a.find("ArticleCaption")
            if lab not in out and cap is not None:
                out[lab] = re.sub(r"[（）]", "", "".join(cap.itertext()).strip())
    _CAPS[law] = out
    return out

def art_re(lab):
    """「第32条の2」と「32条の2」の両方に当たり、「32条」だけには当たらない。"""
    m = re.match(r"第(\d+)条(?:の(\d+))?$", lab)
    a, b = m.group(1), m.group(2)
    return re.compile(r"第?\s*" + a + r"\s*条" +
                      (r"\s*の\s*" + b if b else r"(?!\s*の\s*\d)"))

def thin_ones(subj, per):
    """出題2回以上なのに、資料での扱いが1回の言及だけのものを挙げる。"""
    law = SUBJ[subj]["law"]
    if not law:
        return []
    txt = notes_text(subj)
    heads = "\n".join(re.findall(r"^#{2,4} .+$", txt, re.M))
    caps = captions(law)
    out = []
    for (lw, lab), n in per.items():
        if lw != law or n < 2:
            continue
        rx = art_re(lab)
        hits = len(rx.findall(txt))
        cap = caps.get(lab, "")
        if hits == 0:
            out.append((lab, cap, n)); continue
        if hits >= 2 or rx.search(heads) or (len(cap) >= 3 and cap in txt):
            continue
        # 1回しか出てこなくても、比較表や一覧の中で扱っていることがある。
        # その行に十分な説明があれば、触れているだけとは言えない。
        m = rx.search(txt)
        i = txt.rfind("\n", 0, m.start()) + 1
        j = txt.find("\n", m.end())
        line = txt[i: j if j > 0 else len(txt)]
        if len(re.sub(r"[\s*`>|#-]", "", line)) >= 40:
            continue
        out.append((lab, cap, n))
    return sorted(out, key=lambda x: -x[2])

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    per = collections.defaultdict(collections.Counter)
    for ss, src, body in load_questions():
        for s in ss:
            for key in cites(body, SUBJ[s]["law"]):
                per[s][key] += 1

    total = 0
    for s in SUBJ:
        if only and s != only:
            continue
        txt  = notes_text(s)
        have = arts_in(txt)
        rows = []
        for (lw, lab), n in per[s].items():
            # 主法令のほか、その科目で出る関係法令も対象にする
            rows.append((lw, lab, n))
        main_law = SUBJ[s]["law"]
        own = [(lw, lab, n) for lw, lab, n in rows if not main_law or lw == main_law]
        gap = sorted([(lw, lab, n) for lw, lab, n in own if lab not in have],
                     key=lambda x: (-x[2], int(re.match(r"第(\d+)条", x[1]).group(1))))
        print(f"\n══ {s}（{main_law or '複数法令'}）　資料 {len(notes_files(s))}件")
        print(f"   出題実績のある条 {len(own)}件 / 資料に無い {len(gap)}件")
        if gap:
            print("   " + "、".join(f"{lw if not main_law else ''}{lab}({n})" for lw, lab, n in gap[:30]))
        if not main_law:
            c = collections.Counter()
            for lw, lab, n in rows:
                c[lw] += n
            print("   出題の多い法令: " + "、".join(f"{k}{v}" for k, v in c.most_common(10)))
        total += len(gap)
    print(f"\n合計 資料に無い条 {total}件")

    # 条番号は出てくるが、解説が見当たらないもの
    thin = 0
    for s2 in SUBJ:
        if only and s2 != only:
            continue
        rows = thin_ones(s2, per[s2])
        if rows:
            thin += len(rows)
            print(f"\n── {s2}　解説が見当たらない条 {len(rows)}件")
            for lab, cap, n in rows[:8]:
                print(f"   {lab} {cap or '（見出しなし）'}（出題{n}回）")
    print(f"\n合計 解説が見当たらない条 {thin}件")

if __name__ == "__main__":
    main()
