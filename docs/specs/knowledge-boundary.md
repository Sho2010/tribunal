# 知識の境界

Rule 回答に非公式な情報が混ざらないことを保証する。
この保証は複数の層に分かれて実装されているため、1 ファイルを読んでも全体が見えない。

## 要件

- Rule 質問には **Rule Adjudicator Protocol** が適用され、回答は protocol が定める形式に従う
- Strategy 質問には **Strategy Analyst Protocol** が適用される。Rule Adjudicator を流用しない
- Rule 回答の根拠は **Rule Store のみ**。Strategy Store を根拠にしない
- Strategy 回答は、戦略資料を公式ルールとして提示しない
- **一方の Store が未設定のとき、他方で代替しない**
  - Rule Store が未設定 → 起動時に落ちる
  - Strategy Store が未設定 → strategy 質問は retriever を呼ばずに「答えられない」と返る
- Rule 回答の根拠に使える authority は `official` / `publisher` まで

## 受け入れ条件

```text
Strategy Store 未設定の状態で、戦略と判定される質問を投げる
 → Rule Store を検索しない
 → 戦略資料が未整備である旨が返る
```

```text
Rule Store 未設定で起動する
 → 起動に失敗する（Strategy Store があっても代替しない）
```

```text
ルール裁定を求める質問が Strategy として処理された場合
 → その場で裁定を下さず、ルール資料での確認が必要だと伝える
```

## 保証していないこと

- **`game_id` による絞り込みは、現在ユーザー経路では効いていない。**
  retriever は `game_id` を受け取ればフィルタするが、Slack からは渡していないため
  Rule Store 全体を検索する。複数ゲームの資料を同じ Store に入れると混線しうる
- 回答内容の正しさ。protocol は手順を強制するが、結論の正しさは保証しない

## 関連

決定の理由: `tribunal-decisions` の 0004 / 0006 / 0007
