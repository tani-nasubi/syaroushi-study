# kakomon — 過去問データの生成

本試験のPDFから問題・正答を取り出し、アプリ用のデータと資料を組み立てる。

## 元データの取得

`pdf/` と `txt/` はリポジトリに含めていない。
[社会保険労務士試験オフィシャルサイト](https://www.sharosi-siken.or.jp/) から
第49〜57回の「択一式」「選択式」「合格基準及び正答」のPDFを `pdf/` に置き、
`extract.py` でテキスト化してから以下を実行する。

## 生成の順番

| スクリプト | 出力 | 内容 |
|---|---|---|
| `parse_seitou.py` | `seitou.json` | 正答表。列座標＋DPで欠けたセルを補う |
| `parse_mondai.py` | `mondai.json` | 問題文と選択肢 |
| `gen_data.py` | `drill/data/kako-*.js` | 択一630問・選択式72問・肢別○×2,580問 |
| `gen_tokuten.py` | `notes/96-得点源リスト.md` | 論点のS/A/B/Cランクと出題傾向の分析 |
| `gen_hikkake.py` | `notes/97-引っかけの型.md` | 誤り肢の改変パターン |
| `gen_seibun.py` | `notes/A0-正文集.md` | 正誤が確定した正しい肢 |
| `gen_kosuu.py` | `notes/A1-個数・組合せ問題の解き方.md` | 選択肢構造の解析 |
| `gen_genbun.py` | `notes/95-条文素読.md` | 選択式の原文（正答を埋め戻したもの） |
| `gen_trend.py` | `notes/0*.md`, `10-*.md` | 各科目ノートの「出題傾向」節 |
| `gen_stats.py` | `drill/data/stats.js` | 傾向タブ用の統計 |
| `gen_notes.py` | `drill/data/notes.js` | `notes/*.md` をアプリに埋め込む |
| `gen_anaume2.py` | `drill/data/anaume2.js` | 条文穴埋め（速答）約3,900問 |
| `gen_ref.py` | `drill/data/ref.js` | 条文・論点 → 読むべき資料の対応表 |
| `gen_qref.py` | `drill/data/qref.js` | 解説のない問題 → 根拠の条（引用と本文の一致から） |
| `gen_jobun.py` | `drill/data/jobun.js` | その条の原文（法令XMLから。gen_qref のあとに流す） |
| `gen_print.py` | `drill/print*.html` | 紙で読むための印刷版（リンクを資料番号に置き換える） |
| `stale.py` | `drill/data/stale.js` | 改正で答えが変わった過去問に注意書きを付ける |
| `gen_sw.py` | `drill/sw.js` | 配信ファイルの内容からキャッシュ版数を決める |

**`notes/` のうち 95・96・97・A0・A1 と、各科目ノートの `<!-- TREND -->` 節は自動生成。**
直接編集しても再生成で消えるので、生成スクリプト側を直すこと。

## 元データの範囲について

公式サイトが載せているのは**その年の分だけ**で、過去問の一覧は無い。手元にあるのは
第49〜57回（平成29〜令和7年）の9年分。第48回以前は公式には取れない。

9年で足りるかは測ってある（`artgap.py` の年度別集計）。ある年の出題論点のうち
過去の回にも出ていた割合は、履歴4年で50%、5年で58%、8年でも58%と**頭打ち**になる。
930条のうち**64%は9年間で1回しか出ていない**ので、遡っても「1回だけ出た条」が
増えるだけで、予測の精度は上がらない。

むしろ古い過去問は改正で答えが変わる。9年分の中でも208問がそれに当たるので、
`stale.py` で注意書きを付けている。

## 検査

`review_notes.py` `review2.py` `review3.py` `review4.py` `review5.py`
資料の穴を別々の観点から機械的に洗い出す。
