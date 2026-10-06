"""Collage-style motion graphic: 자동차의 변천사 (30s, 1920x1080, 30fps).

톤앤매너: 찢은 종이 콜라주 · 원색(노랑/빨강/핑크/하늘/초록) · 검정 잉크 · 신문 조각 · 스톱모션
이미지: images_collage/ 폴더 (Google Flow로 생성)
출력: car_history_collage.mp4
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
IMG_DIR = os.path.join(HERE, "images_collage")
OUT = os.path.join(HERE, "car_history_collage.mp4")

W, H, FPS, DUR = 1920, 1080, 30, 30.0
STOP_FPS = 12  # 스톱모션 느낌: 애니메이션은 12fps로 끊어서 움직인다
WIPE = 0.45    # 장면 전환 시트가 지나가는 시간의 절반
WIGGLE_FREQ, WIGGLE_AMP = 1, 10  # wiggle(1,10): 초당 1회, ±10px

YELLOW = (247, 209, 23)
RED = (230, 59, 46)
PINK = (240, 80, 154)
SKY = (140, 200, 236)
GREEN = (125, 194, 66)
ORANGE = (243, 132, 38)
BLACK = (22, 22, 22)
NEWS = (236, 230, 214)
WHITE = (250, 248, 242)
PALETTE = [YELLOW, RED, PINK, SKY, GREEN, ORANGE, NEWS]

USER_FONTS = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts")


def find_font(*names):
    """사용자 폰트 폴더 → 시스템 폰트 폴더 순으로 찾고, 없으면 다음 후보."""
    for n in names:
        for d in (USER_FONTS, r"C:\Windows\Fonts"):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise FileNotFoundError(names)


FONT_KO_B = find_font("SUIT-Heavy.otf", "GmarketSansTTFBold.ttf", "malgunbd.ttf")      # 한글 제목
FONT_KO = find_font("SUIT-ExtraBold.otf", "NanumSquareEB.ttf", "malgunbd.ttf")         # 한글 부제·태그
FONT_NUM = find_font("Gotham-Black.otf", "ariblk.ttf", "impact.ttf")                   # 영문·숫자
TEXT_SCALE = 1.10  # 글씨 크기 전체 10% 확대


def font(path, size):
    return ImageFont.truetype(path, round(size * TEXT_SCALE))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x, s=1.7):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def lerp(a, b, t):
    return a + (b - a) * t


SCENES = [
    dict(kind="title", start=0.0, end=4.0, img="c0_title.jpg", bg=YELLOW),
    dict(start=4.0, end=9.2, img="c1_1886.jpg", bg=NEWS, year="1886",
         title="최초의 자동차", sub="카를 벤츠의 ‘페이턴트 모터바겐’", chip="최고 시속 16km"),
    dict(start=9.2, end=14.4, img="c2_1908.jpg", bg=SKY, year="1908",
         title="포드 모델 T", sub="조립 라인이 연 대량생산 시대", chip="1,500만 대 판매"),
    dict(start=14.4, end=19.6, img="c3_1950s.jpg", bg=PINK, year="1950s",
         title="자동차의 황금기", sub="고속도로, 교외, 화려한 테일핀", chip="자동차 = 자유"),
    dict(start=19.6, end=24.8, img="c4_1973.jpg", bg=ORANGE, year="1973",
         title="오일 쇼크", sub="작고 연비 좋은 차로 방향 전환", chip="효율의 시대"),
    dict(start=24.8, end=30.0, img="c5_2020s.jpg", bg=GREEN, year="2020s",
         title="전기차와 자율주행", sub="엔진 대신 배터리, 운전자 대신 AI", chip="다음 140년은?"),
]
TL_YEARS = [1880, 1886, 1908, 1955, 1973, 2024]


# ---------- 찢은 종이 ----------
def torn_outline(w, h, rng, jag=7, step=12, ox=0, oy=0):
    """w×h 사각형 둘레를 따라 들쭉날쭉한 점들."""
    pts = []
    def edge(x0, y0, x1, y1, nx, ny):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(n):
            t = i / n
            j = rng.uniform(-jag, jag)
            pts.append((ox + lerp(x0, x1, t) + nx * j, oy + lerp(y0, y1, t) + ny * j))
    edge(0, 0, w, 0, 0, 1)
    edge(w, 0, w, h, 1, 0)
    edge(w, h, 0, h, 0, 1)
    edge(0, h, 0, 0, 1, 0)
    return pts


def paper_grain(im, strength=10, seed=0):
    rng = np.random.default_rng(seed)
    a = np.asarray(im).astype(np.int16)
    n = rng.normal(0, strength, a.shape[:2])[..., None].astype(np.int16)
    a[..., :3] = np.clip(a[..., :3] + n, 0, 255)
    return Image.fromarray(a.astype(np.uint8), im.mode)


def halftone(draw, w, h, color, rng, spacing=14):
    r = rng.uniform(1.5, 3.5)
    for y in range(0, h, spacing):
        for x in range((y // spacing % 2) * spacing // 2, w, spacing):
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def newsprint(draw, w, h, rng):
    y = 16
    if rng.random() < 0.7:
        draw.rectangle([14, y, w * rng.uniform(0.5, 0.9), y + 22], fill=BLACK + (230,))
        y += 38
    while y < h - 14:
        x = 14
        while x < w - 30:
            seg = rng.randint(18, 70)
            draw.line([(x, y), (min(w - 14, x + seg), y)], fill=(90, 85, 78, 200), width=3)
            x += seg + 8
        y += 13


def make_scrap(w, h, color, seed, kind="plain", edge=True):
    """찢은 종이 한 장 (RGBA). kind: plain / halftone / news"""
    rng = random.Random(seed)
    pad = 14
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if edge:  # 종이가 찢겨 드러난 흰 섬유층
        d.polygon(torn_outline(w, h, rng, jag=6, ox=pad, oy=pad), fill=WHITE + (255,))
    body = Image.new("RGBA", im.size, color + (255,))
    bd = ImageDraw.Draw(body)
    if kind == "halftone":
        dark = tuple(max(0, c - 40) for c in color)
        halftone(bd, *im.size, dark + (255,), rng)
    elif kind == "news":
        body = Image.new("RGBA", im.size, NEWS + (255,))
        newsprint(ImageDraw.Draw(body), *im.size, rng)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).polygon(torn_outline(w - 6, h - 6, rng, jag=4, ox=pad + 3, oy=pad + 3), fill=255)
    im.paste(body, (0, 0), mask)
    return paper_grain(im, 9, seed)


def with_shadow(sprite, off=(8, 10), blur=8, alpha=110):
    pad = blur * 2 + max(off)
    out = Image.new("RGBA", (sprite.width + 2 * pad, sprite.height + 2 * pad), (0, 0, 0, 0))
    sh = sprite.getchannel("A").point(lambda v: alpha if v > 0 else 0)
    shl = Image.new("L", out.size, 0)
    shl.paste(sh, (pad + off[0], pad + off[1]))
    shl = shl.filter(ImageFilter.GaussianBlur(blur))
    out.paste(Image.new("RGBA", out.size, (20, 15, 10, 255)), (0, 0), shl)
    out.alpha_composite(sprite, (pad, pad))
    return out


def rot(sprite, angle):
    return sprite.rotate(angle, expand=True, resample=Image.BICUBIC)


# ---------- 배경 ----------
def collage_bg(base, seed):
    rng = random.Random(seed)
    bg = Image.new("RGBA", (W, H), base + (255,))
    bg = paper_grain(bg, 7, seed)
    d = ImageDraw.Draw(bg)
    if base != NEWS:
        halftone(d, W, H, tuple(max(0, c - 25) for c in base) + (255,), rng, spacing=22)
    # 가장자리 위주로 종이 조각을 흩뿌린다 (가운데는 비워 둔다)
    for i in range(34):
        side = rng.choice(["top", "bottom", "left", "right"])
        w, h = rng.randint(160, 480), rng.randint(90, 300)
        if side == "top":
            x, y = rng.randint(-100, W), rng.randint(-120, 40)
        elif side == "bottom":
            x, y = rng.randint(-100, W), rng.randint(H - 260, H - 60)
        elif side == "left":
            x, y = rng.randint(-200, 60), rng.randint(-50, H)
        else:
            x, y = rng.randint(W - 260, W), rng.randint(-50, H)
        color = rng.choice([c for c in PALETTE if c != base])
        kind = rng.choices(["plain", "halftone", "news"], [5, 2, 3])[0]
        s = rot(make_scrap(w, h, color, seed * 100 + i, kind), rng.uniform(-18, 18))
        bg.alpha_composite(s, (x, y)) if x >= 0 and y >= 0 else bg.paste(s, (x, y), s)
    # 종이 주름(구김) 음영
    wr = Image.new("L", (W // 8, H // 8), 128)
    wr = Image.fromarray((np.random.default_rng(seed).normal(128, 26, (H // 8, W // 8))).clip(0, 255).astype(np.uint8))
    wr = wr.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    a = np.asarray(bg.convert("RGB")).astype(np.float32)
    a *= (0.93 + 0.14 * (np.asarray(wr, np.float32) / 255))[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


# ---------- 사진 컷아웃 ----------
def placeholder(name):
    im = Image.new("RGB", (1600, 900), (120, 115, 105))
    ImageDraw.Draw(im).text((60, 60), f"missing: {name}", font=font(FONT_KO_B, 60), fill=(240, 240, 240))
    return im


def make_cutout(path, inner_w, angle, seed):
    im = Image.open(path).convert("RGB") if os.path.exists(path) else placeholder(os.path.basename(path))
    iw, ih = im.size
    im = im.crop((0, 0, int(iw * 0.94), int(ih * 0.94)))  # 우하단 ✦ 워터마크 제거
    inner_h = int(inner_w * 9 / 16)
    im = ImageOps.fit(im, (inner_w, inner_h), Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(1.12)
    rng = random.Random(seed)
    pad = 22
    out = Image.new("RGBA", (inner_w + 2 * pad, inner_h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(out).polygon(torn_outline(inner_w + 20, inner_h + 20, rng, jag=9, step=10, ox=pad - 10, oy=pad - 10),
                                fill=WHITE + (255,))
    mask = Image.new("L", out.size, 0)
    ImageDraw.Draw(mask).polygon(torn_outline(inner_w, inner_h, rng, jag=6, step=9, ox=pad, oy=pad), fill=255)
    photo = Image.new("RGBA", out.size, (0, 0, 0, 0))
    photo.paste(im, (pad, pad))
    out.paste(photo, (0, 0), mask)
    # 테이프 대신 붙인 색종이 조각
    for (tx, ty, c) in [(30, -6, PINK), (out.width - 150, out.height - 60, SKY)]:
        tp = rot(make_scrap(120, 44, c, seed + tx, "plain", edge=False), rng.uniform(-25, 25))
        tp.putalpha(tp.getchannel("A").point(lambda v: int(v * 0.9)))
        out.alpha_composite(tp, (max(0, tx), max(0, ty)))
    return rot(with_shadow(paper_grain(out, 6, seed)), angle)


# ---------- 타이포 (종이 띠 / 랜섬노트) ----------
def text_on_strip(text, fnt, fg, bg, seed, padx=30, pady=16, angle=0.0, kind="plain"):
    l, t, r, b = fnt.getbbox(text)
    tw, th = r - l, b - t
    strip = make_scrap(tw + 2 * padx, th + 2 * pady, bg, seed, kind)
    ImageDraw.Draw(strip).text((14 + padx - l, 14 + pady - t), text, font=fnt, fill=fg)
    return rot(with_shadow(strip, (5, 7), 5, 90), angle)


def ransom_digits(label, seed):
    """연도를 한 글자씩 서로 다른 색종이 위에 (랜섬노트)."""
    rng = random.Random(seed)
    f = font(FONT_NUM, 150)
    out = []
    colors = [YELLOW, WHITE, PINK, SKY, GREEN, RED]
    rng.shuffle(colors)
    for i, ch in enumerate(label):
        c = colors[i % len(colors)]
        fg = WHITE if c in (RED,) else BLACK
        if ch == "s":
            f2 = font(FONT_NUM, 110)
            out.append(text_on_strip(ch, f2, fg, c, seed + i, 16, 10, rng.uniform(-9, 9)))
        else:
            out.append(text_on_strip(ch, f, fg, c, seed + i, 16, 10, rng.uniform(-9, 9),
                                     rng.choice(["plain", "plain", "halftone"])))
    return out


def put(base, sprite, x, y, op=1.0):
    if op <= 0.001:
        return
    if op < 0.999:
        sprite = sprite.copy()
        sprite.putalpha(sprite.getchannel("A").point(lambda v: int(v * op)))
    base.paste(sprite, (int(round(x)), int(round(y))), sprite)


def scaled(sprite, sc):
    sc = max(0.02, sc)
    return sprite.resize((max(1, int(sprite.width * sc)), max(1, int(sprite.height * sc))), Image.BILINEAR)


def put_center(base, sprite, cx, cy, sc=1.0, op=1.0):
    s = scaled(sprite, sc) if abs(sc - 1) > 1e-3 else sprite
    put(base, s, cx - s.width / 2, cy - s.height / 2, op)


# ---------- 타임라인 (검정 종이 띠) ----------
TL_X0, TL_X1, TL_A, TL_B = 150, 1770, 1880, 2030
TL_Y = 1010


def tl_x(year):
    return TL_X0 + (year - TL_A) / (TL_B - TL_A) * (TL_X1 - TL_X0)


def build_timeline():
    strip = make_scrap(W + 80, 100, BLACK, 777, "plain")
    pos = (-54, TL_Y - 64)          # 화면상의 띠 위치
    line_y = TL_Y - 22              # 화면상의 눈금선 y
    d = ImageDraw.Draw(strip)
    f = font(FONT_NUM, 24)
    y = line_y - pos[1]
    d.line([(TL_X0 - pos[0], y), (TL_X1 - pos[0], y)], fill=(200, 200, 200), width=2)
    for yr in range(TL_A, TL_B + 1, 10):
        x = tl_x(yr) - pos[0]
        big = yr % 20 == 0
        d.line([(x, y - (10 if big else 6)), (x, y + (10 if big else 6))], fill=WHITE, width=2)
        if big:
            tw = d.textlength(str(yr), font=f)
            d.text((x - tw / 2, y + 14), str(yr), font=f, fill=WHITE)
    return strip, pos, line_y


def draw_timeline(img, A, year, op):
    if op <= 0:
        return
    strip, pos, ly = A["tl"]
    layer = Image.new("RGBA", (W, H - (TL_Y - 90)), (0, 0, 0, 0))
    oy = TL_Y - 90
    layer.paste(strip, (pos[0], pos[1] - oy), strip)
    d = ImageDraw.Draw(layer)
    y = ly - oy
    xm = tl_x(year)
    d.line([(TL_X0, y), (xm, y)], fill=YELLOW, width=8)
    layer.alpha_composite(A["marker"], (int(xm - A["marker"].width / 2), int(y - A["marker"].height / 2)))
    put(img, layer, 0, oy, op)


# ---------- 조립 ----------
def build_assets():
    A = {}
    for i, s in enumerate(SCENES):
        s["bgimg"] = collage_bg(s["bg"], 11 + i)
        p = os.path.join(IMG_DIR, s["img"])
        if s.get("kind") == "title":
            s["card"] = make_cutout(p, 1080, -2.0, 50)
            s["t1"] = text_on_strip("바퀴 위의 140년", font(FONT_KO_B, 118), WHITE, BLACK, 60, 40, 18, -2.5)
            s["t2"] = text_on_strip("자동차의 변천사  1886 – 2026", font(FONT_KO_B, 46), WHITE, RED, 61, 26, 12, 1.8)
        else:
            s["card"] = make_cutout(p, 920, [2.5, -2.0, 2.0, -2.5, 1.5][(i - 1) % 5], 50 + i)
            size = 80
            while font(FONT_KO_B, size).getlength(s["title"]) > 660:
                size -= 2
            s["t_title"] = text_on_strip(s["title"], font(FONT_KO_B, size), WHITE, BLACK, 70 + i, 28, 14, -1.5)
            s["t_sub"] = text_on_strip(s["sub"], font(FONT_KO, 36), BLACK, WHITE, 80 + i, 22, 10, 1.0)
            s["chip"] = text_on_strip(s["chip"], font(FONT_KO, 40), WHITE, RED if s["bg"] != RED else PINK,
                                      90 + i, 24, 10, -4.0)
            s["digits"] = ransom_digits(s["year"], 200 + i * 10)
    A["tl"] = build_timeline()
    A["marker"] = rot(make_scrap(34, 34, RED, 5, "plain"), 20)
    # 장면 전환용 대형 찢은 종이 시트
    A["sheets"] = {c: make_scrap(2 * W + 400, H + 160, c, 300 + k, "halftone" if k % 2 else "plain")
                   for k, c in enumerate([YELLOW, RED, PINK, SKY, GREEN, ORANGE, NEWS, BLACK])}
    rng = np.random.default_rng(3)
    A["grain"] = [rng.normal(0, 4, (H, W, 1)).astype(np.int16) for _ in range(4)]
    return A


def _noise1d(x, seed):
    """정수 지점마다 -1~1 난수, 그 사이는 부드럽게 보간 (값 노이즈)."""
    k = math.floor(x)
    f = x - k
    a = random.Random(seed * 7919 + k).uniform(-1, 1)
    b = random.Random(seed * 7919 + k + 1).uniform(-1, 1)
    return lerp(a, b, f * f * (3 - 2 * f))


def wiggle(t, seed, freq=WIGGLE_FREQ, amp=WIGGLE_AMP):
    """After Effects의 wiggle(freq, amp)과 같은 방식: 초당 freq번, 최대 ±amp px 흔들림 (2옥타브)."""
    def axis(sd):
        return (_noise1d(t * freq, sd) + 0.5 * _noise1d(t * freq * 2, sd + 17)) / 1.5 * amp
    return axis(seed), axis(seed + 101)


jitter = wiggle


def pop(u, delay, dur=0.35):
    return ease_out_back((u - delay) / dur)


def render_scene(img, s, t, tq):
    u = tq - s["start"]
    img.paste(s["bgimg"], (0, 0))
    if s.get("kind") == "title":
        k = pop(u, 0.0, 0.5)
        jx, jy = jitter(tq, 1)
        put_center(img, s["card"], W / 2 + jx, 430 + jy, (0.7 + 0.3 * k) * (1 + 0.03 * u / 4), clamp(k * 3))
        k1 = pop(u, 0.55, 0.4)
        jx, jy = jitter(tq, 2)
        put_center(img, s["t1"], W / 2 + jx, 820 + jy, k1)
        k2 = pop(u, 0.95, 0.35)
        jx, jy = jitter(tq, 3)
        put_center(img, s["t2"], W / 2 + 40 + jx, 965 + jy, k2)
        return

    # 사진 컷아웃: 위에서 툭 떨어지듯
    k = pop(u, 0.05, 0.45)
    jx, jy = jitter(tq, 11)
    put_center(img, s["card"], 1290 + jx, 470 + jy - (1 - k) * 60, (0.85 + 0.15 * k) * (1 + 0.03 * u / 5), clamp(k * 3))

    # 랜섬노트 연도: 한 글자씩 붙는다
    x = 120
    for j, dg in enumerate(s["digits"]):
        kd = pop(u, 0.25 + j * 0.09, 0.3)
        jx, jy = jitter(tq, 20 + j)
        if kd > 0:
            put_center(img, dg, x + dg.width / 2 + jx, 250 + jy, kd)
        x += dg.width - 44

    kt = pop(u, 0.75, 0.35)
    jx, jy = jitter(tq, 30)
    if kt > 0:
        put(img, scaled(s["t_title"], kt), 110 + jx, 400 + jy)
    ks = pop(u, 1.0, 0.35)
    jx, jy = jitter(tq, 31)
    if ks > 0:
        put(img, scaled(s["t_sub"], ks), 120 + jx, 560 + jy)
    kc = pop(u, 1.35, 0.3)
    jx, jy = jitter(tq, 32)
    if kc > 0:
        put_center(img, s["chip"], 130 + s["chip"].width / 2 + jx, 735 + jy, kc)


def timeline_year(t):
    for i, s in enumerate(SCENES):
        if s["start"] <= t < s["end"] or i == len(SCENES) - 1:
            prev = TL_YEARS[i - 1] if i > 0 else TL_YEARS[0]
            return lerp(prev, TL_YEARS[i], ease_in_out((t - s["start"]) / 1.0))


def render_frame(A, fi):
    t = fi / FPS
    tq = math.floor(t * STOP_FPS) / STOP_FPS  # 12fps 스톱모션
    img = Image.new("RGB", (W, H))
    cur = next(s for s in SCENES if s["start"] <= t < s["end"] or s is SCENES[-1])
    render_scene(img, cur, t, tq)
    draw_timeline(img, A, timeline_year(tq), clamp((tq - 3.3) / 0.4))

    # 장면 전환: 다음 장면 색의 찢은 종이 시트가 화면을 쓸고 지나간다
    #   세 장이 시차를 두고 겹쳐 지나가며, 가운데 장이 장면이 바뀌는 순간 화면 전체를 덮는다
    for i, s in enumerate(SCENES[1:], 1):
        b = s["start"]
        if abs(t - b) <= WIPE + 0.12:
            accents = [c for c in (RED, SKY, PINK, YELLOW, GREEN) if c != s["bg"]]
            layers = [(accents[i % len(accents)], -0.12), (BLACK, 0.0), (s["bg"], 0.12)]
            for k, (c, dly) in enumerate(layers):
                p = (tq - (b - WIPE + dly)) / (2 * WIPE)
                if 0 < p < 1:
                    sheet = A["sheets"][c]
                    x = lerp(W + 40, -sheet.width - 40, ease_in_out(p))
                    put(img, sheet, x, -80 + k * 6)

    arr = np.asarray(img, np.int16) + A["grain"][int(tq * STOP_FPS) % len(A["grain"])]
    fade = clamp((t - (DUR - 0.5)) / 0.5)
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
            Image.fromarray(render_frame(A, int(float(ts) * FPS))).save(os.path.join(d, f"collage_{ts}.png"))
        return
    n = int(DUR * FPS)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    cache = {}
    for fi in range(n):
        # 스톱모션이라 같은 12fps 구간의 프레임은 재사용 (전환·페이드 구간 제외)
        t = fi / FPS
        key = int(t * STOP_FPS)
        in_wipe = any(abs(t - s["start"]) <= WIPE + 0.15 for s in SCENES[1:]) or t > DUR - 0.5
        if not in_wipe and key in cache:
            frame = cache[key]
        else:
            frame = render_frame(A, fi).tobytes()
            cache = {key: frame}
        proc.stdin.write(frame)
        if fi % 90 == 0:
            print(f"frame {fi}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
