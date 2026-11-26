"""アニメ語り記事のページ閲覧数を集計して _data/views.json に保存する
  CF_API_TOKEN=... CF_ACCOUNT_ID=... python3 _tools/fetch_views.py
サイトに入っている Cloudflare Web Analytics の計測データ（ページの読み込み回数）を
GraphQL API で日ごとに取り、前回までの合計に足していきます。
（Cloudflare 側のデータは保存期間に限りがあるため、合計はこのファイルに積み上げて持つ）
保存後に python3 _tools/build.py を実行すると、記事と一覧の日付の横に閲覧数が出ます。
GitHub Actions（.github/workflows/update-views.yml）が毎日自動で実行します。
"""
import json, os, re, sys, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_data" / "views.json"
HOST = "cotton-100.github.io"
FIRST_DAY = date(2026, 11, 1)  # 記事の公開を始めた月。初回はここから集計する
CHUNK = 30                     # 1回の問い合わせで取る日数

QUERY = """query ($account: String!, $host: String!, $start: Date!, $end: Date!) {
  viewer { accounts(filter: {accountTag: $account}) {
    rumPageloadEventsAdaptiveGroups(limit: 5000,
      filter: {requestHost: $host, date_geq: $start, date_leq: $end}) {
      count
      dimensions { requestPath }
    }
  } }
}"""


def norm(path):
    """/anime/x.html・/anime/x・/anime/x/ を同じページとして数える"""
    path = path.split("?")[0].split("#")[0].rstrip("/")
    return re.sub(r"\.html$", "", path)


def fetch(token, account, start, end):
    body = json.dumps({"query": QUERY, "variables": {
        "account": account, "host": HOST, "start": start.isoformat(), "end": end.isoformat()}}).encode()
    req = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", data=body,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    if res.get("errors"):
        sys.exit("Cloudflare APIのエラー: " + "; ".join(e.get("message", "") for e in res["errors"]))
    accounts = res["data"]["viewer"]["accounts"]
    if not accounts:
        sys.exit("アカウントが見つかりません（CF_ACCOUNT_ID とトークンの権限を確認してください）")
    counts = {}
    for g in accounts[0]["rumPageloadEventsAdaptiveGroups"]:
        p = norm(g["dimensions"]["requestPath"])
        if not p.startswith("/anime/"):
            continue
        counts[p] = counts.get(p, 0) + g["count"]
    return counts


def main():
    token, account = os.environ.get("CF_API_TOKEN"), os.environ.get("CF_ACCOUNT_ID")
    if not token or not account:
        sys.exit("CF_API_TOKEN と CF_ACCOUNT_ID を設定してください")
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"pages": {}}
    pages = data.get("pages", {})
    start = date.fromisoformat(data["through"]) + timedelta(days=1) if data.get("through") else FIRST_DAY
    end = datetime.now(timezone.utc).date() - timedelta(days=1)  # 集計が確定した前日（UTC）まで
    if start > end:
        print("新しく集計する日がありません")
        return
    d = start
    while d <= end:
        e = min(d + timedelta(days=CHUNK - 1), end)
        for p, n in fetch(token, account, d, e).items():
            pages[p] = pages.get(p, 0) + n
        d = e + timedelta(days=1)
    data = {"through": end.isoformat(), "pages": dict(sorted(pages.items()))}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{start}〜{end} を集計しました（{len(pages)}ページ）→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
