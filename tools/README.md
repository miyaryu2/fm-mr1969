# tools

フィールドマップの開発用スクリプトです。アプリの動作には関係しません。

| ファイル | 役割 |
| --- | --- |
| `e2e.py` | 公開版を2台相当(iPhone・Android)で開き、共有・位置合わせ・圏外表示を自動テストする |
| `e2e_net.py` | 圏外中の送信・受信・表示を個別に確認する |
| `offline_test.py` | 手元のファイルに対して、圏外でもアプリとマップが開くかを確認する |
| `record.py` | 使い方の動画(`guide.mp4`)用に、アプリを自動操作して画面を1コマずつ書き出す |
| `check.py` | 手元のマニュアル2ページで、動画が再生できるかを確認する |

## 準備

Google Chrome が入っている Mac で、リポジトリの外に作業用フォルダを作って行います。

```
mkdir ~/fm-work && cd ~/fm-work
python3 -m venv venv
./venv/bin/pip install playwright imageio-ffmpeg
```

`imageio-ffmpeg` は動画の変換にだけ使います。テストだけなら `playwright` だけで足ります。

## テスト

```
./venv/bin/python ~/Projects/fm-mr1969/tools/e2e.py
./venv/bin/python ~/Projects/fm-mr1969/tools/e2e_net.py
./venv/bin/python ~/Projects/fm-mr1969/tools/offline_test.py ~/Projects/fm-mr1969
```

- `e2e.py` は項目ごとに `OK` か `NG` を表示します。「Android相当が圏外になり、戻ると共有が自動で再開する」は、テストツールが圏外を完全には再現できないため必ず `NG` になります。この項目は `e2e_net.py` の結果で判断します。
- `e2e.py` と `e2e_net.py` は、公開版と本番の共有サーバを使います。使い捨ての合言葉で接続し、終了時にデータを削除します。

## 動画の撮り直し

アプリの画面や操作を変えたら撮り直します。字幕の文言と操作の順番は `record.py` の中にあります。

```
./venv/bin/python ~/Projects/fm-mr1969/tools/record.py ~/Projects/fm-mr1969
FF=$(./venv/bin/python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -y -framerate 10 -i frames/f%05d.jpg -vf "scale=720:1280:flags=lanczos,fps=30,format=yuv420p" \
  -c:v libx264 -profile:v high -crf 25 -preset slow -movflags +faststart -an guide.mp4
"$FF" -y -i frames/f00590.jpg -vf "scale=720:1280:flags=lanczos" -q:v 5 guide-poster.jpg
./venv/bin/python ~/Projects/fm-mr1969/tools/check.py ~/Projects/fm-mr1969
```

- 1行目で `frames/` に画像が書き出されます(約1分)。
- できた `guide.mp4` と `guide-poster.jpg` を開発フォルダにコピーしてから、最後の行で再生を確認します。
- 録画には、公式マップではなくアプリ内蔵のサンプルフィールドを使います。公式画像を動画に入れて再配布しないためです。
- 録画中は、デモ用の合言葉 `akagumi-demo` で本番の共有サーバに接続し、終了時にデータを削除します。
