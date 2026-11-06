"""SBV字幕 → 発言全文（Markdown）
使い方: python3 transcript.py captions.sbv 開始秒 終了秒 [辞書.tsv] > out.md
- [音楽] を削除、[笑い] を（笑）に
- 視聴者へのあいさつ定型文を削除（ハンドル名を記事に残さないため）
- 単独の「え、」「えー、」などの言い淀みを削除
- 辞書（誤変換→正しい表記、タブ区切り）で固有名詞を補正
- 約90秒ごとに段落を切り、タイムスタンプ（動画へのリンク用）を付与
"""
import re, sys

def parse(path):
    src = open(path, encoding="utf-8").read()
    for b in re.split(r"\n\s*\n", src.strip()):
        lines = b.split("\n")
        h, m, s = lines[0].split(",")[0].split(":")
        yield int(h) * 3600 + int(m) * 60 + float(s), "".join(lines[1:])

def load_dict(path):
    pairs = []
    if path:
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line and not line.startswith("#") and "\t" in line:
                a, b = line.split("\t", 1)
                pairs.append((a, b))
    return pairs

GREETING = [
    r"[^。、]{1,15}さん[、]?(こんにちは|こんばんは|こんばんわ)(です)?。?(ようこそお越しいただきま[^。]*。)?(お越しいただきま[^。]*ありがとうございます。)?",
    r"ようこそお越しいただきました。",
    r"お越しいただきま(した|して)(。)?ありがとうございます。",
    r"[^。、]{1,15}さん[、]?お疲れ様でした。",
]
FILLER = r"(?:(?<=[。、？?！!])|^)(?:え|えー|えっと|ま|あの|うん)、"

def clean(text, pairs):
    text = text.replace("[音楽]", "").replace("[笑い]", "（笑）")
    for a, b in pairs:
        text = text.replace(a, b)
    for g in GREETING:
        text = re.sub(g, "", text)
    for _ in range(3):
        text = re.sub(FILLER, "", text)
    text = re.sub(r"(（笑）)+", "（笑）", text)
    text = re.sub(r"。{2,}", "。", text)
    return text.strip("、 ")

def fmt(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"

def main():
    path, start, end = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    pairs = load_dict(sys.argv[4] if len(sys.argv) > 4 else None)
    cues = [(t, x) for t, x in parse(path) if start <= t < end]
    # 先に全部つないで補正（字幕の改行で単語が割れるため）
    paras, cur, cur_t = [], [], None
    for t, x in cues:
        if cur_t is None:
            cur_t = t
        cur.append(x)
        if t - cur_t >= 90 and x.rstrip().endswith(("。", "?", "？")):
            paras.append((cur_t, "".join(cur)))
            cur, cur_t = [], None
    if cur:
        paras.append((cur_t, "".join(cur)))
    for t, x in paras:
        body = clean(x, pairs)
        if body:
            print(f'<p class="ts"><a href="#" data-t="{int(t)}">{fmt(t)}</a></p>\n\n{body}\n')

if __name__ == "__main__":
    main()
