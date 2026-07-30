#!/usr/bin/env python3
"""過去問9年分から抽出した出題傾向を、各科目ノートの冒頭に「出題傾向」節として挿入する。
すでに挿入済みの場合は最新の内容で置き換える。"""
import json, re, collections, os

MONDAI = json.load(open("mondai.json"))
SEITOU = json.load(open("seitou.json"))
NOTES = "../notes"
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))

def qtype(stem):
    s = NOSP(stem)
    if "いくつあるか" in s: return "個数問題"
    if "組合せ" in s: return "組合せ問題"
    if re.search(r"誤っているもの|誤りである", s): return "誤りを選ぶ"
    if re.search(r"正しいもの|適切なもの", s): return "正しいものを選ぶ"
    return "その他"

LAW = re.compile(r"(労働基準法|労働安全衛生法|労働者災害補償保険法|労災保険法|雇用保険法|"
                 r"労働保険の保険料の徴収等に関する法律|労働保険徴収法|健康保険法|厚生年金保険法|"
                 r"国民年金法|介護保険法|国民健康保険法|社会保険労務士法|労働契約法|労働組合法|"
                 r"最低賃金法|労働者派遣法|確定拠出年金法)(?:施行規則)?"
                 r"(?:第([0-9]{1,3})条(?:の([0-9]{1,2}))?)?")

D = collections.defaultdict(lambda: {"t":collections.Counter(),"a":collections.Counter(),"s":[],
                                     "y":collections.defaultdict(collections.Counter),
                                     "ay":collections.defaultdict(set)})
for kai, v in MONDAI.items():
    k = int(kai)
    for q in v["takuitsu"]:
        d = D[q["subject"]]
        d["t"][qtype(q["stem"])] += 1
        # 年度別の設問形式（傾向の推移を見るため）
        y = d["y"][k]; y[qtype(q["stem"])] += 1; y["問数"] += 1
        y["字数計"] += sum(len(NOSP(c)) for c in q["choices"])
        y["肢数"]  += len(q["choices"])
        if re.search(r"最高裁判所|判示|判例", NOSP(q["stem"] + "".join(q["choices"]))): y["判例"] += 1
        for m in LAW.finditer(NOSP(q["stem"] + "".join(q["choices"]))):
            if not m.group(2): continue
            key = f"{m.group(1)}{m.group(2)}条" + (f"の{m.group(3)}" if m.group(3) else "")
            d["a"][key] += 1
            d["ay"][key].add(k)          # どの回に出たかを覚えておく
    for q in v["sentaku"]:
        d = D[q["subject"]]
        body = NOSP(q["body"])
        laws = sorted({f"{m.group(1)}{m.group(2)}条" + (f"の{m.group(3)}" if m.group(3) else "")
                       for m in LAW.finditer(body) if m.group(2)})
        raw = SEITOU[kai]["sentaku"][q["subject"]]
        ws = []
        for i, a in enumerate(raw):
            a = a[0] if isinstance(a, list) else a
            if a is None: continue
            w = (q["choices"][a-1] if q["format"]=="pool20"
                 else (q["choices"][i][a-1] if a-1 < len(q["choices"][i]) else ""))
            if w: ws.append(re.sub(r"\s+", " ", w).strip())
        d["s"].append((k, laws[:3], ws))


# ── 条文の見出しと、読むべき深掘りページを引くための下ごしらえ ──────────
# 条番号だけ並べても何を読めばよいか分からないので、法令XMLから見出しを取り、
# その条をいちばん詳しく扱っている深掘りページへの導線を付ける。
import glob, ast
import xml.etree.ElementTree as ET

HOUREI = "hourei"
LAWS = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})",
        open("gen_anaume2.py", encoding="utf-8").read(), re.S).group(1))
ALIAS = {"労災保険法": "労働者災害補償保険法",
         "労働保険の保険料の徴収等に関する法律": "労働保険徴収法"}

_caption = {}
def captions(law):
    """法令名 → {条ラベル: 見出し}。見出しが無い条は空文字。"""
    law = ALIAS.get(law, law)
    if law in _caption:
        return _caption[law]
    lid = next((k for k, v in LAWS.items() if v == law), None)
    got = {}
    p = os.path.join(HOUREI, f"{lid}.xml") if lid else None
    if p and os.path.exists(p):
        for a in ET.parse(p).getroot().iter("Article"):
            q = a.get("Num", "").split(":")[0].split("_")
            if not q[0].isdigit():
                continue
            lab = f"第{int(q[0])}条" + (f"の{int(q[1])}" if len(q) > 1 and q[1].isdigit() else "")
            if lab in got:
                continue                    # 附則にも同じ番号があるので本則を優先する
            cap = a.find("ArticleCaption")
            # 条見出しがある条だけを「何を定めているか」に使う。無い条は空にして、
            # 深掘りページの表題や本体の節見出しで代えさせる（本文の書き出しは読みにくい）
            got[lab] = (re.sub(r"[（）]", "", "".join(cap.itertext()).strip())
                        if cap is not None else "")
    _caption[law] = got
    return got

# 深掘りページの接頭辞 → その科目
DEEP_PRE = {"01-労働基準法.md": ("B", "C"), "02-労働安全衛生法.md": ("D",),
            "03-労災保険法.md": ("E",), "04-雇用保険法.md": ("F",),
            "05-徴収法.md": ("G",),
            # 一般常識は労一・社一で法令が入り混じるので、両方の深掘りを見る
            "06-労働一般常識.md": ("H", "I"), "07-社会保険一般常識.md": ("I", "H"),
            "08-健康保険法.md": ("J",),
            "09-国民年金法.md": ("K",), "10-厚生年金保険法.md": ("L",)}

# 深掘りページの中で「◯条」の直前に出てくる、その科目以外の法令名
OTHERLAW = re.compile(
    r"(労働契約法|民法|労働組合法|労働関係調整法|労働施策総合推進法|男女雇用機会均等法|"
    r"育児・介護休業法|パートタイム・有期雇用労働法|高年齢者雇用安定法|障害者雇用促進法|"
    r"最低賃金法|労働者派遣法|職業安定法|労働審判法|賃金支払確保法|"
    r"労働基準法|労働安全衛生法|労災保険法|労働者災害補償保険法|雇用保険法|労働保険徴収法|"
    r"健康保険法|厚生年金保険法|国民年金法|国民健康保険法|介護保険法|高齢者医療確保法|"
    r"社会保険労務士法|船員保険法|確定拠出年金法|確定給付企業年金法|"
    r"安衛則|労基則|労災則|徴収則|則|施行規則|施行令|憲法)\s*(?:第)?$")
# 行や見出しのどこにあっても拾う版
OTHERLAW_ANY = re.compile(OTHERLAW.pattern.rstrip("$").replace(r"\s*(?:第)?", ""))

_deepmap, _headmap = {}, {}
def deep_head(note, page, lab):
    """指定した深掘りページの中で、その条を扱っている見出しを返す。"""
    deep_of(note)
    return _headmap.get(note, {}).get((page, lab), "")


def deep_of(note, ownlaw=None):
    """その科目の深掘りページを読み、条ラベル → (ページ, 表題, その条を扱う見出し) を返す。

    ページには他の法律の条番号も出てくる（労基の深掘りに労働契約法9条など）。
    その行や直前の見出しに別の法令名があるものは数えない。"""
    if note in _deepmap:
        return _deepmap[note]
    pres = DEEP_PRE.get(note, ())
    score = collections.defaultdict(collections.Counter)
    title, heading = {}, {}
    ART = re.compile(r"(?<![0-9])([0-9]{1,3})条(?:の([0-9]{1,2}))?")
    RANGE = re.compile(r"(?<![0-9])([0-9]{1,3})条(?:の[0-9]{1,2})?\s*[〜～~－ー-]\s*([0-9]{1,3})条")
    lab_of = lambda m: f"第{int(m.group(1))}条" + (f"の{int(m.group(2))}" if m.group(2) else "")

    def other(text):
        """その文字列に、この科目以外の法令名があるか。"""
        for mo in OTHERLAW_ANY.finditer(text):
            if ownlaw is None or mo.group(1) != ownlaw:
                return True
        return False

    for path in sorted(glob.glob(f"{NOTES}/*.md")):
        b = os.path.basename(path)
        if not (pres and b[0] in pres and re.match(r"^[A-Z]\d-", b)):
            continue
        body = open(path, encoding="utf-8").read()
        title[b] = re.sub(r"｜.*$", "", body.split("\n", 1)[0].lstrip("# ").strip())
        cur = ""
        for line in body.split("\n"):
            hm = re.match(r"^#{2,4} (.+)$", line)
            if hm:
                cur = re.sub(r"（[^）]*）\s*$", "", hm.group(1)).strip()
                if other(hm.group(1)):      # 別の法令についての見出しは数えない
                    cur = ""
                    continue
                # 見出し自体が条を挙げていれば、その見出しをその条の説明に使う
                for rg in RANGE.finditer(hm.group(1)):
                    a, z = int(rg.group(1)), int(rg.group(2))
                    if 0 < z - a < 40:
                        for i in range(a, z + 1):
                            heading.setdefault((b, f"第{i}条"), cur)
                            score[f"第{i}条"][b] += 1
                for mm in ART.finditer(hm.group(1)):
                    heading.setdefault((b, lab_of(mm)), cur)   # 最初の見出しを採る
                    score[lab_of(mm)][b] += 2      # 見出しに出るものは重みを付ける
                continue
            if other(line):
                continue
            if cur and other(cur):
                continue
            for rg in RANGE.finditer(line):
                a, z = int(rg.group(1)), int(rg.group(2))
                if 0 < z - a < 40:
                    for i in range(a, z + 1):
                        score[f"第{i}条"][b] += 1
                        heading.setdefault((b, f"第{i}条"), cur)
            for mm in ART.finditer(line):
                score[lab_of(mm)][b] += 1
                heading.setdefault((b, lab_of(mm)), cur)
    out = {}
    for lab, c in score.items():
        f, n = c.most_common(1)[0]
        out[lab] = (f, title.get(f, f), heading.get((f, lab), ""))
    _deepmap[note] = out
    _headmap[note] = heading
    return out

# 法令名 → その法令を主に扱う本体ノート（他科目の条を指すときに使う）
LAW2NOTE = {"労働基準法": "01-労働基準法.md", "労働安全衛生法": "02-労働安全衛生法.md",
            "労働者災害補償保険法": "03-労災保険法.md", "労災保険法": "03-労災保険法.md",
            "雇用保険法": "04-雇用保険法.md", "労働保険徴収法": "05-徴収法.md",
            "労働保険の保険料の徴収等に関する法律": "05-徴収法.md",
            "健康保険法": "08-健康保険法.md", "厚生年金保険法": "10-厚生年金保険法.md",
            "国民年金法": "09-国民年金法.md"}

_bylaw = {}
def deep_by_law(note):
    """労一・社一のように複数の法律を扱う科目で、法令名 → 深掘りページ を返す。"""
    if note in _bylaw:
        return _bylaw[note]
    pres = DEEP_PRE.get(note, ())
    out = {}
    for path in sorted(glob.glob(f"{NOTES}/*.md")):
        b = os.path.basename(path)
        if not (pres and b[0] in pres and re.match(r"^[A-Z]\d-", b)):
            continue
        head = open(path, encoding="utf-8").read().split("\n", 1)[0]
        title = re.sub(r"｜.*$", "", head.lstrip("# ").strip())
        for nm in re.findall(r"[一-鿿・]{2,20}?(?:法|規則|令)", title + " " + b):
            out.setdefault(nm, (b, title))
    _bylaw[note] = out
    return out

_secmap = {}
def sections_of(note, ownlaw=None):
    """本体ノートの見出し → その節で触れている条ラベル。
       深掘りページが無い条でも、本体のどこを読めばよいかを示すために使う。"""
    if note in _secmap:
        return _secmap[note]
    body = open(f"{NOTES}/{note}", encoding="utf-8").read()
    # 自動生成している「出題傾向」の節は読み飛ばす（自分自身を指してしまうため）
    body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "", body, flags=re.S)
    out, head = {}, None
    for line in body.split("\n"):
        m = re.match(r"^#{2,3} (.+)$", line)
        if m:
            head = m.group(1).strip()
            if re.match(r"(出題傾向|頻出条文|次に読むもの|深掘り|直前チェック|基準点|設問形式)", head):
                head = None
                continue
            # 「4. 労働時間・休憩・休日（32条〜41条の2）」のように、見出し自体が
            # 範囲を示していることがある。その範囲の条もこの節に属するとみなす。
            rg = re.search(r"([0-9]{1,3})条(?:の[0-9]{1,2})?\s*[〜～~－ー-]\s*([0-9]{1,3})条", head)
            if rg:
                a, b = int(rg.group(1)), int(rg.group(2))
                if 0 < b - a < 80:
                    for i in range(a, b + 1):
                        out.setdefault(f"第{i}条", head)
                        for j in range(1, 12):
                            out.setdefault(f"第{i}条の{j}", head)
            else:
                for mm in re.finditer(r"(?<![0-9])([0-9]{1,3})条(?:の([0-9]{1,2}))?", head):
                    lab = f"第{int(mm.group(1))}条" + (f"の{int(mm.group(2))}" if mm.group(2) else "")
                    out.setdefault(lab, head)
            continue
        if not head:
            continue
        for mm in re.finditer(r"(?<![0-9])([0-9]{1,3})条(?:の([0-9]{1,2}))?", line):
            mo = OTHERLAW_ANY.search(line[:mm.start()])
            if mo and (ownlaw is None or mo.group(1) != ownlaw):
                continue
            lab = f"第{int(mm.group(1))}条" + (f"の{int(mm.group(2))}" if mm.group(2) else "")
            out.setdefault(lab, head)
    _secmap[note] = out
    return out

def art_rows(note, arts, ay, lawfilter):
    """頻出条文を、見出し・出題年・深掘りページ付きの表にする。"""
    deep = deep_of(note, lawfilter)
    sec  = sections_of(note, lawfilter)
    rows = ["| 条文 | 何を定めているか | 回数 | 出題された年度 | 詳しく読む |",
            "|---|---|---|---|---|"]
    for key, n in arts.most_common(12):
        m = re.match(r"^(.+?)(第?[0-9]{1,3}条(?:の[0-9]{1,2})?)$", key)
        if not m:
            continue
        law, lab = m.group(1), m.group(2)
        lab = lab if lab.startswith("第") else "第" + lab
        ys = "・".join(KAI2Y[k] for k in sorted(ay.get(key, ()), reverse=True))
        d = deep.get(lab)
        if not lawfilter:                 # 労一・社一は法令名でページを選ぶ
            byname = deep_by_law(note).get(law)
            if byname:
                d = (byname[0], byname[1], deep_head(note, byname[0], lab))
        if d:
            link = f"[{d[1]}]({d[0]})"
        elif sec.get(lab):
            h = sec[lab]
            link = f"本体の[{h}]({note}#{h})"
        elif LAW2NOTE.get(law) and LAW2NOTE[law] != note:
            link = f"[{LAW2NOTE[law][3:-3]}]({LAW2NOTE[law]})"   # 他科目の法令
        else:
            link = "—"
        cap = captions(law).get(lab, "")
        if not cap or len(cap) > 26:
            vague = ("制度の趣旨", "全体像", "何のための制度か", "ポイント", "概要",
                     "основ", "基本", "定義", "はじめに", "主要条文", "位置づけ")
            # 「3つの請求のかたち」のような、内容を表さない見出しは説明に使わない
            VAGUE_RE = re.compile(r"^([0-9１-９]+つ|全体像|一覧|比較|まとめ|区別|使い分け)")
            h2 = (d[2] if d and d[2] and len(d[2]) >= 4
                  and not d[2].startswith(vague) and not VAGUE_RE.match(d[2]) else "")
            cand = [h2, d[1] if d else "",
                    re.sub(r"（[0-9条〜の、・\s]+）$", "",
                           re.sub(r"^\d+\.\s*", "", sec.get(lab, "")))]
            cap = next((c for c in cand if c and c != law and len(c) <= 26), "—")
        shown = lab if lawfilter else key
        rows.append(f"| **{shown}** | {cap} | {n} | {ys or '—'} | {link} |")
    return rows

def tidy(w):
    """本試験PDF由来の余分な空白を詰める（「満15 歳」→「満15歳」）。"""
    w = re.sub(r"(?<=[0-9])\s+(?=[0-9])", "", w)
    w = re.sub(r"\s+(?=[年月日歳時分秒円人条項号級％%割分の以未満トメキ])", "", w)
    return re.sub(r"\s+", " ", w).strip()

def kind_of(w):
    """空欄に入った語を、覚え方が違う3種類に分ける。"""
    if len(w) >= 18:
        return "判示・条文の言い回し"
    if re.search(r"[0-9]", w):
        return "数字"
    return "用語"

def short(w):
    """長い判示はそのまま載せると読めないので、先頭だけにする。"""
    w = w.rstrip("、。 ")
    return w if len(w) <= 26 else w[:24] + "…"

# ノート → (択一の集計に使う科目, 選択式に使う科目, 条文の絞り込み)
TARGET = {
 "01-労働基準法.md":       (["労基安衛"], ["労基安衛"], "労働基準法"),
 "02-労働安全衛生法.md":   (["労基安衛"], ["労基安衛"], "労働安全衛生法"),
 "03-労災保険法.md":       (["労災"],     ["労災"],     "労災保険法"),
 "04-雇用保険法.md":       (["雇用"],     ["雇用"],     "雇用保険法"),
 "05-徴収法.md":           (["労災","雇用"], [],        "労働保険徴収法"),
 "06-労働一般常識.md":     (["一般常識"], ["労一"],     None),
 "07-社会保険一般常識.md": (["一般常識"], ["社一"],     None),
 "08-健康保険法.md":       (["健保"],     ["健保"],     "健康保険法"),
 "09-国民年金法.md":       (["国年"],     ["国年"],     "国民年金法"),
 "10-厚生年金保険法.md":   (["厚年"],     ["厚年"],     "厚生年金保険法"),
}

# ── 基準点補正（合格基準PDFの「ただし〜点以上」から抽出）
KIJUN = json.load(open("kijun.json"))
KIJUN = {int(k): v for k, v in KIJUN.items()}

def shift_table(subs):
    """年度別の設問形式の推移。作問方針が変わったかを見る。"""
    ys = collections.defaultdict(collections.Counter)
    for s in subs:
        for k, c in D[s]["y"].items(): ys[k].update(c)
    if not ys: return [], None
    rows = ["| 年度 | 個数・組合せ | 誤りを選ぶ | 正しいものを選ぶ | 肢の平均字数 | 判例に言及 |",
            "|---|---:|---:|---:|---:|---:|"]
    for k in sorted(ys, reverse=True):
        c = ys[k]; ko = c["個数問題"] + c["組合せ問題"]
        rows.append(f"| {KAI2Y[k]} | {ko} | {c['誤りを選ぶ']} | {c['正しいものを選ぶ']} | "
                    f"{c['字数計']/max(c['肢数'],1):.0f} | {c['判例']} |")
    # 前期（第49〜53回）と後期（第54〜57回）の平均を比べる
    def avg(keys, f):
        cs = [ys[k] for k in keys if k in ys]
        return sum(f(c) for c in cs) / max(len(cs), 1)
    old, new = range(49, 54), range(54, 58)
    g = lambda ks, key: avg(ks, lambda c: c[key])
    d = {"個数": (g(old,"個数問題")+g(old,"組合せ問題"), g(new,"個数問題")+g(new,"組合せ問題")),
         "正": (g(old,"正しいものを選ぶ"), g(new,"正しいものを選ぶ")),
         "判例": (g(old,"判例"), g(new,"判例")),
         "字数": (avg(old, lambda c: c["字数計"]/max(c["肢数"],1)),
                  avg(new, lambda c: c["字数計"]/max(c["肢数"],1)))}
    msg = []
    if d["個数"][1] - d["個数"][0] >= .8:
        msg.append(f"**個数・組合せ問題が増えています**（前期 平均{d['個数'][0]:.1f}問 → 直近4年 平均{d['個数'][1]:.1f}問）。"
                   "全肢の判断が必要なので、1問あたりの時間が伸びます")
    elif d["個数"][0] - d["個数"][1] >= .8:
        msg.append(f"個数・組合せ問題は減っています（前期 平均{d['個数'][0]:.1f}問 → 直近4年 平均{d['個数'][1]:.1f}問）")
    if d["正"][1] - d["正"][0] >= 1:
        msg.append(f"**「正しいものを選べ」が増えています**（{d['正'][0]:.1f}問 → {d['正'][1]:.1f}問）。"
                   "誤りを探すより、**正しい形を知っているか**が問われる方向です")
    if d["判例"][1] - d["判例"][0] >= .5:
        msg.append(f"**判例への言及が増えています**（{d['判例'][0]:.1f}問 → {d['判例'][1]:.1f}問）")
    if d["字数"][0] - d["字数"][1] >= 5:
        msg.append(f"肢が短くなっています（平均{d['字数'][0]:.0f}字 → {d['字数'][1]:.0f}字）")
    return rows, msg

def kijun_lines(sel_subj, tak_subj):
    """この科目で基準点が下がった年。＝救済が期待できるかどうか。"""
    sel = [(k, v["sel"][sel_subj]) for k, v in sorted(KIJUN.items(), reverse=True)
           if sel_subj and sel_subj in v["sel"]]
    tak = [(k, v["tak"][tak_subj]) for k, v in sorted(KIJUN.items(), reverse=True)
           if tak_subj and tak_subj in v["tak"]]
    out = ["### 基準点補正の履歴（この科目が救済された年）", ""]
    if sel:
        out.append("**選択式**　" + "／".join(f"{KAI2Y[k]}年度 **{p}点**に引下げ" for k, p in sel))
    else:
        out.append("**選択式**　過去9年で**一度も引下げなし**")
    if tak:
        out.append("")
        out.append("**択一式**　" + "／".join(f"{KAI2Y[k]}年度 **{p}点**に引下げ" for k, p in tak))
    out.append("")
    n = len(sel)
    if n >= 3:
        out.append(f"> 選択式は9年で**{n}回**引下げられています。難問が出れば救済される可能性はありますが、"
                   "**救済を前提にした学習計画は組めません**。3点は自力で取る前提で。")
    elif n >= 1:
        out.append(f"> 選択式の引下げは9年で{n}回。**例外的**です。基準点は自力で超える前提で臨んでください。")
    else:
        out.append("> **選択式は一度も救済されていません。** ここで3点を割ると、"
                   "他がどれだけ良くてもその時点で不合格です。**取りこぼせない科目**です。"
                   + ("択一も引下げは1回だけです。" if tak else ""))
    out.append("")
    return out
BEGIN, END = "<!-- TREND:BEGIN -->", "<!-- TREND:END -->"

for f, (tsubs, ssubs, lawfilter) in TARGET.items():
    types = collections.Counter(); arts = collections.Counter()
    for s in tsubs:
        types.update(D[s]["t"]); arts.update(D[s]["a"])
    if lawfilter:
        arts = collections.Counter({a:c for a,c in arts.items() if a.startswith(lawfilter)})
    tot = sum(types.values())

    out = [BEGIN, "## 出題傾向（過去9年・第49〜57回の実データ）", ""]
    if tot:
        out += ["### 択一の設問形式", "", "| 形式 | 問数 | 割合 |", "|---|---:|---:|"]
        for t, c in types.most_common():
            out.append(f"| {t} | {c} | {c/tot*100:.0f}% |")
        kosuu = types.get("個数問題",0); kumi = types.get("組合せ問題",0); ko = kosuu + kumi
        out += ["", f"**{tsubs[0] if len(tsubs)==1 else '労災・雇用'}枠 計{tot}問**のうち、"
                    f"**個数問題{kosuu}問・組合せ問題{kumi}問（合わせて{ko/tot*100:.0f}%）**。"
                    + (f"組合せのほうが多い科目です。組合せは**2肢の正誤が分かれば98.5%で正解が決まる**ので、"
                       "時間はかかりません。飛ばす候補は個数問題だけです。"
                       if kumi > kosuu else
                       f"個数問題が多い科目です。個数は**5肢すべての判断が必要**で時間を食います。"
                       "2肢以上分からなければ飛ばしてください。")
                    + "（→ [`A1-個数・組合せ問題の解き方.md`](A1-個数・組合せ問題の解き方.md)）", ""]
    # ── 年度別の推移（作問方針が変わったか）
    rows, msg = shift_table(tsubs)
    if rows:
        out += ["### 設問形式の推移（作問方針の変化）", ""] + rows + [""]
        out += [("\n".join("- " + m for m in msg) if msg
                 else "- 9年を通じて設問形式に大きな変化はありません。過去問の解き方がそのまま通用します。"), ""]

    # ── 基準点補正（救済が期待できる科目か）
    SEL_OF = {"01":"労基安衛","02":"労基安衛","03":"労災","04":"雇用",
              "06":"労一","07":"社一","08":"健保","09":"国年","10":"厚年"}
    TAK_OF = {"01":"労基安衛","02":"労基安衛","03":"労災","04":"雇用",
              "06":"一般常識","07":"一般常識","08":"健保","09":"国年","10":"厚年"}
    pre = f[:2]
    if pre in SEL_OF:
        out += kijun_lines(SEL_OF[pre], TAK_OF[pre])
    elif pre == "05":
        out += ["### 基準点補正の履歴", "",
                "徴収法は独立した科目ではなく、**労災の択一10問中3問・雇用の択一10問中3問**として出題されます。",
                "したがって徴収法単独の基準点はなく、労災・雇用の基準点に組み込まれます。", "",
                "> 択一で**計6問**＝全70問の**9%**。ここは条文数が少なく得点しやすいので、"
                "**6問中5問**を目標にしてください。労災・雇用の基準点割れを防ぐ最大の保険になります。", ""]

    if arts:
        ay = collections.defaultdict(set)
        for sj in tsubs:
            for kk, vv in D[sj]["ay"].items():
                ay[kk] |= vv
        top = arts.most_common(12)
        out += ["### 頻出条文（択一で9年間に参照された回数）", "",
                f"**上位{len(top)}条で択一{sum(c for _, c in top)}回分**。"
                "回数が多い条ほど、条文そのものを読んでおく価値があります。"
                "「詳しく読む」は、その条をいちばん詳しく扱っている別ページです。", ""]
        out += art_rows(f, arts, ay, lawfilter) + [""]
    for s in ssubs:
        if not D[s]["s"]: continue
        rows, kinds = [], collections.Counter()
        for k, laws, ws in sorted(D[s]["s"], reverse=True):
            for i, w in enumerate(ws):
                w = tidy(w)
                kinds[kind_of(w)] += 1
                rows.append((KAI2Y[k] if i == 0 else "",
                             "ABCDE"[i] if i < 5 else str(i + 1),
                             short(w),
                             "／".join(laws) if (i == 0 and laws) else ""))
        tot5 = sum(kinds.values())
        out += [f"### 選択式が9年間で問うたこと（{s}）", "",
                f"**{tot5}空欄**の内訳は "
                + "、".join(f"**{k}{v}**（{v/tot5*100:.0f}%）" for k, v in kinds.most_common())
                + "。空欄は5つあり、**3つ取れれば基準点**です。"
                  "長い判示は先頭だけを載せています。全文は "
                  "[`95-条文素読（選択式の原文）.md`](95-条文素読（選択式の原文）.md) にあります。", "",
                "| 年度 | 空欄 | 正答となった語 | その年の根拠条文 |", "|---|---|---|---|"]
        for y, ab, w, law in rows:
            out.append(f"| {y} | {ab} | {w} | {law} |")
        out.append("")
    out += ["> この節は `kakomon/gen_trend.py` が過去問データから自動生成しています。", END, ""]

    body = open(f"{NOTES}/{f}").read()
    block = "\n".join(out)
    if BEGIN in body:
        body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", block, body, flags=re.S)
    else:
        i = body.index("\n---\n")          # 冒頭の説明表の直後に差し込む
        body = body[:i+5] + "\n" + block + body[i+5:]
    open(f"{NOTES}/{f}", "w").write(body)
    print(f"{f:26s} 択一{tot:3d}問 / 条文{len(arts):2d}種 / 選択式{sum(len(D[s]['s']) for s in ssubs)}年分")
