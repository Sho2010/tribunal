# 知識の境界

Rule 回答に非公式な情報が混ざらないことを保証する。
この保証は複数の層に分かれて実装されているため、1 ファイルを読んでも全体が見えない。

## 要件

- Rule 質問には **Rule Adjudicator Protocol** が適用され、回答は protocol が定める形式に従う
- Strategy 質問には **Strategy Analyst Protocol** が適用される。Rule Adjudicator を流用しない
- Store はゲームごと・区分（rule / strategy）ごとに `games/games.yaml` の `stores` で宣言する
- Rule 回答の根拠は **そのゲームの Rule Store のみ**。Strategy Store を根拠にしない
- Strategy 回答は、戦略資料を公式ルールとして提示しない
- **ある区分の Store が未設定のとき、別の区分や別のゲームの Store で代替しない**
  - Rule Store が未設定のゲーム → 回答の対象にしない。対象が 1 つも無ければ起動時に落ちる
  - Strategy Store が未設定のゲーム → strategy 質問は retriever を呼ばずに「答えられない」と返る
- **複数ゲームの Store をまとめて検索しない。** 対象ゲームを 1 つに決められなければ「答えられない」と返る
- Rule 回答の根拠に使える authority は `official` / `publisher` まで

## 受け入れ条件

```text
Strategy Store が未設定のゲームで、戦略と判定される質問を投げる
 → Rule Store を検索しない
 → 戦略資料が未整備である旨が返る
```

```text
どのゲームにも Rule Store が設定されていない状態で起動する
 → 起動に失敗する（Strategy Store があっても代替しない）
```

```text
Rule Store が設定されたゲームが複数あり、対象ゲームを指定せずに質問する
 → どの Store も検索しない
 → ゲームを特定できない旨が返る
```

```text
ルール裁定を求める質問が Strategy として処理された場合
 → その場で裁定を下さず、ルール資料での確認が必要だと伝える
```

## 保証していないこと

- **ユーザー経路で対象ゲームを指定する手段が無い。** Slack からは `game_id` を渡していないため、
  Rule Store が設定されたゲームが 2 つ以上あると、すべての質問が「特定できない」になる。
  **これは意図した仕様ではなく未解決の欠落。** 解決には GameResolver が要る
  （`docs/future/game-resolver.md`）
- 回答内容の正しさ。protocol は手順を強制するが、結論の正しさは保証しない

## 関連

決定の理由: `tribunal-decisions` の 0004 / 0006 / 0007 / 0020
