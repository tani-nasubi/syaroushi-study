#!/usr/bin/env python3
"""改正で答えが変わってしまった過去問を洗い出す。

過去問は9年分あるが、社労士試験は改正が多い。出題時は正しかった肢でも、
今は誤りになっているものがある。それを知らずに繰り返すと、間違いを
覚え込むことになる。

  施行より前の回の問題で、その論点に触れているものを拾う。
  出力: ../drill/data/stale.js  { 問題ID: "注意書き" }

第49回=平成29年 … 第57回=令和7年。試験は8月なので、その年の4月施行の
改正はその回から対象になる。
"""
import json, re, os, glob, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_qref import js_array

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "drill", "data")
OUT  = os.path.join(DATA, "stale.js")

# (この回から新しい扱い, 語, 何がどう変わったか)
CHANGES = [
 (51, r"時間外労働の上限|限度時間|特別条項|月45時間|年360時間|100時間未満|複数月平均80",
      "時間外労働の上限規制は平成31年4月（中小は令和2年4月）から。それ以前の回の「限度基準告示」を前提にした肢は、いまは扱いが違う"),
 (51, r"時季を定めることにより与えなければ|年5日|5日について時季",
      "年休の年5日の時季指定義務は平成31年4月から"),
 (52, r"労働契約法第20条|労契法20条|期間の定めがあることによる不合理",
      "労働契約法20条は令和2年4月に削除され、パート・有期法8条・9条へ移った"),
 (52, r"国内に住所を有する|国内居住要件",
      "被扶養者の国内居住要件は令和2年4月から。それ以前の回には無い要件"),
 (53, r"70歳までの|就業確保措置|創業支援等措置",
      "70歳までの就業確保措置（努力義務）は令和3年4月から"),
 (54, r"支給停止調整開始額|28万円|47万円",
      "60歳台前半の在職老齢年金の基準額は令和4年4月に28万円から47万円へ。令和8年4月からは65万円"),
 (54, r"繰下げ|75歳|0\.7％|0\.5％|0\.4％",
      "繰下げの上限は令和4年4月から75歳。繰上げの減額率は昭和37年4月2日以後生まれが0.4％"),
 (54, r"傷病手当金.*(1年6|一年六|通算)|通算して1年6",
      "傷病手当金の支給期間の通算化は令和4年1月から。それ以前は暦の上での1年6か月"),
 (54, r"任意継続被保険者.*(申出|脱退)|任意継続.*資格を喪失",
      "任意継続被保険者の申出による脱退は令和4年1月から。それ以前は2年間抜けられなかった"),
 (55, r"出生時育児休業|産後パパ育休|育児休業.*分割",
      "出生時育児休業（産後パパ育休）と育休の分割取得は令和4年10月から"),
 (55, r"101人|100人を超える|51人|501人|短時間労働者.*適用拡大|特定適用事業所",
      "短時間労働者の適用拡大は、令和4年10月に101人超、令和6年10月に51人超へ。年によって数字が違う"),
 (55, r"後期高齢者.*2割|2割を負担",
      "後期高齢者医療の2割負担は令和4年10月から"),
 (58, r"給付制限|2か月間|二箇月間",
      "自己都合離職の給付制限は令和7年4月から原則1か月。過去問はすべて旧法（2か月）"),
 (58, r"高年齢雇用継続給付|15％|100分の15",
      "高年齢雇用継続基本給付金の上限は令和7年4月から10％。過去問はすべて旧法（15％）"),
 (58, r"懲役|禁錮|禁こ",
      "令和7年6月から拘禁刑に一本化。条文の「懲役」「禁錮」はいまは「拘禁刑」"),
 (58, r"年金分割.*請求|2年を経過|請求すべき期限",
      "離婚時分割の請求期限は令和8年4月から5年（旧2年）"),
 (58, r"葬祭料|315,000|31万5",
      "労災の葬祭料の定額部分は330,000円（旧315,000円）"),
 (58, r"支給停止調整額|50万円|51万円|48万円",
      "在職老齢年金の支給停止調整額は令和8年4月から65万円"),
]

def main():
    out, cnt = {}, collections.Counter()
    for f in sorted(glob.glob(os.path.join(DATA, "*.js"))):
        s = open(f, encoding="utf-8").read()
        m = re.search(r'DRILL\.register\(\s*"([^"]+)"', s)
        if not m:
            continue
        tail = s[m.end():]
        try:
            arr = json.loads(tail[tail.index("["):tail.rindex("]") + 1])
        except Exception:
            arr = js_array(tail[tail.index("["):tail.rindex("]") + 1])
        if arr is None:
            continue
        for i, q in enumerate(arr):
            src = str(q.get("src", ""))
            mm = re.search(r"第(\d+)回", src)
            if not mm:
                continue
            kai = int(mm.group(1))
            body = " ".join(str(q.get(k, "")) for k in ("q", "stem", "head", "tail"))
            body += " ".join(str(x) for x in (q.get("choices") or []))
            body = re.sub(r"\s+", "", body)
            hits = [note for since, pat, note in CHANGES
                    if kai < since and re.search(pat, body)]
            if hits:
                out[f"{m.group(1)}#{i}"] = hits[0]
                cnt[hits[0][:26]] += 1
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("/* 改正で答えが変わった過去問。kakomon/stale.py が作る。 */\n")
        fh.write("window.STALE = " + json.dumps(out, ensure_ascii=False, indent=0) + ";\n")
    print(f"→ {OUT}  {len(out)}問に注意書きを付けた / {os.path.getsize(OUT):,} bytes")
    for k, v in cnt.most_common():
        print(f"   {v:4d}問  {k}…")

if __name__ == "__main__":
    main()
