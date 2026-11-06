# アニメ語り図書館の作り方

`_` で始まるフォルダ（`_anime` `_transcripts` `_tools`）は GitHub Pages では公開されません。

## 1本追加する手順
1. YouTube Studio から字幕（.sbv）をダウンロード
2. 発言全文を作る（その作品を語っている範囲を秒で指定）
   python3 _tools/transcript.py captions.sbv 開始秒 終了秒 _tools/dict_<slug>.tsv > _transcripts/<slug>.md
3. 記事を `_anime/<slug>.md` に書く（AIに下書き → 本人が確認）
   - 見出しの末尾に `<!-- t=秒 -->` を付けると、▶ボタン・目次・動画の見どころ情報が入る
   - 末尾の `<!-- highlights -->` 以下の箇条書きが「ことはの注目ポイント」になる
   - `category` はチャンネルの分類（積みアニメ／布教解説／アニメ発掘／視聴供養／演出解剖／再視聴・再評価）
4. `python3 _tools/build.py` → `anime/<slug>.html` と `anime.html` が更新される
5. 確認が済んだら `status: draft` の行を消して再ビルド（記事の検索除けが外れる）

必要なもの: Python 3、`pip install markdown pyyaml`
