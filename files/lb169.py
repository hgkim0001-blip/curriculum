"""Vox-style motion graphic v2: 자동차의 변천사 (30s, 1920x1080, 30fps).

v1(make_video.py) 대비 변경
- 배경: assets/paper_bg.jpg(구겨진 종이) → Motion Tile 가로·세로 5배(미러 엣지) → wiggle(10, 1000)
- 폰트/색: MZ 감성의 굵은 폰트(G마켓 산스 Bold · SUIT Heavy · Gotham Black) + 형광 컬러
- 모든 소재: wiggle(1, 10), 등장 시 10프레임 동안 투명 → 불투명
- 최종: Posterize Time 5fps (30fps 영상이지만 초당 5번만 그림이 바뀜)
출력: car_history_vox_v2.mp4
"""
import math
import os
import random
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "images")
BG_PATH = os.path.join(HERE, "assets", "paper_bg.jpg")
OUT = os.path.join(HERE, "car_history_vox_v2.mp4")

W, H, FPS, DUR = 1920, 1080, 30, 30.0
POSTERIZE_FPS = 5                 # Posterize Time
FADE = 10 / FPS                   # 등장 불투명도 10프레임
EL_WIGGLE = (1, 10)               # 소재 wiggle(freq, amp)
BG_WIGGLE = (10, 1000)            # 배경 wiggle(freq, amp)
TILE = 5                          # Motion Tile 가로·세로 배수

# ---- palette: 잉크 + 형광 ----
INK = (17, 17, 17)
WHITE = (255, 255, 255)
LIME = (204, 255, 0)
PINK = (255, 46, 136)
BLUE = (41, 82, 255)
ORANGE = (255, 112, 0)

USER_FONTS = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts")


def find_font(*names):
    for n in names:
        for d in (USER_FONTS, r"C:\Windows\Fonts"):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise FileNotFoundError(names)


FONT_TITLE = find_font("GmarketSansTTFBold.ttf", "SUIT-Heavy.otf", "malgunbd.ttf")  # 한글 제목
FONT_KO = find_font("SUIT-Heavy.otf", "GmarketSansTTFBold.ttf", "malgunbd.ttf")     # 한글 부제·태그
FONT_NUM = find_font("Gotham-Black.otf", "Objective-Black.otf", "ariblk.ttf")       # 영문·숫자


def font(path, size):
    return ImageFont.truetype(path, size)


# ---- easing ----
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3


def ease_in_cubic(x):
    return clamp(x) ** 3


def ease_out_back(x, s=1.4):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def lerp(a, b, t):
    return a + (b - a) * t


# ---- wiggle (After Effects 방식: 초당 freq번, ±amp) ----
def _noise1d(x, seed):
    k = math.floor(x)
    f = x - k
    a = random.Random(seed * 7919 + k).uniform(-1, 1)
    b = random.Random(seed * 7919 + k + 1).uniform(-1, 1)
    return lerp(a, b, f * f * (3 - 2 * f))


def wiggle(t, seed, freq, amp):
    def axis(sd):
        return (_noise1d(t * freq, sd) + 0.5 * _noise1d(t * freq * 2, sd + 17)) / 1.5 * amp
    return axis(seed), axis(seed + 101)


# ---- scenes ----
SCENES = [
    dict(kind="title", start=0.0, end=4.0, img="s0_title.jpg", treat="warm"),
    dict(start=4.0, end=9.2, img="s1_1886.jpg", treat="sepia", year=1886, suffix="", accent=PINK,
         title="최초의 자동차", sub="카를 벤츠의 ‘페이턴트 모터바겐’", chip="최고 시속 16km"),
    dict(start=9.2, end=14.4, img="s2_1908.jpg", treat="sepia", year=1908, suffix="", accent=BLUE,
         title="포드 모델 T", sub="조립 라인이 연 대량생산 시대", chip="1,500만 대 판매"),
    dict(start=14.4, end=19.6, img="s3_1950s.jpg", treat="warm", year=1950, suffix="s", accent=ORANGE,
         title="자동차의 황금기", sub="고속도로, 교외, 화려한 테일핀", chip="자동차 = 자유"),
    dict(start=19.6, end=24.8, img="s4_1973.jpg", treat="faded", year=1973, suffix="", accent=PINK,
         title="오일 쇼크", sub="작고 연비 좋은 차로 방향 전환", chip="효율의 시대"),
    dict(start=24.8, end=30.0, img="s5_2020s.jpg", treat="none", year=2020, suffix="s", accent=BLUE,
         title="전기차와 자율주행", sub="엔진 대신 배터리, 운전자 대신 AI", chip="다음 140년은?", last=True),
]
TL_YEARS = [1880, 1886, 1908, 1955, 1973, 2024]


# ---- background: Motion Tile ×5 ----
def seamless(im, band=0.22):
    """원본과 반 칸 밀린(roll) 사본을 가장자리에서 섞어, 이어 붙여도 이음매가 없는 타일로 만든다."""
    h, w = im.shape[:2]
    shifted = np.roll(im, (h // 2, w // 2), axis=(0, 1))
    def ramp(n):
        x = np.minimum(np.arange(n), n - 1 - np.arange(n)) / (n * band)
        return np.clip(x, 0, 1)
    m = np.minimum(ramp(h)[:, None], ramp(w)[None, :])
    m = (m * m * (3 - 2 * m))[..., None]
    return (im * m + shifted * (1 - m)).astype(np.uint8)


def build_bg_tile():
    im = seamless(np.asarray(Image.open(BG_PATH).convert("RGB")).astype(np.float32))
    return np.ascontiguousarray(np.tile(im, (TILE, TILE, 1)))


def bg_frame(tile, t):
    th, tw = tile.shape[:2]
    wx, wy = wiggle(t, 4242, *BG_WIGGLE)
    x0 = int(clamp(tw / 2 - W / 2 + wx, 0, tw - W))
    y0 = int(clamp(th / 2 - H / 2 + wy, 0, th - H))
    return Image.fromarray(tile[y0:y0 + H, x0:x0 + W])


# ---- asset builders ----
def placeholder(name):
    im = Image.new("RGB", (1600, 900), (120, 115, 105))
    ImageDraw.Draw(im).text((60, 60), f"missing: {name}", font=font(FONT_KO, 60), fill=(240, 240, 240))
    return im


def treat(im, mode):
    if mode == "sepia":
        g = ImageEnhance.Contrast(ImageOps.grayscale(im)).enhance(1.15)
        im = ImageOps.colorize(g, black=(45, 32, 20), white=(245, 228, 196))
    elif mode == "warm":
        im = Image.blend(ImageEnhance.Color(im).enhance(0.9), Image.new("RGB", im.size, (255, 214, 150)), 0.06)
    elif mode == "faded":
        im = Image.blend(ImageEnhance.Color(im).enhance(0.75), Image.new("RGB", im.size, (240, 220, 190)), 0.08)
    return im


def make_card(path, mode, inner_w, angle, seed, tape_colors):
    """사진 → 흰 테두리 + 형광 테이프 + 그림자가 있는 회전된 카드 (RGBA)."""
    im = Image.open(path).convert("RGB") if os.path.exists(path) else placeholder(os.path.basename(path))
    iw, ih = im.size
    im = im.crop((0, 0, int(iw * 0.9), int(ih * 0.9)))  # 우하단 ✦ 워터마크 제거
    inner_h = int(inner_w * 9 / 16)
    im = treat(ImageOps.fit(im, (inner_w, inner_h), Image.LANCZOS), mode)
    b = 18
    card = Image.new("RGBA", (inner_w + 2 * b, inner_h + 2 * b), WHITE + (255,))
    card.paste(im, (b, b))
    ImageDraw.Draw(card).rectangle([0, 0, card.width - 1, card.height - 1], outline=INK + (255,), width=4)

    pad = 80
    cw, ch = card.size
    canvas = Image.new("RGBA", (cw + 2 * pad, ch + 2 * pad), (0, 0, 0, 0))
    # 팝한 하드 섀도(잉크색 오프셋) + 부드러운 그림자
    soft = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(soft).rectangle([pad + 10, pad + 16, pad + cw + 10, pad + ch + 16], fill=90)
    canvas.paste(Image.new("RGBA", canvas.size, (0, 0, 0, 255)), (0, 0), soft.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(canvas).rectangle([pad + 14, pad + 14, pad + cw + 14, pad + ch + 14], fill=INK + (255,))
    canvas.alpha_composite(card, (pad, pad))

    rng = random.Random(seed)
    for (tx, ty, ta), col in zip([(pad + 40, pad - 8, -32), (pad + cw - 40, pad - 8, 30)], tape_colors):
        tape = Image.new("RGBA", (170, 46), col + (225,))
        td = ImageDraw.Draw(tape)
        for i in range(0, 170, 6):
            td.line([(i, 0), (i, 3 + rng.randint(0, 3))], fill=(0, 0, 0, 0))
            td.line([(i, 46), (i, 43 - rng.randint(0, 3))], fill=(0, 0, 0, 0))
        tape = tape.rotate(ta, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(tape, (tx - tape.width // 2, ty - tape.height // 2 + 10))
    return canvas.rotate(angle, expand=True, resample=Image.BICUBIC)


def text_sprite(text, fnt, color, pad=6, stroke=0, stroke_fill=None, shadow=None):
    """shadow=(dx, dy, color): 스티커 느낌의 하드 섀도."""
    l, t, r, b = fnt.getbbox(text, stroke_width=stroke)
    sx, sy = (shadow[0], shadow[1]) if shadow else (0, 0)
    im = Image.new("RGBA", (r - l + 2 * pad + sx, b - t + 2 * pad + sy), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        d.text((pad - l + sx, pad - t + sy), text, font=fnt, fill=shadow[2],
               stroke_width=stroke, stroke_fill=shadow[2])
    d.text((pad - l, pad - t), text, font=fnt, fill=color, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def highlight_sprite(w, h, color, seed):
    rng = random.Random(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pts_top = [(x, rng.randint(0, 8)) for x in range(0, w + 1, 40)]
    pts_bot = [(x, h - rng.randint(0, 8)) for x in range(w, -1, -40)]
    ImageDraw.Draw(im).polygon(pts_top + pts_bot, fill=color + (255,))
    return im


def box_sprite(text, fnt, fg, bg, padx=26, pady=14, shadow=INK):
    ts = text_sprite(text, fnt, fg)
    im = Image.new("RGBA", (ts.width + 2 * padx + 8, ts.height + 2 * pady + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([8, 8, im.width - 1, im.height - 1], fill=shadow + (255,))
    d.rectangle([0, 0, im.width - 9, im.height - 9], fill=bg + (255,), outline=INK + (255,), width=4)
    im.alpha_composite(ts, (padx, pady))
    return im


def with_opacity(sprite, op):
    if op >= 0.999:
        return sprite
    s = sprite.copy()
    s.putalpha(s.getchannel("A").point(lambda v: int(v * op)))
    return s


def put(base, sprite, x, y, op=1.0):
    if op <= 0.001:
        return
    s = with_opacity(sprite, op)
    base.paste(s, (int(round(x)), int(round(y))), s)


# ---- timeline ----
TL_Y, TL_X0, TL_X1, TL_A, TL_B = 1005, 150, 1770, 1880, 2030


def tl_x(year):
    return TL_X0 + (year - TL_A) / (TL_B - TL_A) * (TL_X1 - TL_X0)


def draw_timeline(img, year, op, t):
    if op <= 0:
        return
    layer = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 55
    f = font(FONT_NUM, 24)
    d.line([(TL_X0, y), (TL_X1, y)], fill=INK + (255,), width=4)
    for yr in range(TL_A, TL_B + 1, 10):
        x = tl_x(yr)
        big = yr % 20 == 0
        d.line([(x, y - (13 if big else 8)), (x, y + (13 if big else 8))], fill=INK + (255,), width=3)
        if big:
            tw = d.textlength(str(yr), font=f)
            d.text((x - tw / 2, y + 20), str(yr), font=f, fill=INK + (255,))
    xm = tl_x(year)
    d.line([(TL_X0, y), (xm, y)], fill=BLUE + (255,), width=10)
    d.ellipse([xm - 16, y - 16, xm + 16, y + 16], fill=PINK + (255,), outline=INK + (255,), width=4)
    d.polygon([(xm - 12, y - 40), (xm + 12, y - 40), (xm, y - 24)], fill=INK + (255,))
    wx, wy = wiggle(t, 900, *EL_WIGGLE)
    put(img, layer, wx, TL_Y - 55 + wy, op)


# ---- main render ----
def build_assets():
    A = {"bg": build_bg_tile()}
    f_sub = font(FONT_KO, 42)
    tapes = [(LIME, PINK), (PINK, BLUE), (BLUE, LIME), (ORANGE, LIME), (LIME, PINK), (PINK, BLUE)]
    for i, s in enumerate(SCENES):
        p = os.path.join(IMG_DIR, s["img"])
        if s.get("kind") == "title":
            s["card"] = make_card(p, s["treat"], 1060, -2.5, i, tapes[i])
            s["t1"] = text_sprite("바퀴 위의 140년", font(FONT_TITLE, 132), INK)
            s["hl"] = highlight_sprite(s["t1"].width + 40, int(s["t1"].height * 0.62), LIME, 99)
            s["t2"] = box_sprite("자동차의 변천사  1886 - 2026", font(FONT_KO, 46), WHITE, PINK)
        else:
            s["card"] = make_card(p, s["treat"], 900, [3, -2.5, 2.5, -3, 2][(i - 1) % 5], i, tapes[i])
            size = 92
            while font(FONT_TITLE, size).getlength(s["title"]) > 640:
                size -= 2
            s["t_title"] = text_sprite(s["title"], font(FONT_TITLE, size), INK)
            s["hl"] = highlight_sprite(s["t_title"].width + 36, int(s["t_title"].height * 0.55), LIME, i)
            s["t_sub"] = text_sprite(s["sub"], f_sub, INK)
            s["chip"] = box_sprite(s["chip"], font(FONT_KO, 40), LIME, INK, shadow=s["accent"])
    rng = np.random.default_rng(3)
    A["grain"] = [rng.normal(0, 4, (H, W, 1)).astype(np.int16) for _ in range(4)]
    return A


def enter_exit(u, dur, delay, last=False, t_in=0.7, t_out=0.45):
    """(x 오프셋, 불투명도): 10프레임 동안 투명→불투명하며 오른쪽에서 들어오고, 왼쪽으로 빠진다."""
    p_in = ease_out_cubic((u - delay) / t_in)
    dx = (1 - p_in) * 260
    op = clamp((u - delay) / FADE)
    if not last:
        p_out = ease_in_cubic((u - (dur - t_out) + delay * 0.3) / t_out)
        dx -= p_out * 420
        op *= 1 - p_out
    return dx, op


def render_scene(img, s, t):
    u, dur = t - s["start"], s["end"] - s["start"]
    last = s.get("last", False)
    sid = SCENES.index(s) * 50

    def wg(k):
        return wiggle(t, sid + k, *EL_WIGGLE)

    if s.get("kind") == "title":
        card = s["card"]
        scale = 0.6 + 0.4 * ease_out_back(u / 0.8) + 0.03 * clamp(u / dur)
        c = card.resize((int(card.width * scale), int(card.height * scale)), Image.BILINEAR)
        dx, op = enter_exit(u, dur, 0.0, t_in=0.01)
        wx, wy = wg(1)
        put(img, c, W / 2 - c.width / 2 + dx + wx, 410 - c.height / 2 + wy, op)
        dx1, op1 = enter_exit(u, dur, 0.5)
        wx, wy = wg(2)
        tx, ty = W / 2 - s["t1"].width / 2 + dx1 + wx, 755 + wy
        hl = s["hl"]
        w = int(hl.width * ease_in_out((u - 0.8) / 0.5))
        if w > 0:
            put(img, hl.crop((0, 0, w, hl.height)), tx - 20, ty + s["t1"].height * 0.42, op1)
        put(img, s["t1"], tx, ty, op1)
        dx2, op2 = enter_exit(u, dur, 1.1)
        wx, wy = wg(3)
        put(img, s["t2"], W / 2 - s["t2"].width / 2 + dx2 + wx, 925 + wy, op2)
        return

    card = s["card"]
    dx, op = enter_exit(u, dur, 0.0, last)
    sc = (0.92 + 0.08 * ease_out_back(u / 0.7)) * (1 + 0.035 * clamp(u / dur))
    c = card.resize((int(card.width * sc), int(card.height * sc)), Image.BILINEAR)
    wx, wy = wg(1)
    put(img, c, 1290 - c.width / 2 + dx * 1.3 + wx, 470 - c.height / 2 + wy, op)

    # 연도 카운터: 형광 컬러 + 잉크 하드 섀도
    prev = SCENES[SCENES.index(s) - 1].get("year", 1880)
    k = ease_out_cubic((u - 0.15) / 1.1)
    yr = int(round(lerp(prev, s["year"], k)))
    label = f"{yr}{s['suffix'] if k >= 1 else ''}"
    ys = text_sprite(label, font(FONT_NUM, 200), s["accent"], stroke=5, stroke_fill=INK, shadow=(12, 12, INK + (255,)))
    dxy, opy = enter_exit(u, dur, 0.1, last)
    wx, wy = wg(2)
    put(img, ys, 110 + dxy + wx, 120 + wy, opy)

    dxt, opt = enter_exit(u, dur, 0.35, last)
    wx, wy = wg(3)
    tt = s["t_title"]
    tx, ty = 130 + dxt + wx, 410 + wy
    hl = s["hl"]
    w = int(hl.width * ease_in_out((u - 0.8) / 0.45))
    if w > 0:
        put(img, hl.crop((0, 0, w, hl.height)), tx - 16, ty + tt.height * 0.45, opt)
    put(img, tt, tx, ty, opt)

    dxs, ops = enter_exit(u, dur, 0.6, last)
    wx, wy = wg(4)
    put(img, s["t_sub"], 134 + dxs + wx, 555 + wy, ops)

    ch = s["chip"]
    pc = ease_out_back((u - 1.3) / 0.45, 2.2)
    if pc > 0:
        _, opc = enter_exit(u, dur, 1.3, last)
        cs = ch.resize((max(1, int(ch.width * pc)), max(1, int(ch.height * pc))), Image.BILINEAR)
        wx, wy = wg(5)
        put(img, cs, 134 + ch.width / 2 - cs.width / 2 + wx, 670 + ch.height / 2 - cs.height / 2 + wy, opc)


def timeline_state(t):
    for i, s in enumerate(SCENES):
        if s["start"] <= t < s["end"] or i == len(SCENES) - 1:
            prev = TL_YEARS[i - 1] if i > 0 else TL_YEARS[0]
            return lerp(prev, TL_YEARS[i], ease_in_out((t - s["start"]) / 1.2))


def render_frame(A, fi):
    t = math.floor(fi / FPS * POSTERIZE_FPS) / POSTERIZE_FPS  # Posterize Time 5fps
    img = bg_frame(A["bg"], t)
    for s in SCENES:
        if s["start"] - 0.01 <= t < s["end"] + 0.01:
            render_scene(img, s, t)
    draw_timeline(img, timeline_state(t), clamp((t - 3.4) / FADE), t)
    arr = np.asarray(img, np.int16) + A["grain"][int(t * POSTERIZE_FPS) % len(A["grain"])]
    fade = clamp((t - (DUR - 0.6)) / 0.6)
    if fade > 0:
        arr = arr * (1 - fade)
    return arr.clip(0, 255).astype(np.uint8)


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found")
    A = build_assets()
    only = sys.argv[1:]
    if only:
        d = os.environ.get("PREVIEW_DIR", HERE)
        for ts in only:
            Image.fromarray(render_frame(A, int(float(ts) * FPS))).save(os.path.join(d, f"vox2_{ts}.png"))
        return
    n = int(DUR * FPS)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    last_key, frame = None, None
    for fi in range(n):
        key = math.floor(fi / FPS * POSTERIZE_FPS)  # 같은 5fps 구간은 같은 그림
        if key != last_key:
            frame, last_key = render_frame(A, fi).tobytes(), key
        proc.stdin.write(frame)
        if fi % 90 == 0:
            print(f"frame {fi}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
