"""SBV字幕 → 発言全文の下書き（Markdown）
使い方: python3 _tools/transcript.py captions.sbv 開始秒 終了秒 [辞書.tsv] > _transcripts/<slug>.md

自動でやること
- [音楽] を削除、[笑い] を（笑）に
- 視聴者へのあいさつ定型文を削除（ハンドル名を記事に残さないため）
- 「え、」「あの、」「ま、」「うん。」などの言い淀み・相づちを削除
- 辞書（誤変換→正しい表記、タブ区切り）で固有名詞を補正
- 約60秒ごとにタイムスタンプ（動画へのリンク）を付け、その中を2〜3文ごとの段落に分ける

これは下書きです。仕上げとして、AI（Claude）に次の方針で整えてもらいます（README参照）。
- 明らかな誤字脱字を直す／意味をなさない断片（「あ」「や」など）は削除するか整える
- 話し言葉の口調・言い回しはそのまま残す（要約や言い換えはしない）
- 読みやすいように段落を分ける
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
B = r"(?:(?<=[。、？?！!」）])|^)"   # 文や節の頭
FILLERS = [
    B + r"(?:え|えー|ええ|えっと|えーと|ま|まあ|あの|あのー|その|うん|うーん|ほ|ほい|お|あ|や|う|こ|は|へ|ん)、",
    B + r"(?:はい|うん|ね|そう|うんうん)。",
]

def clean(text, pairs):
    text = text.replace("[音楽]", "").replace("[笑い]", "（笑）").replace("[咳払い]", "")
    text = re.sub(r"\[\s*_+\s*\]", "", text)
    for a, b in pairs:
        text = text.replace(a, b)
    for g in GREETING:
        text = re.sub(g, "", text)
    for _ in range(4):
        for f in FILLERS:
            text = re.sub(f, "", text)
    text = text.replace("?", "？").replace("!", "！")
    text = re.sub(r"(（笑）)+", "（笑）", text)
    text = re.sub(r"([、。])\1+", r"\1", text)
    text = re.sub(r"、。", "。", text)
    return text.strip("、 ")

def paragraphs(text, size=110):
    sents = re.findall(r"[^。？！]+[。？！]?(?:（笑）)?", text)
    out, cur = [], ""
    for s in sents:
        cur += s
        if len(cur) >= size:
            out.append(cur); cur = ""
    if cur:
        out.append(cur)
    return out

def fmt(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"

def main():
    path, start, end = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    pairs = load_dict(sys.argv[4] if len(sys.argv) > 4 else None)
    cues = [(t, x) for t, x in parse(path) if start <= t < end]
    blocks, cur, cur_t = [], [], None
    for t, x in cues:
        if cur_t is None:
            cur_t = t
        cur.append(x)
        if t - cur_t >= 60 and x.rstrip().endswith(("。", "?", "？")):
            blocks.append((cur_t, "".join(cur))); cur, cur_t = [], None
    if cur:
        blocks.append((cur_t, "".join(cur)))
    for t, x in blocks:
        body = clean(x, pairs)
        if body:
            print(f'<p class="ts"><a href="#" data-t="{int(t)}">{fmt(t)}</a></p>\n')
            for p in paragraphs(body):
                print(p + "\n")

if __name__ == "__main__":
    main()
