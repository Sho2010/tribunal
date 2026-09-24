---
name: image-pdf-to-markdown
description: テキストを持たない画像 PDF（スキャンしたルールブック、画像だけの攻略本）を、ページマーカー付きの 1 つの Markdown に変換する。OCRmyPDF → Docling → 問題ページの検出 → LLM で照合 → 組み立て、を scripts/rag-preprocess/ の部品で順に流す。画像 PDF を Vector Store に載せる Markdown にしたいときに使う。
---

# 画像 PDF を Markdown にする

`scripts/rag-preprocess/` の部品を順に流す。部品は 1 つの変換だけをし、出力があればスキップするので、
どの段で止まっても同じコマンドで続きから流せる。

## 守ること

- **生成物はすべて `temp/` の下の 1 つのディレクトリに置く**（以下 `$RUN`）。書籍の派生物なので、それ以外の場所に書かない
- **LLM を呼ぶ前に必ず止めて、照合するページ数を示してユーザーの了承を取る**。了承なしに照合の段へ進まない
- **API key を読まない・表示しない**。key のファイルを開く、`echo` する、ログに出す、をしない
- 最終出力を `games/<game_id>/{rule,strategy}/` へ置くのも、Vector Store へ載せるのもユーザーがやる

## 始める前に聞くこと

まとめて 1 回で聞く。

1. **原本の PDF**（`games/<game_id>/raw/` にあることが多い）
2. **`$RUN`** — `temp/` の下のディレクトリ。名前はユーザーに合わせる
3. **見開きか**（1 ページに左右 2 ページ分が並んでいるか）。分からなければ `pdfinfo -f 1 -l 3 <pdf>` の
   ページ寸法（横長か）を見せて確認する
4. **照合するページ** — 全ページ / 問題ページだけ。ルールブックは全ページを勧める
   （問題ページに掛からないページにも OCR の誤読が残る）。数百ページの本は問題ページだけを勧める
5. **LLM** — `claude` / `openai`

## 手順

`S=scripts/rag-preprocess` とする。

### 1. 見開きを分ける（見開きのときだけ）

```sh
$S/split-spreads.sh <raw.pdf> $RUN/split.pdf
```

以降は `$RUN/split.pdf` を原本として扱う。マーカーのページ番号も分けた後の番号になる。
見開きでなければ、以降の `$RUN/split.pdf` を原本の PDF に読み替える。

### 2. OCR と Docling

```sh
$S/run-ocr.sh $RUN/split.pdf $RUN/ocr.pdf
$S/run-docling.sh $RUN/ocr.pdf $RUN/docling
$S/docling-markdown.sh $RUN/docling/ocr.json >$RUN/docling.md
```

OCR は 1 ページ数十秒かかる。数ページを超えるときは background で流す。
テキスト層を持つ PDF は `run-ocr.sh` が止まる。それは変換の対象外なのでユーザーに伝えて終える。

### 3. 照合するページを決める

```sh
$S/detect-problem-pages.sh $RUN/docling/ocr.json >$RUN/problems.tsv
```

- 問題ページだけ: `awk -F'\t' 'NR > 1 && $5 != "" { print $1 }' $RUN/problems.tsv >$RUN/pages.txt`
- 全ページ: `seq 1 "$(qpdf --show-npages $RUN/split.pdf)" >$RUN/pages.txt`

### 4. ページごとの入力を作る

`$RUN/pages.txt` の各ページ N について:

```sh
mkdir -p $RUN/pages
pdftoppm -f N -l N -r 200 -png -singlefile $RUN/split.pdf $RUN/pages/pN
pdftotext -f N -l N -layout $RUN/ocr.pdf $RUN/pages/pN.ocr.txt
jq -r --argjson n N '.texts[] | select(.prov[0].page_no == $n) | .text' $RUN/docling/ocr.json >$RUN/pages/pN.docling.txt
```

画像は照合する側（`$RUN/split.pdf`）から作る。OCR 済みの PDF からではない。

### 5. ここで止まって了承を取る

ユーザーに示す:

- 照合するページ数と、そのページ番号
- 使う LLM とモデル（`claude` は既定 `claude-opus-5`、`openai` は既定 `gpt-5`）
- 目安: Claude で 1 ページ 入力 7〜10k / 出力 1.5〜4k トークン、20 秒前後。4 並列で流す

了承を得たら key を用意する。環境変数（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`）が既にあるかは
`[[ -n "${ANTHROPIC_API_KEY:-}" ]] && echo set` のように値を出さずに確かめる。無ければ、
**ユーザー自身のターミナルで**（`!` では入力を受けられない）次を実行してもらう:

```sh
read -rs k && printf '%s' "$k" > $RUN/.llm-key && chmod 600 $RUN/.llm-key
```

`printf '%s' 'sk-...'` のように key を書いたコマンドを `!` で実行させない（会話に key が残る）。

### 6. 照合する

key がファイルにあるとき（`claude` の例。`openai` なら変数名を `OPENAI_API_KEY` にする）:

```sh
ANTHROPIC_API_KEY="$(<$RUN/.llm-key)" TRIBUNAL_LLM=claude xargs -P 4 -I{} \
    $S/reconcile-page.sh $RUN/pages/p{}.png $RUN/pages/p{}.ocr.txt $RUN/pages/p{}.docling.txt {} $RUN/pages/p{}.md \
    <$RUN/pages.txt
```

- 失敗したページは出力を書かない。同じコマンドをもう一度流すと、そのページだけやり直す
- 2 回続けて同じページが失敗したら、stderr を見せてユーザーに判断を仰ぐ

### 7. 組み立てて確かめる

```sh
$S/assemble.py $RUN/docling.md $(sed 's|.*|'"$RUN"'/pages/p&.md|' $RUN/pages.txt) >$RUN/final.md
grep -c '^<!-- source_pdf_page: [0-9]* -->$' $RUN/final.md
qpdf --show-npages $RUN/split.pdf
```

マーカー数と総ページ数が一致しなければ `final.md` を渡さない。`assemble.py` が止まったときも同じ。

### 8. 終える

- `$RUN/final.md` のパスを伝える
- 照合したページのうち 1 ページについて、`$RUN/docling.md` の同じページと並べて違いを短く示す
- key のファイルを作ったなら、ユーザーに削除を促す: `rm $RUN/.llm-key`
