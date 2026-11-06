"""アニメ語り図書館のビルド
  python3 _tools/build.py
_anime/*.md（記事）と _transcripts/*.md（発言全文）から
  anime/<slug>.html … 記事ページ
  anime.html        … 一覧ページ
を生成します。必要: pip install markdown pyyaml
"""
import html, json, re, sys
from pathlib import Path
import markdown, yaml

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "_tools"
SITE = "https://cotton-100.github.io"
# チャンネルの分類（一覧ページの絞り込みボタンの並び順）
CATEGORIES = ["積みアニメ", "布教解説", "アニメ発掘", "視聴供養", "演出解剖", "再視聴・再評価"]

HEAD_COMMON = """<link rel="icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=Shippori+Mincho+B1:wght@500;700;800&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/anime/library.css">"""

def header(current):
    cur = ' aria-current="page"' if current == "library" else ""
    return f"""<div class="lib-top"><div class="inner">
  <a class="logo" href="/"><picture><source srcset="/logo.webp" type="image/webp"><img src="/logo.png" alt="幕張ことは" width="640" height="220"></picture></a>
  <nav aria-label="サイト内メニュー"><a href="/">ホーム</a><a href="/anime.html"{cur}><span class="lg">アニメ語り</span>図書館</a><a href="/quiz.html"><span class="lg">幕張ことは杯</span><span class="sm">クイズ</span></a><a href="https://www.youtube.com/@cotton-100" target="_blank" rel="noopener">YouTube</a></nav>
</div></div>"""

FOOTER = """<footer class="lib-foot">
  <picture><source srcset="/logo.webp" type="image/webp"><img class="mark" src="/logo.png" alt="幕張ことは ロゴ" width="640" height="220" loading="lazy"></picture>
  <div class="name">幕張ことは &nbsp;/&nbsp; MAKUHARI KOTOHA</div>
  <div class="links"><a href="/">公式サイト</a><a href="/anime.html">アニメ語り図書館</a><a href="/quiz.html">幕張ことは杯</a><a href="https://www.youtube.com/@cotton-100" target="_blank" rel="noopener">YouTube</a><a href="https://x.com/cotton_makuhari" target="_blank" rel="noopener">X</a></div>
  <p class="note">記事は配信での幕張ことはの発言をもとに構成しています。作品の権利は各権利者に帰属します。</p>
  <div class="copy">© COTTON-100 &nbsp;ALL RIGHTS RESERVED</div>
</footer>"""

def fmt(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    left = re.findall(r"\{\{\w+\}\}", tpl)
    assert not left, f"テンプレートの埋め忘れ: {left}"
    return tpl

def load(md_path):
    _, fm, body = md_path.read_text(encoding="utf-8").split("---", 2)
    meta = yaml.safe_load(fm)
    meta["streamed"] = str(meta["streamed"])
    # 配信日（streamed）と記事の公開日（published）・更新日（updated）は分けて持つ
    meta["published"] = str(meta.get("published") or meta["streamed"])
    meta["updated"] = str(meta.get("updated") or meta["published"])
    meta["_body"] = body.strip()
    meta["_url"] = f"{SITE}/anime/{meta['slug']}.html"
    return meta

def render_article(meta, all_meta):
    vid, body = meta["video_id"], meta["_body"]

    highlights = []
    if "<!-- highlights -->" in body:
        body, hl = body.split("<!-- highlights -->", 1)
        highlights = [l[2:].strip() for l in hl.strip().splitlines() if l.startswith("- ")]

    chapters = []
    spoiler_at = body.find('class="spoiler-note"')
    def heading(m):
        t = int(m.group(3))
        after = spoiler_at != -1 and m.start() > spoiler_at
        chapters.append((len(m.group(1)), m.group(2).strip(), t, after))
        return f"{m.group(1)} {m.group(2).strip()} {{#t{t}}}"
    body = re.sub(r"^(#{2,3}) (.+?) <!-- t=(\d+) -->\s*$", heading, body, flags=re.M)
    body_html = markdown.markdown(body, extensions=["attr_list", "extra"])

    def add_btn(m):
        tag, attrs, inner = m.groups()
        t = re.search(r'id="t(\d+)"', attrs)
        if not t:
            return m.group(0)
        t = t.group(1)
        return (f'<{tag} id="t{t}">{inner}<a class="jump" href="https://www.youtube.com/watch?v={vid}&amp;t={t}s" '
                f'data-t="{t}">▶ {fmt(t)}</a></{tag}>')
    body_html = re.sub(r"<(h[23])([^>]*)>(.*?)</\1>", add_btn, body_html)

    toc_items, marked = [], False
    for lv, tx, t, after in chapters:
        if after and not marked:
            toc_items.append('<li class="toc-spoiler">ここから先は結末に触れています</li>')
            marked = True
        toc_items.append(f'<li class="lv{lv}"><a href="#t{t}"><span class="tc">{fmt(t)}</span>{html.escape(tx)}</a></li>')
    toc = "\n".join(toc_items)

    transcript_html = ""
    tr_path = ROOT / "_transcripts" / f"{meta['slug']}.md"
    if tr_path.exists():
        tr = tr_path.read_text(encoding="utf-8")
        tr = re.sub(r'<p class="ts"><a href="#" data-t="(\d+)">[^<]*</a></p>',
                    lambda m: f'<p class="ts"><a href="https://www.youtube.com/watch?v={vid}&amp;t={m.group(1)}s" data-t="{m.group(1)}">{fmt(m.group(1))}</a></p>', tr)
        tr = re.sub(r"（コメント：(.+?)）", r'<span class="cmt">\1</span>', tr)
        tr = re.sub(r"〔注：(.+?)〕", r'<span class="fix">\1</span>', tr)
        transcript_html = markdown.markdown(tr)

    # 関連：タグか分類が重なる他の記事
    mine = set(meta.get("tags", []))
    rel = [o for o in all_meta if o is not meta and (mine & set(o.get("tags", [])) or o.get("category") == meta.get("category"))]
    rel.sort(key=lambda o: -len(mine & set(o.get("tags", []))))
    related = ('<ul class="links">' + "".join(f'<li><a href="/anime/{o["slug"]}.html">{html.escape(o["title"])}</a></li>' for o in rel[:5]) + "</ul>"
               if rel else '<p class="soon">同じテーマの記事は準備中です。</p>')

    start, end = meta["segment"]
    clips = sorted(((lv, tx, t) for lv, tx, t, _ in chapters), key=lambda c: c[2])
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": meta["title"], "description": meta["description"],
         "datePublished": meta["published"], "dateModified": meta["updated"], "inLanguage": "ja", "mainEntityOfPage": meta["_url"],
         "image": f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",
         "author": {"@type": "Person", "name": "幕張ことは", "url": SITE + "/"},
         "isPartOf": {"@type": "CollectionPage", "name": "アニメ語り図書館", "url": SITE + "/anime.html"},
         "about": {"@type": "CreativeWork", "name": meta["work"]},
         "video": {"@id": meta["_url"] + "#video"}},
        {"@type": "VideoObject", "@id": meta["_url"] + "#video", "name": meta["stream_title"],
         "description": meta["description"], "uploadDate": meta["streamed"],
         "thumbnailUrl": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
         "embedUrl": f"https://www.youtube.com/embed/{vid}", "contentUrl": f"https://www.youtube.com/watch?v={vid}",
         "hasPart": [{"@type": "Clip", "name": tx, "startOffset": t,
                      "endOffset": clips[i + 1][2] if i + 1 < len(clips) else end,
                      "url": f"https://www.youtube.com/watch?v={vid}&t={t}s"} for i, (lv, tx, t) in enumerate(clips)]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "幕張ことは 公式サイト", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "アニメ語り図書館", "item": SITE + "/anime.html"},
            {"@type": "ListItem", "position": 3, "name": meta["work"], "item": meta["_url"]}]},
    ]}

    return fill((TOOLS / "article.html").read_text(encoding="utf-8"),
        robots='<meta name="robots" content="noindex">' if meta.get("status") == "draft" else "",
        title=html.escape(meta["title"]), subtitle=html.escape(meta.get("subtitle", "")),
        description=html.escape(meta["description"]), url=meta["_url"], work=html.escape(meta["work"]),
        category=html.escape(meta.get("category", "")), work_info=html.escape(meta.get("work_info", "")),
        spoiler=html.escape(meta.get("spoiler", "")), streamed=meta["streamed"].replace("-", "."),
        published=meta["published"].replace("-", "."),
        note=(f'<dt>補足</dt><dd>{html.escape(meta["note"])}</dd>' if meta.get("note") else ""),
        stream_title=html.escape(meta["stream_title"]), video_id=vid, start=start, toc=toc, body=body_html,
        highlights="\n".join(f"<li>{html.escape(h)}</li>" for h in highlights),
        tags="".join(f"<li>#{html.escape(t)}</li>" for t in meta.get("tags", [])),
        related=related, transcript=transcript_html,
        jsonld=json.dumps(ld, ensure_ascii=False, indent=1),
        head_common=HEAD_COMMON, header=header("article"), footer=FOOTER)

def render_library(all_meta):
    books = []
    for m in sorted(all_meta, key=lambda m: m["streamed"], reverse=True):
        words = " ".join([m["work"], m["title"], m.get("subtitle", ""), m.get("work_info", ""), " ".join(m.get("tags", []))])
        books.append(f"""<li class="book" data-cat="{html.escape(m.get('category', ''))}" data-streamed="{m['streamed']}" data-published="{m['published']}" data-words="{html.escape(words.lower())}"><a href="/anime/{m['slug']}.html">
  <div class="thumb" style="background-image:url('https://i.ytimg.com/vi/{m['video_id']}/hqdefault.jpg')" role="img" aria-label="{html.escape(m['stream_title'])}"></div>
  <div class="meta">
    <div class="row"><span class="cat">{html.escape(m.get('category', ''))}</span><span>配信 {m['streamed'].replace('-', '.')}</span><span>記事化 {m['published'].replace('-', '.')}</span></div>
    <h3>{html.escape(m['work'])}</h3>
    <p>{html.escape(m.get('subtitle', ''))}</p>
    <p class="book-spoiler"><span class="spoiler">ネタバレ：{html.escape(m.get('spoiler', 'なし'))}</span></p>
    <div class="tags">{' '.join('#' + html.escape(t) for t in m.get('tags', [])[:4])}</div>
  </div>
</a></li>""")
    used = {m.get("category") for m in all_meta}
    filters = ['<button type="button" aria-pressed="true" data-cat="">すべて</button>'] + [
        f'<button type="button" aria-pressed="false" data-cat="{c}"{"" if c in used else " disabled"}>{c}</button>' for c in CATEGORIES]
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "アニメ語り図書館",
          "url": SITE + "/anime.html", "inLanguage": "ja",
          "author": {"@type": "Person", "name": "幕張ことは", "url": SITE + "/"},
          "mainEntity": {"@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": m["_url"], "name": m["title"]}
              for i, m in enumerate(sorted(all_meta, key=lambda m: m["streamed"], reverse=True))]}}
    return fill((TOOLS / "library.html").read_text(encoding="utf-8"),
        count=len(all_meta), books="\n".join(books), filters="\n".join(filters),
        jsonld=json.dumps(ld, ensure_ascii=False, indent=1),
        head_common=HEAD_COMMON, header=header("library"), footer=FOOTER)

REQUIRED = ["title", "slug", "work", "video_id", "stream_title", "streamed", "segment", "category", "description"]

def validate(all_meta, paths):
    """記事を増やすときの事故（上書き・秒数の範囲外・書き忘れ）を生成前に止める"""
    errors, seen = [], {}
    for m, p in zip(all_meta, paths):
        name = p.name
        for k in REQUIRED:
            if not m.get(k):
                errors.append(f"{name}: {k} がありません")
        slug = m.get("slug", "")
        if slug != p.stem:
            errors.append(f"{name}: slug「{slug}」がファイル名と違います（{p.stem}.md にそろえてください）")
        if slug in seen:
            errors.append(f"{name}: slug「{slug}」が {seen[slug]} と重複しています（別の記事を上書きしてしまいます）")
        seen[slug] = name
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(m.get("video_id", ""))):
            errors.append(f"{name}: video_id「{m.get('video_id')}」がYouTubeの動画IDの形ではありません")
        for k in ("streamed", "published", "updated"):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", m[k]):
                errors.append(f"{name}: {k}「{m[k]}」は YYYY-MM-DD で書いてください")
        if m["published"] < m["streamed"]:
            errors.append(f"{name}: published（記事化日）が streamed（配信日）より前になっています")
        if m.get("category") and m["category"] not in CATEGORIES:
            errors.append(f"{name}: category「{m['category']}」は分類一覧（{'、'.join(CATEGORIES)}）にありません")
        seg = m.get("segment") or [0, 0]
        if len(seg) != 2 or not seg[0] < seg[1]:
            errors.append(f"{name}: segment は [開始秒, 終了秒] で、開始 < 終了にしてください")
            continue
        for t in re.findall(r"<!-- t=(\d+) -->", m["_body"]):
            if not seg[0] <= int(t) <= seg[1]:
                errors.append(f"{name}: 見出しの t={t}（{fmt(t)}）が配信の対象範囲 {fmt(seg[0])}〜{fmt(seg[1])} の外です")
        tr = ROOT / "_transcripts" / f"{slug}.md"
        if not tr.exists():
            errors.append(f"{name}: 発言全文 _transcripts/{slug}.md がありません")
        else:
            for t in re.findall(r'data-t="(\d+)"', tr.read_text(encoding="utf-8")):
                if not seg[0] - 60 <= int(t) <= seg[1] + 60:
                    errors.append(f"_transcripts/{slug}.md: 時刻 {fmt(t)} が対象範囲の外です")
        if "<!-- highlights -->" not in m["_body"]:
            errors.append(f"{name}: 「ことはの注目ポイント」（<!-- highlights -->）がありません")
    if errors:
        print("入力チェックで止めました：", *errors, sep="\n  - ")
        sys.exit(1)

def main():
    check = "--check" in sys.argv
    paths = sorted((ROOT / "_anime").glob("*.md"))
    all_meta = [load(p) for p in paths]
    validate(all_meta, paths)
    if check:
        # 公開中のHTMLが、今の記事データから作り直したものと一致するか（再生成し忘れの検出）
        outputs = {ROOT / "anime" / f"{m['slug']}.html": render_article(m, all_meta) for m in all_meta}
        outputs[ROOT / "anime.html"] = render_library(all_meta)
        stale = [p for p, v in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != v]
        known = {p.name for p in outputs}
        orphans = [p for p in (ROOT / "anime").glob("*.html") if p.name not in known]
        for p in stale:
            print("再生成が必要：", p.relative_to(ROOT))
        for p in orphans:
            print("元の記事がないHTML：", p.relative_to(ROOT))
        if stale or orphans:
            print("→ python3 _tools/build.py を実行してからコミットしてください")
            sys.exit(1)
        print(f"OK：{len(all_meta)}記事と一覧はすべて最新です")
        return
    (ROOT / "anime").mkdir(exist_ok=True)
    for m in all_meta:
        out = ROOT / "anime" / f"{m['slug']}.html"
        out.write_text(render_article(m, all_meta), encoding="utf-8")
        print(out.relative_to(ROOT), "（下書き：検索除け中）" if m.get("status") == "draft" else "")
    (ROOT / "anime.html").write_text(render_library(all_meta), encoding="utf-8")
    print("anime.html")

if __name__ == "__main__":
    main()
