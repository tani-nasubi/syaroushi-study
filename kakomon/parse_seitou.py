#!/usr/bin/env python3
"""合格基準・正答PDFから正答表を抽出する。

方式:
  1. ヘッダ行（Ａ〜Ｅ・1〜10 の15列）から各列の x 座標を得る
  2. 表領域の解答文字を「文字単位の座標」で拾う
     （科目名と丸数字が1トークンに連結される年度があるため語単位では不可）
  3. 列ごとに独立して y クラスタリングし、上から順に科目へ割り当てる
     （一般常識の択一が2行に分かれる年度と1行の年度が混在するため、
       全列共通のバンドを仮定してはいけない）

科目の並び（上から）:
  選択式: 労基安衛 / 労災 / 雇用 / 労一 / 社一 / 健保 / 厚年 / 国年
  択一式: 労基安衛 / 労災 / 雇用 / 一般常識 / 健保 / 厚年 / 国年

例外:
  ・全員正解（セルが「※」のみ）→ None
  ・複数正答（1セルに2文字）    → リスト
"""
import fitz, glob, json, os, re, statistics, sys

MARU = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
SEL_SUBJECTS = ["労基安衛", "労災", "雇用", "労一", "社一", "健保", "厚年", "国年"]
TAK_SUBJECTS = ["労基安衛", "労災", "雇用", "一般常識", "健保", "厚年", "国年"]
HDR = re.compile(r"[ＡＢＣＤＥ]|10|[1-9]")


def chars(page):
    """(y, x, 文字) を文字単位で返す。"""
    out = []
    for blk in page.get_text("rawdict")["blocks"]:
        for line in blk.get("lines", []):
            for span in line["spans"]:
                for ch in span["chars"]:
                    x0, y0, _, _ = ch["bbox"]
                    out.append((y0, x0, ch["c"]))
    return out


def cluster(entries, gap=18):
    """[(y, value)] を y の近さでセルにまとめる → [(y_center, [values])]"""
    cells = []
    for y, v in sorted(entries):
        if cells and y - cells[-1][-1] < gap:
            cells[-1][1].append(v)
            cells[-1][2] = y
        else:
            cells.append([y, [v], y])
    return [((c[0] + c[2]) / 2, c[1]) for c in cells]


def align(ys, ref):
    """ys（欠落あり）を ref のスロットへ単調に割り当てる。戻り値: (総コスト, スロット番号list)"""
    m, n = len(ys), len(ref)
    INF = float("inf")
    dp = [[INF] * (n + 1) for _ in range(m + 1)]
    bk = [[None] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = 0
    for i in range(m + 1):
        for j in range(n + 1):
            if dp[i][j] == INF:
                continue
            if j < n and dp[i][j] < dp[i][j + 1]:        # スロット j を飛ばす
                dp[i][j + 1], bk[i][j + 1] = dp[i][j], (i, j, None)
            if i < m and j < n:                           # ys[i] を スロット j に対応
                c = dp[i][j] + abs(ys[i] - ref[j])
                if c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1], bk[i + 1][j + 1] = c, (i, j, j)
    best_j = min(range(n + 1), key=lambda j: dp[m][j] if dp[m][j] < INF else INF)
    slots, i, j = [], m, best_j
    while bk[i][j]:
        pi, pj, s = bk[i][j]
        if s is not None:
            slots.append(s)
        i, j = pi, pj
    return dp[m][best_j], slots[::-1]


def assign(by_col, n_subj, subjects, n_col):
    """列ごとのセル列を科目に割り当てる。

    一般常識の択一が「労一行／社一行」に分かれる年度と、独立1行の年度が
    混在するため、全列共通の y バンドを仮定できない。完全な列（セル数＝科目数）は
    上から順に対応させ、欠落のある列は最も近い完全列の y 配置へ DP で位置合わせする。
    """
    full = {i: [c[0] for c in by_col[i]] for i in range(n_col) if len(by_col[i]) == n_subj}

    table = {s: [None] * n_col for s in subjects}
    for col in range(n_col):
        cells = by_col[col]
        if len(cells) == n_subj:
            slots = list(range(n_subj))
        elif full:
            ys = [c[0] for c in cells]
            _, slots = min((align(ys, ref) for ref in full.values()), key=lambda r: r[0])
        else:
            slots = list(range(len(cells)))
        for (ycen, vals), r in zip(cells, slots):
            table[subjects[r]][col] = vals[0] if len(vals) == 1 else sorted(set(vals))
    return table


def parse(path):
    pg = fitz.open(path)[0]

    # --- ヘッダ行（列見出しが最も多く並ぶ行）---
    rows = {}
    for w in pg.get_text("words"):
        if HDR.fullmatch(w[4]):
            rows.setdefault(round(w[1] / 6) * 6, []).append(w[0])
    hdr_y, cols = max(rows.items(), key=lambda kv: len(kv[1]))
    cols = sorted(cols)
    assert len(cols) == 15, f"{path}: 列数 {len(cols)} @y={hdr_y}"

    # --- 表の下端 ---
    # 表の下には「※…問6及び問10についてはA及びEを正答とする」といった脚注があり、
    # その A / E が x 座標の偶然で択一列に入り込む。丸数字（選択式列にしか現れない）の
    # 最終行を表の下端とみなして除外する。
    cs = chars(pg)
    maru_ys = [y for y, x, ch in cs
               if ch in MARU and y > hdr_y + 10 and abs(min(cols[:5], key=lambda c: abs(c - x)) - x) <= 14]
    bottom = max(maru_ys) + 24 if maru_ys else float("inf")

    # --- 表領域の解答文字を列に割り当て ---
    sel = {i: [] for i in range(5)}
    tak = {i: [] for i in range(10)}
    for y, x, ch in cs:
        if y <= hdr_y + 10 or y >= bottom:
            continue
        col = min(range(15), key=lambda i: abs(cols[i] - x))
        if abs(cols[col] - x) > 14:
            continue
        if col < 5 and ch in MARU:
            sel[col].append((y, MARU.index(ch) + 1))
        elif col >= 5 and ch in "ABCDE":
            tak[col - 5].append((y, "ABCDE".index(ch)))

    return {
        "sentaku": assign({i: cluster(sel[i]) for i in range(5)}, 8, SEL_SUBJECTS, 5),
        "takuitsu": assign({i: cluster(tak[i]) for i in range(10)}, 7, TAK_SUBJECTS, 10),
    }


if __name__ == "__main__":
    result, bad = {}, 0
    for p in sorted(glob.glob("pdf/*-kijyun-seitou.pdf")):
        kai = int(os.path.basename(p).split("-")[0])
        r = parse(p)
        result[kai] = r
        notes = []
        for kind, tbl in r.items():
            for s, vals in tbl.items():
                for i, v in enumerate(vals):
                    if v is None:
                        notes.append(f"{kind}/{s}/問{i+1}=全員正解")
                    elif isinstance(v, list):
                        notes.append(f"{kind}/{s}/問{i+1}=複数正答{[chr(65+x) if kind=='takuitsu' else x for x in v]}")
        n_sel = sum(1 for v in r["sentaku"].values() for x in v if x is not None)
        n_tak = sum(1 for v in r["takuitsu"].values() for x in v if x is not None)
        ok = n_sel == 40 and n_tak + sum("全員正解" in n for n in notes) >= 70
        if not ok: bad += 1
        print(f"第{kai}回 選択{n_sel}/40 択一{n_tak}/70{'' if ok else '  ← 要確認'}"
              + ("\n         " + "\n         ".join(notes) if notes else ""))
    json.dump(result, open("seitou.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n→ seitou.json （要確認 {bad} 件）")
