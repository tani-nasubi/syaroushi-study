#!/usr/bin/env python3
"""本試験問題PDF（選択式・択一式）から設問を抽出する。

PDF特有の処理:
  ・数字が下付き文字（U+2080〜2089）で入っている → 通常数字へ正規化
  ・日本語が行の途中で折り返される → 行を連結（空白を入れない）
  ・ページ番号だけの行、ページ区切りを除去
  ・選択肢の記号は行頭の全角ＡＢＣＤＥ＋全角スペース
"""
import glob, json, os, re, sys, unicodedata

SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
MARU = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

SEL_SUBJECTS = ["労基安衛", "労災", "雇用", "労一", "社一", "健保", "厚年", "国年"]
TAK_SUBJECTS = ["労基安衛", "労災", "雇用", "一般常識", "健保", "厚年", "国年"]


def load_lines(path):
    """PDF抽出テキストを行リストへ。ページ区切り・ページ番号行を除去。"""
    raw = open(path).read().translate(SUB)
    raw = raw.replace("　", "　")
    out = []
    for line in raw.split("\n"):
        s = line.strip()
        if not s or s.startswith("=== p"):
            continue
        if re.fullmatch(r"[0-9]{1,3}", s):        # ページ番号
            continue
        out.append(s)
    return drop_vertical_footer(out)


# ページ脚注は縦組み（1文字1行）で入るため、1文字行の連なりとして現れる。
# 空欄記号（Ａ〜Ｅ）も1文字行なので、連結して脚注と一致する範囲だけを取り除く。
FOOTER = re.compile(r"問題は次のページに続きます。?|問題は次ページに続きます。?|以下余白")


def drop_vertical_footer(lines):
    out, i = [], 0
    while i < len(lines):
        if len(lines[i]) == 1:
            j = i
            while j < len(lines) and len(lines[j]) == 1:
                j += 1
            run = "".join(lines[i:j])
            m = FOOTER.search(run)
            if m and j - i >= 5:
                out += list(run[:m.start()]) + list(run[m.end():])
                i = j
                continue
        out.append(lines[i])
        i += 1
    return out


# 設問と設問の間に挟まる科目見出し。直後の設問のものなので、前の設問の末尾から取り除く
HEADINGS = {
    "労働基準法及び労働安全衛生法", "労働者災害補償保険法", "雇用保険法",
    "労務管理その他の労働に関する一般常識", "社会保険に関する一般常識",
    "健康保険法", "厚生年金保険法", "国民年金法",
    "労働者災害補償保険法（労働保険の保険料の徴収等に関する法律を含む。）",
    "雇用保険法（労働保険の保険料の徴収等に関する法律を含む。）",
    "労務管理その他の労働及び社会保険に関する一般常識",
}


_NOSP = {re.sub(r"\s|　", "", h) for h in HEADINGS}


def trim_block(blk):
    """設問ブロック末尾の科目見出し行を除去する。

    見出しは「雇　用　保　険　法」のように字間に全角スペースを入れて組版されて
    いるため、空白を除去してから照合する。
    """
    while len(blk) > 1 and re.sub(r"\s|　", "", blk[-1]) in _NOSP:
        blk = blk[:-1]
    return blk


def blank_of(line):
    """行が空欄記号（Ａ〜Ｅ／A〜E の単独）ならその英字を返す。"""
    s = line.strip()
    if len(s) == 1 and s in "ＡＢＣＤＥABCDE":
        return "ABCDE"["ＡＢＣＤＥABCDE".index(s) % 5]
    return None


def split_maru(txt):
    """丸数字で区切られた選択肢列を番号順のリストにする。"""
    parts = re.split(f"([{MARU}])", txt)
    d = {}
    for a in range(1, len(parts) - 1, 2):
        d[MARU.index(parts[a]) + 1] = parts[a + 1].strip(" 　")
    return [d.get(i + 1, "") for i in range(max(d))] if d else []


def join(lines):
    """日本語の折り返しを連結し、余分な空白を整理。"""
    t = "".join(lines)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"(?<=[぀-ヿ一-鿿、。」）])\s+(?=[぀-ヿ一-鿿「（])", "", t)
    return t.strip()


# ────────────────────────── 択一式 ──────────────────────────
def parse_takuitsu(path):
    lines = load_lines(path)
    # 設問の開始位置
    idx = [(i, int(m.group(1))) for i, l in enumerate(lines)
           if (m := re.match(r"〔問\s*(\d+)〕", l))]
    if not idx:
        return []
    qs = []
    subj_i = -1
    for k, (start, num) in enumerate(idx):
        if num == 1:
            subj_i += 1
        end = idx[k + 1][0] if k + 1 < len(idx) else len(lines)
        blk = trim_block(lines[start:end])
        subject = TAK_SUBJECTS[subj_i] if subj_i < 7 else "?"

        # (1) 選択肢が行頭にある通常形式
        marks = [(j, l[0]) for j, l in enumerate(blk) if re.match(r"^[ＡＢＣＤＥ]　", l)]
        seq, want = [], "ＡＢＣＤＥ"
        for j, ch in marks:
            if len(seq) < 5 and ch == want[len(seq)]:
                seq.append(j)
        if len(seq) == 5:
            stem = re.sub(r"^〔問\s*\d+〕\s*", "", join(blk[:seq[0]]))
            ch = [re.sub(r"^[ＡＢＣＤＥ]　", "",
                         join(blk[seq[a]: seq[a + 1] if a + 1 < 5 else len(blk)])) for a in range(5)]
            qs.append({"num": num, "subject": subject, "stem": stem, "choices": ch})
            continue

        # (2) 組合せ問題など、1行に複数の選択肢が並ぶ形式
        #     連結後のテキストから Ａ→Ｂ→Ｃ→Ｄ→Ｅ が昇順に並ぶ最後の並びを選択肢とみなす
        text = join(blk)
        pos = [(m.start(), m.group(0)[0]) for m in re.finditer(r"[ＡＢＣＤＥ]　", text)]
        best = None
        for i, (p, c) in enumerate(pos):
            if c != "Ａ":
                continue
            got, want2 = [p], "ＢＣＤＥ"
            for p2, c2 in pos[i + 1:]:
                if len(got) <= 4 and c2 == want2[len(got) - 1]:
                    got.append(p2)
                if len(got) == 5:
                    break
            if len(got) == 5:
                best = got
        if best:
            stem = re.sub(r"^〔問\s*\d+〕\s*", "", text[:best[0]]).strip()
            ch = [re.sub(r"^[ＡＢＣＤＥ]　", "",
                         text[best[a]: best[a + 1] if a + 1 < 5 else len(text)]).strip() for a in range(5)]
            qs.append({"num": num, "subject": subject, "stem": stem, "choices": ch})
        else:
            qs.append({"num": num, "subject": subject, "stem": text, "choices": [], "broken": True})
    return qs


# ────────────────────────── 選択式 ──────────────────────────
def parse_sentaku(path):
    lines = load_lines(path)
    idx = [(i, int(m.group(1))) for i, l in enumerate(lines)
           if (m := re.match(r"〔問\s*(\d+)〕", l))]
    qs = []
    for k, (start, num) in enumerate(idx):
        end = idx[k + 1][0] if k + 1 < len(idx) else len(lines)
        blk = trim_block(lines[start:end])
        # 「選択肢」行で本文と語群を分ける
        cut = next((j for j, l in enumerate(blk) if l.strip() == "選択肢"), None)
        if cut is None:
            qs.append({"num": num, "subject": SEL_SUBJECTS[num - 1] if num <= 8 else "?",
                       "body": join(blk), "choices": [], "broken": True})
            continue
        # 単独行の空欄記号＝空欄。原文に半角混じりの年度があるため両方を受ける
        body = [(f"【{blank_of(l)}】" if blank_of(l) else l) for l in blk[:cut]]
        body = join(body)
        body = re.sub(r"^〔問\s*\d+〕\s*", "", body)
        body = re.sub(r"^次の文中の\s*の部分を選択肢の中の最も適切な語句で埋め、?完全な文章とせよ。?\s*", "", body)
        blanks = sorted(set(re.findall(r"【([A-E])】", body)))

        # 語群は2形式ある:
        #   pool20   … ①〜⑳の共通語群から5つ選ぶ（現行の標準形式）
        #   perblank … 空欄ごとに①〜④程度の選択肢が用意される（雇用保険法などで頻出）
        tail = blk[cut + 1:]
        marks = [(j, blank_of(l)) for j, l in enumerate(tail) if blank_of(l)]
        if marks:
            groups = []
            for a, (j, _) in enumerate(marks):
                e = marks[a + 1][0] if a + 1 < len(marks) else len(tail)
                groups.append(split_maru(join(tail[j + 1:e])))
            fmt, ch = "perblank", groups
            ok = len(groups) == 5 and all(len(g) >= 2 for g in groups)
        else:
            d = split_maru(join(tail))
            fmt, ch = "pool20", (d + [""] * 20)[:20]
            ok = len([c for c in ch if c]) == 20

        qs.append({"num": num, "subject": SEL_SUBJECTS[num - 1] if num <= 8 else "?",
                   "body": body, "format": fmt, "choices": ch, "blanks": blanks,
                   "broken": (not ok) or blanks != list("ABCDE")})
    return qs


# ── 段落の復元 ──
# PDFの行送りは文の途中で折り返すため、抽出時にすべて連結している。
# そのままだと「ア」「イ」や段落番号が本文と地続きになって読めないので、
# 試験問題そのものが持つ構造記号から段落を組み直す。
def restore_iroha(stem):
    """「次のアからオの記述のうち」型で、ア〜オを行頭に出す。
    ア〜オが句点のあとに『この順で』現れる位置だけを切るので、
    「アルバイト」のような語頭の一致では切れない。"""
    if not re.search(r"次のアから|アから[イウエオ]", stem):
        return stem
    pos, cuts = 0, []
    for L in "アイウエオ":
        m = re.compile(r"(?<=[。）])" + L + r"[　 ]?").search(stem, pos)
        if not m:
            break
        cuts.append(m.start()); pos = m.end()
    if len(cuts) < 2:
        return stem
    parts, prev = [], 0
    for c in cuts:
        parts.append(stem[prev:c]); prev = c
    parts.append(stem[prev:])
    return "\n".join(p.strip() for p in parts)

def restore_para(body):
    """選択式の段落番号（2〜5）を行頭に出す。
    区切りは「句点＋数字＋全角スペース」に限る。金額や条番号は全角スペースを
    伴わないので巻き込まない。"""
    pos, cuts = 0, []
    for n in range(2, 6):
        m = re.compile(r"(?<=。)" + str(n) + r"　").search(body, pos)
        if not m:
            break
        cuts.append(m.start()); pos = m.end()
    if not cuts:
        return body
    parts, prev = [], 0
    for c in cuts:
        parts.append(body[prev:c]); prev = c
    parts.append(body[prev:])
    return "\n".join(p.strip() for p in parts)


if __name__ == "__main__":
    out = {}
    for p in sorted(glob.glob("txt/*-sentakusiki.txt")):
        kai = int(os.path.basename(p).split("-")[0])
        qs = parse_sentaku(p)
        for q in qs: q["body"] = restore_para(q["body"])
        bad = [q["num"] for q in qs if q.get("broken")]
        print(f"第{kai}回 選択式 {len(qs)}問" + (f"  ← 要確認 問{bad}" if bad else ""))
        out.setdefault(kai, {})["sentaku"] = qs
    print()
    for p in sorted(glob.glob("txt/*-takuitusiki.txt")):
        kai = int(os.path.basename(p).split("-")[0])
        qs = parse_takuitsu(p)
        for q in qs: q["stem"] = restore_iroha(q["stem"])
        bad = [f'{q["subject"]}問{q["num"]}' for q in qs if q.get("broken")]
        print(f"第{kai}回 択一式 {len(qs)}問" + (f"  ← 要確認 {bad}" if bad else ""))
        out.setdefault(kai, {})["takuitsu"] = qs
    json.dump(out, open("mondai.json", "w"), ensure_ascii=False, indent=1)
    print("\n→ mondai.json")
