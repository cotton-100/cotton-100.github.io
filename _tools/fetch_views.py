"""アニメ語り記事の配信の再生数を取得して _data/views.json に保存する
  YOUTUBE_API_KEY=... python3 _tools/fetch_views.py
YouTube Data API v3（videos.list / part=statistics）を使います。
保存後に python3 _tools/build.py を実行すると、記事と一覧の日付の横に再生数が出ます。
GitHub Actions（.github/workflows/update-views.yml）が毎日自動で実行します。
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_data" / "views.json"


def video_ids():
    ids = []
    for p in sorted((ROOT / "_anime").glob("*.md")):
        m = re.search(r"^video_id:\s*['\"]?([A-Za-z0-9_-]{11})", p.read_text(encoding="utf-8"), re.M)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def main():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        sys.exit("YOUTUBE_API_KEY が設定されていません")
    ids, counts = video_ids(), {}
    for i in range(0, len(ids), 50):  # 1回のリクエストで50件まで
        q = urllib.parse.urlencode({"part": "statistics", "id": ",".join(ids[i:i + 50]), "key": key})
        with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/videos?{q}", timeout=30) as r:
            for item in json.load(r).get("items", []):
                if "viewCount" in item.get("statistics", {}):
                    counts[item["id"]] = int(item["statistics"]["viewCount"])
    if not counts:
        sys.exit("再生数を1件も取得できませんでした（APIキーや動画IDを確認してください）")
    data = {"fetched": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"),
            "videos": dict(sorted(counts.items()))}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(counts)}/{len(ids)}本の再生数を保存しました → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
