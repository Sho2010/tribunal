# 技術仕様

**いま保証している振る舞い**を書く。外から観測できる契約と受け入れ条件。

- 実装された振る舞いを定義するのは**コードとテスト**。spec はその次
- 決定の理由は `.claude/skills/tribunal-decisions`。あれは現在の振る舞いを定義しない
- 食い違っていたら、実装に合わせて spec を直す

**コードとテストだけで契約が伝わるなら spec を書かない。** 書くのは、
複数のファイルに分かれていて 1 箇所を読んでも分からないもの、
または「やらない」ことが保証になっているもの。

| 領域 | 仕様 |
| --- | --- |
| Rule / Strategy の境界 | [知識の境界](knowledge-boundary.md) |
| 質問の振り分け | [intent routing](intent-routing.md) |

## 書き方

prompt（`application/*/prompts/*.md`）は**アプリケーション実装**であって spec ではない。
spec 側には「どの protocol が適用されるか」を書き、protocol の中身（マーカー名、文言、手順）は写さない。
そうしないと prompt を直すたびに spec も直すことになり、二重管理になる。
