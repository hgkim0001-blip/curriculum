"""Vox-style motion graphic: 자동차의 변천사 (30s, 1920x1080, 30fps).

이미지: images/ 폴더 (Google Flow로 생성)
출력: car_history_vox.mp4  (PIL로 프레임을 그려 ffmpeg로 인코딩)
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
OUT = os.path.join(HERE, "car_history_vox.mp4")

W, H, FPS, DUR = 1920, 1080, 30, 30.0

# ---- palette (Vox: 종이, 형광 노랑, 빨강, 잉크) ----
PAPER = (242, 235, 221)
INK = (28, 28, 28)
YELLOW = (255, 213, 0)
RED = (232, 72, 59)
WHITE = (252, 250, 244)

FONT_KO_B = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_KO = r"C:\Windows\Fonts\malgun.ttf"
FONT_YEAR = r"C:\Windows\Fonts\timesbd.ttf"  # 라이닝 숫자


def font(path, size):
    return ImageFont.truetype(path, size)


# ---- easing ----
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_cubic(x):
    x = clamp(x)
    return x ** 3


def ease_out_back(x, s=1.4):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def lerp(a, b, t):
    return a + (b - a) * t


# ---- scenes ----
SCENES = [
    dict(kind="title", start=0.0, end=4.0, img="s0_title.jpg", treat="warm"),
    dict(start=4.0, end=9.2, img="s1_1886.jpg", treat="sepia", year=1886, suffix="",
         title="최초의 자동차", sub="카를 벤츠의 ‘페이턴트 모터바겐’", chip="최고 시속 16km"),
    dict(start=9.2, end=14.4, img="s2_1908.jpg", treat="sepia", year=1908, suffix="",
         title="포드 모델 T", sub="조립 라인이 연 대량생산 시대", chip="1,500만 대 판매"),
    dict(start=14.4, end=19.6, img="s3_1950s.jpg", treat="warm", year=1950, suffix="s",
         title="자동차의 황금기", sub="고속도로, 교외, 화려한 테일핀", chip="자동차 = 자유"),
    dict(start=19.6, end=24.8, img="s4_1973.jpg", treat="faded", year=1973, suffix="",
         title="오일 쇼크", sub="작고 연비 좋은 차로 방향 전환", chip="효율의 시대"),
    dict(start=24.8, end=30.0, img="s5_2020s.jpg", treat="none", year=2020, suffix="s",
         title="전기차와 자율주행", sub="엔진 대신 배터리, 운전자 대신 AI", chip="다음 140년은?", last=True),
]
TL_YEARS = [1880, 1886, 1908, 1955, 1973, 2024]  # 타임라인 마커 목표 연도


# ---- asset builders ----
def paper_texture():
    rng = np.random.default_rng(7)
    base = np.ones((H, W, 3), np.float32) * np.array(PAPER, np.float32)
    fibers = rng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    fibers = np.array(Image.fromarray(((fibers * 30) + 128).clip(0, 255).astype(np.uint8))
                      .resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2)), np.float32) - 128
    base += fibers[..., None] * 0.18
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    base *= (1 - 0.16 * np.clip(d - 0.35, 0, None))[..., None]
    # 은은한 격자 (Vox 보드 느낌)
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    for x in range(0, W, 60):
        dr.line([(x, 0), (x, H)], fill=(230, 222, 206), width=1)
    for y in range(0, H, 60):
        dr.line([(0, y), (W, y)], fill=(230, 222, 206), width=1)
    return img


def placeholder(name):
    im = Image.new("RGB", (1600, 900), (120, 115, 105))
    d = ImageDraw.Draw(im)
    d.text((60, 60), f"missing: {name}", font=font(FONT_KO_B, 60), fill=(240, 240, 240))
    return im


def treat(im, mode):
    if mode == "sepia":
        g = ImageOps.grayscale(im)
        g = ImageEnhance.Contrast(g).enhance(1.15)
        im = ImageOps.colorize(g, black=(45, 32, 20), white=(245, 228, 196))
    elif mode == "warm":
        im = ImageEnhance.Color(im).enhance(0.85)
        im = Image.blend(im, Image.new("RGB", im.size, (255, 214, 150)), 0.08)
    elif mode == "faded":
        im = ImageEnhance.Color(im).enhance(0.7)
        im = ImageEnhance.Contrast(im).enhance(0.92)
        im = Image.blend(im, Image.new("RGB", im.size, (240, 220, 190)), 0.10)
    return im


def make_card(path, mode, inner_w, angle, seed):
    """사진 → 흰 테두리 + 테이프 + 그림자가 있는 회전된 폴라로이드 카드 (RGBA)."""
    im = Image.open(path).convert("RGB") if os.path.exists(path) else placeholder(os.path.basename(path))
    inner_h = int(inner_w * 9 / 16)
    iw, ih = im.size
    im = im.crop((0, 0, int(iw * 0.94), int(ih * 0.94)))  # 우하단 ✦ 워터마크 제거
    im = ImageOps.fit(im, (inner_w, inner_h), Image.LANCZOS)
    im = treat(im, mode)
    b = 18
    card = Image.new("RGBA", (inner_w + 2 * b, inner_h + 2 * b), WHITE + (255,))
    card.paste(im, (b, b))
    ImageDraw.Draw(card).rectangle([b, b, b + inner_w - 1, b + inner_h - 1], outline=(0, 0, 0, 40), width=2)

    pad = 80
    cw, ch = card.size
    canvas = Image.new("RGBA", (cw + 2 * pad, ch + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(shadow).rectangle([pad + 14, pad + 20, pad + cw + 14, pad + ch + 20], fill=95)
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.paste(Image.new("RGBA", canvas.size, (40, 30, 20, 255)), (0, 0), shadow)
    canvas.alpha_composite(card, (pad, pad))

    # 마스킹 테이프
    rng = random.Random(seed)
    for (tx, ty, ta) in [(pad + 40, pad - 8, -32), (pad + cw - 40, pad - 8, 30)]:
        tape = Image.new("RGBA", (170, 46), (236, 224, 190, 190))
        td = ImageDraw.Draw(tape)
        for i in range(0, 170, 6):
            td.line([(i, 0), (i, 3 + rng.randint(0, 3))], fill=(0, 0, 0, 0))
            td.line([(i, 46), (i, 43 - rng.randint(0, 3))], fill=(0, 0, 0, 0))
        tape = tape.rotate(ta, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(tape, (tx - tape.width // 2, ty - tape.height // 2 + 10))
    return canvas.rotate(angle, expand=True, resample=Image.BICUBIC)


def text_sprite(text, fnt, color, pad=6):
    l, t, r, b = fnt.getbbox(text)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=fnt, fill=color)
    return im


def highlight_sprite(w, h, color, seed):
    """형광펜으로 그은 듯한 불규칙한 띠."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pts_top = [(x, rng.randint(0, 8)) for x in range(0, w + 1, 40)]
    pts_bot = [(x, h - rng.randint(0, 8)) for x in range(w, -1, -40)]
    ImageDraw.Draw(im).polygon(pts_top + pts_bot, fill=color + (235,))
    return im


def chip_sprite(text):
    f = font(FONT_KO_B, 38)
    ts = text_sprite(text, f, WHITE)
    im = Image.new("RGBA", (ts.width + 48, ts.height + 24), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=10, fill=RED + (255,))
    im.alpha_composite(ts, (24, 12))
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
TL_Y, TL_X0, TL_X1, TL_A, TL_B = 1000, 150, 1770, 1880, 2030


def tl_x(year):
    return TL_X0 + (year - TL_A) / (TL_B - TL_A) * (TL_X1 - TL_X0)


def draw_timeline(img, year, op):
    if op <= 0:
        return
    layer = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 60
    f = font(FONT_YEAR, 22)
    d.line([(TL_X0, y), (TL_X1, y)], fill=INK + (110,), width=3)
    for yr in range(TL_A, TL_B + 1, 10):
        x = tl_x(yr)
        big = yr % 20 == 0
        d.line([(x, y - (12 if big else 7)), (x, y + (12 if big else 7))], fill=INK + (150,), width=2)
        if big:
            tw = d.textlength(str(yr), font=f)
            d.text((x - tw / 2, y + 18), str(yr), font=f, fill=INK + (160,))
    xm = tl_x(year)
    d.line([(TL_X0, y), (xm, y)], fill=RED + (255,), width=7)
    d.ellipse([xm - 13, y - 13, xm + 13, y + 13], fill=RED + (255,), outline=WHITE + (255,), width=4)
    d.polygon([(xm - 11, y - 34), (xm + 11, y - 34), (xm, y - 20)], fill=INK + (255,))
    put(img, layer, 0, TL_Y - 60, op)


# ---- main render ----
def build_assets():
    A = {"paper": paper_texture()}
    f_title = font(FONT_KO_B, 84)
    f_sub = font(FONT_KO, 40)
    for i, s in enumerate(SCENES):
        p = os.path.join(IMG_DIR, s["img"])
        if s.get("kind") == "title":
            s["card"] = make_card(p, s["treat"], 1060, -2.5, i)
            f_big = font(FONT_KO_B, 120)
            s["t1"] = text_sprite("바퀴 위의 140년", f_big, INK)
            s["hl"] = highlight_sprite(s["t1"].width + 40, int(s["t1"].height * 0.62), YELLOW, 99)
            s["t2"] = text_sprite("자동차의 변천사  1886 → 2026", font(FONT_KO_B, 44), WHITE)
        else:
            s["card"] = make_card(p, s["treat"], 900, [3, -2.5, 2.5, -3, 2][(i - 1) % 5], i)
            size = 84
            while font(FONT_KO_B, size).getlength(s["title"]) > 600:
                size -= 2
            s["t_title"] = text_sprite(s["title"], font(FONT_KO_B, size), INK)
            s["hl"] = highlight_sprite(s["t_title"].width + 36, int(s["t_title"].height * 0.55), YELLOW, i)
            s["t_sub"] = text_sprite(s["sub"], f_sub, (60, 55, 50))
            s["chip"] = chip_sprite(s["chip"])
    rng = np.random.default_rng(3)
    A["grain"] = [rng.normal(0, 4, (H, W, 1)).astype(np.int16) for _ in range(6)]
    return A


def enter_exit(u, dur, delay, last=False, t_in=0.7, t_out=0.45):
    """(x 오프셋, 불투명도) : 오른쪽에서 들어와서 왼쪽으로 빠진다."""
    p_in = ease_out_cubic((u - delay) / t_in)
    dx = (1 - p_in) * 260
    op = clamp((u - delay) / (t_in * 0.6))
    if not last:
        p_out = ease_in_cubic((u - (dur - t_out) + delay * 0.3) / t_out)
        dx -= p_out * 420
        op *= 1 - p_out
    return dx, op


def render_scene(img, s, t):
    u, dur = t - s["start"], s["end"] - s["start"]
    last = s.get("last", False)
    if s.get("kind") == "title":
        card = s["card"]
        pop = ease_out_back(u / 0.8)
        scale = 0.6 + 0.4 * pop + 0.03 * clamp(u / dur)
        c = card.resize((int(card.width * scale), int(card.height * scale)), Image.BILINEAR)
        dx, op = enter_exit(u, dur, 0.0, t_in=0.01)
        put(img, c, W / 2 - c.width / 2 + dx, 420 - c.height / 2, op * clamp(u / 0.25))
        # 제목 + 형광펜
        dx1, op1 = enter_exit(u, dur, 0.5)
        tx, ty = W / 2 - s["t1"].width / 2 + dx1, 770
        hl = s["hl"]
        w = int(hl.width * ease_in_out((u - 0.8) / 0.5))
        if w > 0:
            put(img, hl.crop((0, 0, w, hl.height)), tx - 20, ty + s["t1"].height * 0.42, op1)
        put(img, s["t1"], tx, ty, op1)
        # 부제 (잉크 박스)
        dx2, op2 = enter_exit(u, dur, 1.1)
        t2 = s["t2"]
        box = Image.new("RGBA", (t2.width + 40, t2.height + 20), INK + (255,))
        box.alpha_composite(t2, (20, 10))
        put(img, box, W / 2 - box.width / 2 + dx2, 935, op2)
        return

    # 사진 카드 (살짝 줌인하는 켄 번스)
    card = s["card"]
    dx, op = enter_exit(u, dur, 0.0, last)
    sc = (0.92 + 0.08 * ease_out_back(u / 0.7)) * (1 + 0.035 * clamp(u / dur))
    c = card.resize((int(card.width * sc), int(card.height * sc)), Image.BILINEAR)
    put(img, c, 1290 - c.width / 2 + dx * 1.3, 470 - c.height / 2, op)

    # 연도 카운터
    prev = SCENES[SCENES.index(s) - 1].get("year", 1880)
    k = ease_out_cubic((u - 0.15) / 1.1)
    yr = int(round(lerp(prev, s["year"], k)))
    label = f"{yr}{s['suffix'] if k >= 1 else ''}"
    ys = text_sprite(label, font(FONT_YEAR, 190), RED)
    dxy, opy = enter_exit(u, dur, 0.1, last)
    put(img, ys, 120 + dxy, 150, opy)

    # 제목 + 형광펜 스와이프
    dxt, opt = enter_exit(u, dur, 0.35, last)
    tt = s["t_title"]
    tx, ty = 130 + dxt, 420
    hl = s["hl"]
    w = int(hl.width * ease_in_out((u - 0.8) / 0.45))
    if w > 0:
        put(img, hl.crop((0, 0, w, hl.height)), tx - 16, ty + tt.height * 0.45, opt)
    put(img, tt, tx, ty, opt)

    dxs, ops = enter_exit(u, dur, 0.6, last)
    put(img, s["t_sub"], 134 + dxs, 545, ops)

    # 팩트 칩: 튀어오르듯 등장
    ch = s["chip"]
    pc = ease_out_back((u - 1.3) / 0.45, 2.2)
    if pc > 0:
        _, opc = enter_exit(u, dur, 1.3, last)
        sc = max(0.01, pc)
        cs = ch.resize((max(1, int(ch.width * sc)), max(1, int(ch.height * sc))), Image.BILINEAR)
        put(img, cs, 134 + ch.width / 2 - cs.width / 2, 640 + ch.height / 2 - cs.height / 2, opc)


def timeline_state(t):
    for i, s in enumerate(SCENES):
        if s["start"] <= t < s["end"] or i == len(SCENES) - 1:
            prev = TL_YEARS[i - 1] if i > 0 else TL_YEARS[0]
            k = ease_in_out((t - s["start"]) / 1.2)
            return lerp(prev, TL_YEARS[i], k)


def render_frame(A, fi):
    t = fi / FPS
    img = A["paper"].copy()
    for s in SCENES:
        if s["start"] - 0.01 <= t < s["end"] + 0.01:
            render_scene(img, s, t)
    draw_timeline(img, timeline_state(t), clamp((t - 3.4) / 0.6))

    # 필름 그레인 + 미세한 흔들림(스톱모션 질감)
    arr = np.asarray(img, np.int16) + A["grain"][(fi // 2) % len(A["grain"])]
    if (fi // 3) % 2:
        arr = np.roll(arr, 1, axis=0)
    # 엔딩 페이드 아웃
    fade = clamp((t - (DUR - 0.6)) / 0.6)
    if fade > 0:
        arr = arr * (1 - fade)
    return arr.clip(0, 255).astype(np.uint8)


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found")
    A = build_assets()
    only = sys.argv[1:]  # 예: python make_video.py 2.0 6.5  → 해당 시점 PNG 미리보기
    if only:
        for ts in only:
            Image.fromarray(render_frame(A, int(float(ts) * FPS))).save(os.path.join(os.environ.get("PREVIEW_DIR", HERE), f"preview_{ts}.png"))
        return
    n = int(DUR * FPS)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "23",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    for fi in range(n):
        proc.stdin.write(render_frame(A, fi).tobytes())
        if fi % 90 == 0:
            print(f"frame {fi}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
