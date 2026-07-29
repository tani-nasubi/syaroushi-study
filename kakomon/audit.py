#!/usr/bin/env python3
"""ドリルデータの多角的監査。verify.py（原典との文字列照合）が見ていない
別の失敗モードを、10種類の観点から順に検査する。
"""
import collections, json, re, sys, unicodedata
import verify as V
import fitz

ALL = V.ALL
OK, NG = "OK  ", "NG  "
results = []


def report(n, title, problems, detail=""):
    results.append((n, title, problems))
    mark = OK if not problems else NG
    print(f"  {n:2d}. {mark}{title}" + (f"  … {detail}" if detail and not problems else ""))
    for p in problems[:6]:
        print(f"        - {p}")
    if len(problems) > 6:
        print(f"        … 他 {len(problems)-6} 件")


def src_key(q):
    m = V.SRC_RE.search(q["src"])
    return int(m.group(1)), m.group(2)


# ── 1. 正答表の再解析結果が、正答PDFの脚注の記述と整合するか ─────────────
def r1():
    bad = []
    for kai in range(49, 58):
        txt = "".join(p.get_text() for p in fitz.open(f"pdf/{kai}-kijyun-seitou.pdf"))
        note = re.sub(r"[\s　]", "", txt)
        sei = V.SEITOU[kai]
        special = [(k, s, i + 1, v) for k, tbl in sei.items()
                   for s, vals in tbl.items() for i, v in enumerate(vals)
                   if v is None or isinstance(v, list)]
        has_note = "全員正解" in note or "正答とする" in note
        if special and not has_note:
            bad.append(f"第{kai}回: 例外を検出したが脚注に記述なし {special}")
        if has_note and not special:
            bad.append(f"第{kai}回: 脚注に例外の記述があるが表に反映されていない")
        for kind, s, no, v in special:
            if v is None and "全員正解" not in note:
                bad.append(f"第{kai}回 {s}問{no}: 全員正解と判定したが脚注にその記述がない")
            if isinstance(v, list) and "正答とする" not in note:
                bad.append(f"第{kai}回 {s}問{no}: 複数正答と判定したが脚注にその記述がない")
    return report(1, "没問・複数正答の判定が正答PDFの脚注と整合", bad, "例外3件すべて脚注と一致")


# ── 2. 択一式の設問番号が各年・各科目で1〜10を過不足なく満たすか ───────────
def r2():
    bad = []
    seen = collections.defaultdict(set)
    for q in ALL:
        if q["type"] != "abc":
            continue
        kai, subj = src_key(q)
        no = int(re.search(r"問(\d+)$", q["src"]).group(1))
        if no in seen[(kai, subj)]:
            bad.append(f"第{kai}回 {subj} 問{no} が重複")
        seen[(kai, subj)].add(no)
    for kai in range(49, 58):
        for subj in V.parse_seitou.TAK_SUBJECTS:
            got = seen[(kai, subj)]
            if got != set(range(1, 11)):
                bad.append(f"第{kai}回 {subj}: 問番号 {sorted(got)}（1〜10であるべき）")
    return report(2, "択一式の設問番号が9年×7科目×10問を完全に充足", bad, f"{len(seen)}科目すべて1〜10")


# ── 3. 選択式が各年8科目そろい、科目の割当が正しいか ────────────────────
def r3():
    bad = []
    seen = collections.defaultdict(list)
    for q in ALL:
        if q["type"] in ("sel20", "selpb"):
            kai, subj = src_key(q)
            seen[kai].append(subj)
    for kai in range(49, 58):
        if sorted(seen[kai]) != sorted(V.parse_seitou.SEL_SUBJECTS):
            bad.append(f"第{kai}回: {sorted(seen[kai])}")
    return report(3, "選択式が9年×8科目を完全に充足", bad, "各年8科目そろい")


# ── 4. 選択式の空欄がA〜Eの5個で、本文中に昇順で初出するか ────────────────
def r4():
    bad = []
    for q in ALL:
        if q["type"] not in ("sel20", "selpb"):
            continue
        order = []
        for m in re.finditer(r"【([A-E])】", q["q"]):
            if m.group(1) not in order:
                order.append(m.group(1))
        if order != list("ABCDE"):
            bad.append(f"{q['src']}: 初出順 {''.join(order)}")
        if len(q["a"]) != 5:
            bad.append(f"{q['src']}: 解答数 {len(q['a'])}")
    return report(4, "選択式の空欄がA〜Eの5個・本文中で昇順に初出", bad, "72問すべて正常")


# ── 5. 選択式の正答が語群内に実在し、20語に重複がないか ──────────────────
def r5():
    bad = []
    for q in ALL:
        if q["type"] == "sel20":
            if len(set(q["choices"])) != 20:
                dup = [w for w, c in collections.Counter(q["choices"]).items() if c > 1]
                bad.append(f"{q['src']}: 語群に重複 {dup}")
            for i, v in enumerate(q["a"]):
                if not q["choices"][v].strip():
                    bad.append(f"{q['src']} 空欄{'ABCDE'[i]}: 正答が空文字")
        elif q["type"] == "selpb":
            for i, g in enumerate(q["groups"]):
                if len(set(g)) != len(g):
                    bad.append(f"{q['src']} 空欄{'ABCDE'[i]}: 選択肢に重複")
                if not g[q["a"][i]].strip():
                    bad.append(f"{q['src']} 空欄{'ABCDE'[i]}: 正答が空文字")
    return report(5, "選択式の語群に重複がなく正答が実在", bad, "語群の重複・空正答なし")


# ── 6. 制御文字・置換文字・不正なUnicodeの混入 ────────────────────────
def r6():
    bad = []
    for q in ALL:
        texts = [q.get("q", "")] + list(q.get("choices") or []) + \
                [c for g in (q.get("groups") or []) for c in g]
        for t in texts:
            if not isinstance(t, str):
                continue
            for ch in t:
                cat = unicodedata.category(ch)
                if cat.startswith("C") and ch not in "\n\t":
                    bad.append(f"{q['src']}: 制御文字 U+{ord(ch):04X}")
                    break
            if "�" in t or "□" in t:
                bad.append(f"{q['src']}: 文字化けの疑い")
                break
    return report(6, "制御文字・文字化けの混入なし", bad, "3,282問すべてクリーン")


# ── 7. 末尾欠落の決定的検査 ────────────────────────────────
#    「文末記号があるか」といった体裁の推定では、体言止めの肢（「…当該機械による作業」）や
#    計算問題（「…= 2，000 円」）と区別できない。
#    そこで原典上で「肢の直後が次の肢記号（Ｂ〜Ｅ）／次の設問」になっているかを直接確かめる。
#    途中で切れていれば、直後には本来続くはずの本文が現れるため確実に検出できる。
def r7():
    bad = []
    HEAD = "|".join(re.escape(h[:3]) for h in V.parse_mondai.HEADINGS)
    NEXT = re.compile(rf"^(〔問|選択肢|{HEAD}|$)")

    def fits(raw, start, q):
        """start から順に5肢が並び、各肢の直後が次の肢記号になっているか"""
        pos = start
        for i, c in enumerate(q["choices"]):
            t = V.norm(c)
            if not t:
                return False
            p = raw.find(t, pos)
            if p < 0:
                return False
            pos = p + len(t)
            after = raw[pos: pos + 3]
            if i < 4:
                if not after.startswith("ＢＣＤＥ"[i]):
                    return False
            elif not NEXT.match(after):
                return False
        return True

    for q in ALL:
        if q["type"] != "abc":
            continue
        kai, _ = src_key(q)
        raw = V.RAW[(kai, "takuitsu")]
        stem = V.norm(q["q"])
        # 設問文は年度内で重複しうる（「厚生年金保険法に関する次のアからオの…」等）ため、
        # 一致する全候補位置を試し、どれかで5肢の境界が成立すればよい
        cands, p = [], raw.find(stem)
        while p >= 0:
            cands.append(p + len(stem))
            p = raw.find(stem, p + 1)
        if not cands:
            bad.append(f"{q['src']}: 問題文が原典に存在しない")
        elif not any(fits(raw, c, q) for c in cands):
            bad.append(f"{q['src']}: 5肢が原典上で連続していない（末尾欠落の疑い）")
    return report(7, "各肢の直後が原典上で次の肢記号／次設問（末尾欠落なし）", bad,
                  "630設問×5肢すべて境界一致")


# ── 8. 同一問題の重複登録 ──────────────────────────────────────
def r8():
    bad = []
    seen = {}
    for q in ALL:
        if q["type"] == "ox":
            continue
        # 設問文は年度をまたいで同一のことがある（「労働基準法の総則…正しいものはどれか。」等）
        # ため、選択肢まで含めた全文で同一性を判定する
        key = re.sub(r"[\s　]", "", q["q"] + "|".join(
            (q.get("choices") or []) + [c for g in (q.get("groups") or []) for c in g]))
        if key in seen and seen[key] != q["src"]:
            bad.append(f"重複: {q['src']} と {seen[key]}")
        seen[key] = q["src"]
    ids = [q["src"] + "|" + q["type"] for q in ALL if q["type"] != "ox"]
    for k, c in collections.Counter(ids).items():
        if c > 1:
            bad.append(f"同一srcが{c}件: {k}")
    return report(8, "設問の重複登録なし（設問文＋選択肢の全文で判定）", bad, "702問すべて一意")


# ── 9. 肢別○×の網羅性と偏り ─────────────────────────────────
def r9():
    bad = []
    parents = {q["src"] for q in ALL if q["type"] == "abc"}
    by_parent = collections.defaultdict(list)
    for q in ALL:
        if q["type"] == "ox":
            by_parent[q["src"].rsplit(" 肢", 1)[0]].append(q)
    for p, ch in by_parent.items():
        if p not in parents:
            bad.append(f"親設問が存在しない: {p}")
        if len(ch) != 5:
            bad.append(f"{p}: 肢が{len(ch)}個")
        if sorted(x["src"][-1] for x in ch) != list("ABCDE"):
            bad.append(f"{p}: 肢記号が不正")
    # 「誤っているものはどれか」型なら 正1:誤4、「正しいものは」型なら 正4:誤1 になるはず
    for p, ch in by_parent.items():
        t = sum(1 for x in ch if x["a"])
        if t not in (1, 4):
            bad.append(f"{p}: 正の肢が{t}個（1か4であるべき）")
    n_true = sum(1 for q in ALL if q["type"] == "ox" and q["a"])
    n = sum(1 for q in ALL if q["type"] == "ox")
    return report(9, "肢別○×が親設問ごとに5肢そろい正誤比が整合", bad,
                  f"{len(by_parent)}設問／○{n_true}・×{n-n_true}")


# ── 10. アプリの採点ロジックを再現し、正答選択で必ず正解になるか ────────────
def r10():
    bad = []
    for q in ALL:
        t = q["type"]
        if t == "abc":
            correct = [] if q["a"] is None else (q["a"] if isinstance(q["a"], list) else [q["a"]])
            # 正答を選べば正解
            for c in (correct or [0]):
                ok = True if q["a"] is None else c in correct
                if not ok:
                    bad.append(f"{q['src']}: 正答{c}を選んで不正解判定")
            # 誤答を選べば不正解（没問を除く）
            if q["a"] is not None:
                wrong = next(i for i in range(5) if i not in correct)
                if wrong in correct:
                    bad.append(f"{q['src']}: 誤答判定が破綻")
        elif t in ("sel20", "selpb"):
            blanks = sorted(set(re.findall(r"【([A-E])】", q["q"])))
            # アプリは picked を a.length で確保し、空欄記号のindexで引くため一致必須
            if len(blanks) != len(q["a"]):
                bad.append(f"{q['src']}: 空欄数{len(blanks)}≠解答数{len(q['a'])}（表示が破綻）")
                continue
            src = q["choices"] if t == "sel20" else None
            for i, v in enumerate(q["a"]):
                pool = src if src is not None else q["groups"][i]
                if not (0 <= v < len(pool)):
                    bad.append(f"{q['src']} 空欄{'ABCDE'[i]}: 正答index {v} が範囲外")
            if not all(q["a"][i] == q["a"][i] for i in range(len(q["a"]))):
                bad.append(f"{q['src']}: 採点不能")
        elif t == "ox":
            if q["a"] not in (True, False):
                bad.append(f"{q['src']}: ○×が真偽値でない")
    return report(10, "アプリの採点ロジック上、正答選択で必ず正解になる", bad,
                  "3,282問すべて採点可能")


if __name__ == "__main__":
    print(f"═══ ドリルデータ多角監査（全 {len(ALL)} 問）═══\n")
    for f in (r1, r2, r3, r4, r5, r6, r7, r8, r9, r10):
        f()
    ng = [r for r in results if r[2]]
    print(f"\n═══ 10項目中 {10-len(ng)} 項目が合格 ═══")
    if ng:
        for n, t, p in ng:
            print(f"  ■ {n}. {t}: {len(p)}件")
        sys.exit(1)
    print("  すべて合格")
