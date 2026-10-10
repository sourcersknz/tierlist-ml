# MLBB ティア＆カウンター表

Mobile Legends: Bang Bang の統計データから、ティア表と対面有利ヒーローを表示するサイトです。

公開URL: https://hyke-cafe.github.io/mlbb-tier/

## 構成

| ファイル | 役割 |
|---|---|
| `index.html` | 公開されるサイト本体（**自動生成。直接編集しない**） |
| `template.html` | サイトの雛形。見た目やロジックを直すのはこちら |
| `data/master.json` | ヒーローの日本語名・レーン・main（主レーン） |
| `scripts/update.py` | データ取得とサイト生成 |
| `.github/workflows/update.yml` | 自動更新の設定 |
| `data/snapshots/` | 日次スナップショット（メタ推移の記録） |

## 更新の仕組み

6時間ごとに自動実行されます。手動で動かすには、
GitHubの **Actions** タブ → **データ更新** → **Run workflow**。

`data/master.json` や `template.html` を編集してコミットすると、
その時点でも自動的に再生成されます。

## ヒーローの日本語名・レーンを変えたい

`data/master.json` を編集します。

```json
"23": { "name": "グールド", "en": "Gord", "lanes": ["mid"], "main": "mid" }
```

- `name` … 表示名
- `lanes` … 所属レーン（複数可）
- `main` … 主レーン。`roam` / `exp` / `jg` / `mid` / `gold`

新ヒーローが追加されると、更新ログに
「台帳に無いヒーロー」として id と英語名が表示されます。
その id を master.json に追記してください。

## データ出典

Mobile Legends: Bang Bang 公式統計 (© Moonton)
