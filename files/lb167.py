"""Retro Paper Collage motion graphic: 자동차의 변천사 (30s, 1920x1080, 30fps).

비디오하이브 샘플/모션패턴_분석_Paper_Collage.md 의 형식을 적용한 버전.
- 차량: cutouts/*.png (make_cutouts.py로 누끼 딴 차량만 사용)
- 12fps 스텝 + 3fps 종이 텍스처 보일, 원색 블롭 솟기, 찢어진 종이 마스크 리빌, 낙서 선, 알약 라벨,
  도장 텍스트, 필기체 쓰기, 붓 하이라이트, 배경 대형 글자, 반복 적층, 대각선 색종이 띠,
  종이 밀기 / 구겨진 종이 구멍 / 찢어진 종이 덮기 전환, 찢어 나눈 배경, 모서리 색종이 프레임
출력: car_history_paper_collage.mp4
"""
import math
import os
import random
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
CUT = os.path.join(HERE, "cutouts")
OUT = os.path.join(HERE, "car_history_paper_collage.mp4")

W, H, FPS, DUR = 1920, 1080, 30, 30.0
STEP_FPS, BOIL_FPS = 12, 3

# ---- 레트로 팔레트 (채도 살짝 낮춤) ----
KRAFT = (226, 208, 176)
ORANGE = (222, 132, 30)
MUSTARD = (232, 184, 72)
TEAL = (86, 164, 170)
OLIVE = (112, 134, 52)
BRICK = (190, 64, 44)
PINK = (222, 128, 122)
BLUE = (66, 116, 170)
INK = (48, 36, 30)
PAPER_WHITE = (247, 241, 226)

USER_FONTS = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts")


def find_font(*names):
    for n in names:
        for d in (USER_FONTS, r"C:\Windows\Fonts"):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise FileNotFoundError(names)


F_STAMP = find_font("GmarketSansTTFBold.ttf", "SUIT-Heavy.otf", "malgunbd.ttf")   # 굵은 도장 글자
F_SCRIPT = find_font("NanumPen.ttf", "NanumBarunpenB.ttf")                         # 필기체
F_LABEL = find_font("NanumBarunpenB.ttf", "GmarketSansTTFMedium.ttf")              # 라벨 손글씨
F_GIANT = find_font("Gotham-Black.otf", "ariblk.ttf", "impact.ttf")                # 배경 대형 글자(영문·숫자)

_fc = {}


def font(p, s):
    k = (p, int(s))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(p, int(s))
    return _fc[k]


# ---------------- easing / time ----------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def seg(u, a, b):
    return clamp((u - a) / (b - a))


def expo_out(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def back_out(x, s=1.8):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def step_time(t):
    return math.floor(t * STEP_FPS + 1e-6) / STEP_FPS


def jit(t, seed, amp=2.0):
    """12fps 스텝마다 바뀌는 미세한 손떨림."""
    r = random.Random(int(t * STEP_FPS + 1e-6) * 7919 + seed)
    return r.uniform(-amp, amp), r.uniform(-amp, amp)


# ---------------- 종이 텍스처 (P16 보일) ----------------
def grain(img, s, seed):
    a = np.asarray(img).astype(np.int16)
    n = np.random.default_rng(seed).normal(0, s, a.shape[:2])[..., None].astype(np.int16)
    a[..., :3] = np.clip(a[..., :3] + n, 0, 255)
    return Image.fromarray(a.astype(np.uint8), img.mode)


def paper_textures():
    rng = np.random.default_rng(11)
    base = np.array(KRAFT, np.float32)
    texs = []
    # 1) 크라프트지: 섬유 + 반점
    a = np.ones((H, W, 3), np.float32) * base
    fib = Image.fromarray((rng.normal(128, 40, (H // 3, W // 3))).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    fib = np.asarray(fib.filter(ImageFilter.GaussianBlur(1.5)), np.float32) - 128
    a += fib[..., None] * 0.10
    spots = (rng.random((H, W)) < 0.0015) * -40
    a += spots[..., None]
    texs.append(a)
    # 2) 줄무늬(골판) 종이
    b = np.ones((H, W, 3), np.float32) * (base + np.array([8, 6, 2]))
    yy, xx = np.mgrid[0:H, 0:W]
    b += (np.sin((xx * 0.55 + yy * 0.25) * 0.9) * 4)[..., None]
    b += rng.normal(0, 5, (H, W, 1))
    texs.append(b)
    # 3) 구겨진 종이: assets/paper_bg.jpg의 음영을 크라프트 색에 곱한다
    pb = os.path.join(HERE, "assets", "paper_bg.jpg")
    c = np.ones((H, W, 3), np.float32) * (base + np.array([10, 10, 8]))
    if os.path.exists(pb):
        lum = np.asarray(ImageOps.fit(Image.open(pb).convert("L"), (W, H)), np.float32) / 255
        c *= (0.78 + 0.25 * lum / lum.max())[..., None]
    c += rng.normal(0, 4, (H, W, 1))
    texs.append(c)
    return [Image.fromarray(x.clip(0, 255).astype(np.uint8)) for x in texs]


# ---------------- 찢어진 종이 ----------------
def torn_edge_pts(w, y, seed, jag=10, step=12):
    rng = random.Random(seed)
    return [(x, y + rng.uniform(-jag, jag)) for x in range(-step, w + 2 * step, step)]


def torn_sheet(w, h, color, seed, fiber=10, top_only=True):
    """윗변이 찢어지고 흰 섬유층이 드러난 종이(RGBA). top_only=False면 아랫변도 찢는다."""
    hh = h + fiber * 3
    out = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    top_w = torn_edge_pts(w, fiber, seed, jag=fiber + 3)
    top_b = torn_edge_pts(w, fiber * 2.2, seed + 1, jag=fiber * 0.8)
    if top_only:
        d.polygon(top_w + [(w + 30, hh), (-30, hh)], fill=PAPER_WHITE + (255,))
        d.polygon(top_b + [(w + 30, hh), (-30, hh)], fill=color + (255,))
    else:
        bot_w = torn_edge_pts(w, hh - fiber, seed + 2, jag=fiber + 3)[::-1]
        bot_b = torn_edge_pts(w, hh - fiber * 2.2, seed + 3, jag=fiber * 0.8)[::-1]
        d.polygon(top_w + bot_w, fill=PAPER_WHITE + (255,))
        d.polygon(top_b + bot_b, fill=color + (255,))
    return grain(out, 6, seed)


def torn_piece(pts_body, color, size, seed, fiber=9):
    """임의 다각형 모양의 찢어진 색종이 조각(모서리 프레임, 찢어 나눈 배경용)."""
    w, h = size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)

    def rough(pts, jag):
        rng = random.Random(seed)
        res = []
        for i in range(len(pts)):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 12))
            for k in range(n):
                s = k / n
                res.append((lerp(x0, x1, s) + rng.uniform(-jag, jag), lerp(y0, y1, s) + rng.uniform(-jag, jag)))
        return res
    d.polygon(rough(pts_body, fiber), fill=PAPER_WHITE + (255,))
    cx = sum(p[0] for p in pts_body) / len(pts_body)
    cy = sum(p[1] for p in pts_body) / len(pts_body)
    inner = [(lerp(x, cx, 0.012), lerp(y, cy, 0.012)) for x, y in pts_body]
    d.polygon(rough(inner, fiber * 0.6), fill=color + (255,))
    return grain(out, 7, seed)


def halftone_overlay(img, spacing=9, strength=0.10):
    """사진·색종이 위 하프톤 망점."""
    w, h = img.size
    dots = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(dots)
    for y in range(0, h, spacing):
        for x in range((y // spacing % 2) * spacing // 2, w, spacing):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=255)
    a = np.asarray(img).astype(np.float32)
    m = np.asarray(dots, np.float32)[..., None] / 255 * strength
    a[..., :3] *= (1 - m)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), img.mode)


# ---------------- 블롭 / 낙서 ----------------
def blob(size, color, seed):
    """P1: 유기적 블롭."""
    w, h = size
    rng = random.Random(seed)
    ph = [rng.uniform(0, 6.28) for _ in range(3)]
    pts = []
    for i in range(120):
        a = 2 * math.pi * i / 120
        r = 1 + 0.10 * math.sin(2 * a + ph[0]) + 0.06 * math.sin(3 * a + ph[1]) + 0.04 * math.sin(5 * a + ph[2])
        pts.append((w / 2 + w / 2 * 0.9 * r * math.cos(a), h / 2 + h / 2 * 0.9 * r * math.sin(a)))
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(out).polygon(pts, fill=color + (255,))
    return halftone_overlay(grain(out, 8, seed), 10, 0.06)


def doodle(d, pts, p, color, width=12):
    """P3: 손으로 그은 낙서 곡선 그리기(Catmull-Rom 보간)."""
    if p <= 0:
        return
    dense = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        for k in range(20):
            s = k / 20
            s2, s3 = s * s, s * s * s
            dense.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * s + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * s2
                                      + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * s3) for j in range(2)))
    n = max(2, int(len(dense) * clamp(p)))
    d.line(dense[:n], fill=color, width=width, joint="curve")
    r = width / 2
    for x, y in (dense[0], dense[n - 1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=color)


# ---------------- 글자 ----------------
def rough_alpha(im, seed, amount=0.18):
    """굵은 손글씨 느낌: 알파 가장자리를 거칠게."""
    a = np.asarray(im.getchannel("A"), np.float32) / 255
    noise = np.random.default_rng(seed).random(a.shape)
    edge = (a > 0.05) & (a < 0.95)
    a = np.where(edge & (noise < amount), a * 0.3, a)
    out = im.copy()
    out.putalpha(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)))
    return out


def text_img(text, fpath, size, color, stroke=0, stroke_fill=None, pad=20):
    f = font(fpath, size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=color, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def stamp_text(text, size, color, seed, angle=0.0, stroke=0, stroke_fill=INK):
    im = text_img(text, F_STAMP, size, color, stroke=stroke, stroke_fill=stroke_fill)
    return rough_alpha(im, seed).rotate(angle, expand=True, resample=Image.BICUBIC)


def script_text(text, size, color, angle=-3.0):
    return text_img(text, F_SCRIPT, size, color).rotate(angle, expand=True, resample=Image.BICUBIC)


def pill(text, size, fg, seed, angle=-4.0, bg=PAPER_WHITE):
    """P4: 흰 종이 알약 라벨(글자는 따로 찍는다)."""
    t = text_img(text, F_LABEL, size, fg, pad=0)
    w, h = t.width + int(size * 1.4), t.height + int(size * 0.7)
    base = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    ImageDraw.Draw(base).rounded_rectangle([10, 10, 10 + w, 10 + h], radius=h // 2, fill=bg + (255,))
    base = rough_alpha(grain(base, 6, seed), seed, 0.35)
    txt = Image.new("RGBA", base.size, (0, 0, 0, 0))
    txt.alpha_composite(t, ((base.width - t.width) // 2, (base.height - t.height) // 2))
    return base.rotate(angle, expand=True, resample=Image.BICUBIC), txt.rotate(angle, expand=True, resample=Image.BICUBIC)


def brush(w, h, color, seed):
    """P7: 노란 붓 자국."""
    rng = random.Random(seed)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    top = [(x, rng.uniform(4, 16)) for x in range(0, w + 1, 18)]
    bot = [(x, h - rng.uniform(4, 16)) for x in range(w, -1, -18)]
    d.polygon(top + bot, fill=color + (235,))
    a = np.asarray(out).astype(np.float32)
    streak = np.random.default_rng(seed).random((h, 1)) < 0.18      # 붓결(가로 줄)
    a[..., 3] *= np.where(streak, 0.55, 1.0)
    return grain(Image.fromarray(a.astype(np.uint8), "RGBA"), 6, seed)


def giant_text(text, size, color, seed, opacity=0.5):
    """P8: 그런지 질감 대형 배경 글자."""
    im = text_img(text, F_GIANT, size, color)
    a = np.asarray(im.getchannel("A"), np.float32) / 255
    rng = np.random.default_rng(seed)
    blotch = Image.fromarray((rng.random((a.shape[0] // 14 + 1, a.shape[1] // 14 + 1)) * 255).astype(np.uint8))
    blotch = np.asarray(blotch.resize((a.shape[1], a.shape[0]), Image.BICUBIC), np.float32) / 255
    fine = rng.random(a.shape)
    a = a * np.clip((blotch - 0.25) * 2.2, 0, 1) * np.where(fine < 0.12, 0.4, 1.0) * opacity
    im.putalpha(Image.fromarray((a * 255).clip(0, 255).astype(np.uint8)))
    return im


def write_on(sprite, p, feather=26):
    """P6: 필기체를 왼쪽부터 써 내려가듯 드러냄."""
    if p >= 1:
        return sprite
    w, h = sprite.size
    edge = int((w + feather) * clamp(p))
    m = np.clip((edge - np.arange(w)) / feather, 0, 1).astype(np.float32)
    a = np.asarray(sprite.getchannel("A"), np.float32) * m[None, :]
    out = sprite.copy()
    out.putalpha(Image.fromarray(a.astype(np.uint8)))
    return out


def wipe(sprite, p):
    """붓·띠를 왼쪽부터 칠하기."""
    if p >= 1:
        return sprite
    w = max(1, int(sprite.width * clamp(p)))
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.paste(sprite.crop((0, 0, w, sprite.height)), (0, 0))
    return out


# ---------------- 배치 도우미 ----------------
def put(st, spr, cx, cy, scale=1.0, blur=0.0, op=1.0):
    if spr is None or op <= 0.001 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if blur > 0.4:
        spr = spr.filter(ImageFilter.GaussianBlur(blur))
    if op < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * op)))
    st.alpha_composite(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2))) if (
        cx - spr.width / 2 >= 0 and cy - spr.height / 2 >= 0 and cx + spr.width / 2 <= W and cy + spr.height / 2 <= H
    ) else st.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


def stamp(st, spr, cx, cy, u, start, t, seed):
    """P5: 흐리고 110%에서 선명하고 100%로 2~3스텝 만에 툭."""
    if u < start:
        return
    p = seg(u, start, start + 0.2)
    jx, jy = jit(t, seed)
    put(st, spr, cx + jx, cy + jy, scale=1.1 - 0.1 * p, blur=6 * (1 - p))


def pill_pop(st, pl, cx, cy, u, start, t, seed):
    """P4: 알약이 먼저 튀어나오고(0→110→100%), 2~3스텝 뒤 글자가 찍힌다."""
    if u < start:
        return
    base, txt = pl
    jx, jy = jit(t, seed)
    s = back_out(seg(u, start, start + 0.2), 2.4)
    put(st, base, cx + jx, cy + jy, scale=s)
    p = seg(u, start + 0.22, start + 0.4)
    if p > 0:
        put(st, txt, cx + jx, cy + jy, scale=1.1 - 0.1 * p, blur=5 * (1 - p))


def script_write(st, spr, cx, cy, u, start, dur, t, seed):
    if u < start:
        return
    jx, jy = jit(t, seed, 1.5)
    put(st, write_on(spr, seg(u, start, start + dur)), cx + jx, cy + jy)


def blob_rise(st, bl, cx, cy, u, start, t, seed):
    """P1: 아래 밖에서 솟아오르며 80→100%."""
    if u < start:
        return
    k = expo_out(seg(u, start, start + 0.4))
    jx, jy = jit(t, seed, 1.5)
    put(st, bl, cx + jx, cy + (1 - k) * 700 + jy, scale=0.8 + 0.2 * k)


def car_reveal(st, car, cx, cy, u, start, t, seed, strip_seed=0):
    """P2: 차량 컷아웃이 아래서 올라오고, 위를 덮은 찢어진 흰 종이 띠가 늦게 벗겨지며 드러난다."""
    if u < start:
        return
    k = expo_out(seg(u, start, start + 0.5))
    y_c = cy + (1 - k) * 650
    cw, ch = car.size
    # 종이 띠의 차량 내 y 위치: 차량 55% 지점에서 차량 위 밖까지 (2스텝 늦게)
    r = ease_in_out(seg(u, start + 0.17, start + 1.0))
    strip_y = lerp(ch * 0.55, -70, r)
    cut = max(0, int(strip_y))
    jx, jy = jit(t, seed, 1.5)
    x0, y0 = int(cx - cw / 2 + jx), int(y_c - ch / 2 + jy)
    if cut < ch:
        part = car.crop((0, cut, cw, ch))
        st.paste(part, (x0, y0 + cut), part)
    if r < 1:
        strip = torn_sheet(cw + 80, 46, PAPER_WHITE, 900 + strip_seed, fiber=8, top_only=False)
        st.paste(strip, (x0 - 40, int(y0 + strip_y - 30)), strip)


# ---------------- 차량 컷아웃 처리 ----------------
def load_car(name, target_w, sat):
    p = os.path.join(CUT, name)
    im = Image.open(p).convert("RGBA")
    rgb = im.convert("RGB")
    g = ImageEnhance.Contrast(ImageOps.grayscale(rgb)).enhance(1.12)
    sep = ImageOps.colorize(g, black=(46, 32, 22), white=(244, 228, 200))
    rgb = Image.blend(sep, ImageEnhance.Color(rgb).enhance(0.8), sat) if sat > 0 else sep
    out = rgb.convert("RGBA")
    out.putalpha(im.getchannel("A"))
    out = halftone_overlay(grain(out, 5, len(name)), 8, 0.07)
    s = target_w / out.width
    return out.resize((int(out.width * s), int(out.height * s)), Image.LANCZOS)


# ---------------- 섹션 ----------------
SECTIONS = [(0.0, 4.2), (4.2, 8.8), (8.8, 13.2), (13.2, 18.0), (18.0, 22.6), (22.6, 26.8), (26.8, 30.0)]
TRANS = {1: ("push_x", 0.5), 2: ("push_y", 0.5), 3: ("hole", 1.0), 4: ("tear", 0.45), 5: ("tear", 0.45), 6: ("tear", 0.45)}


def build_assets():
    A = {"tex": paper_textures()}
    A["car1"] = load_car("car_1886.png", 900, 0.0)
    A["car2"] = load_car("car_1908.png", 820, 0.0)
    A["car3"] = load_car("car_1950s.png", 1180, 0.45)
    A["car4"] = load_car("car_1973.png", 860, 0.45)
    A["car5"] = load_car("car_2020s.png", 1000, 0.6)
    # 타이틀 도로 사진: 찢어진 가장자리 사진 조각
    road = Image.open(os.path.join(HERE, "images", "s0_title.jpg")).convert("RGB")
    rw, rh = road.size
    road = road.crop((0, 0, int(rw * 0.9), int(rh * 0.9)))
    road = ImageOps.colorize(ImageEnhance.Contrast(ImageOps.grayscale(road)).enhance(1.1), (46, 32, 22), (244, 228, 200))
    road = ImageOps.fit(road, (900, 520)).convert("RGBA")
    mask = torn_piece([(0, 0), (900, 0), (900, 520), (0, 520)], (0, 0, 0), (900, 520), 5, fiber=10).getchannel("A")
    road.putalpha(mask.filter(ImageFilter.MinFilter(5)))
    A["road"] = halftone_overlay(road, 8, 0.08)
    # 블롭
    A["blob_o"] = blob((820, 700), ORANGE, 1)
    A["blob_t"] = blob((980, 640), TEAL, 2)
    A["blob_m"] = blob((1000, 640), MUSTARD, 3)
    A["blob_g"] = blob((1100, 600), OLIVE, 4)
    # 대형 배경 글자
    A["g_car"] = giant_text("CAR", 560, (120, 92, 70), 1, 0.45)
    A["g_1886"] = giant_text("1886", 520, (120, 92, 70), 2, 0.42)
    A["g_ev"] = giant_text("EV", 700, (70, 110, 110), 3, 0.40)
    # 텍스트
    A["s0_script"] = script_text("바퀴 위의", 150, BRICK)
    A["s0_stamp"] = stamp_text("140년", 190, BLUE, 10, -3)
    A["s0_pill"] = pill("자동차의 변천사", 46, INK, 11, -4)
    A["s1_pill"] = pill("1886", 56, BRICK, 12, -5)
    A["s1_stamp"] = stamp_text("최초의 자동차", 120, BLUE, 13, -3)
    A["s1_script"] = script_text("카를 벤츠의 모터바겐", 96, BRICK)
    A["s1_brush"] = brush(470, 92, MUSTARD, 14)
    A["s1_btext"] = stamp_text("최고 시속 16km", 56, BRICK, 15, -2)
    A["s2_lines"] = [stamp_text(s, sz, c, 20 + i, -3, stroke=5) for i, (s, sz, c) in enumerate(
        [("1908", 130, MUSTARD), ("포드 모델 T", 110, PAPER_WHITE), ("모두의 자동차", 118, PAPER_WHITE),
         ("1,500만 대 판매", 96, MUSTARD)])]
    A["s3_pill"] = pill("1950s", 56, BRICK, 30, -4)
    A["s3_stamp"] = stamp_text("자동차의 황금기", 124, PAPER_WHITE, 31, -3)
    A["s3_script"] = script_text("고속도로 · 교외 · 테일핀", 92, INK)
    A["s4_rep"] = stamp_text("오일쇼크", 150, BRICK, 40, 0)
    A["s4_bar"] = stamp_text("1973 OIL SHOCK", 96, PAPER_WHITE, 41, 0)
    A["s4_script"] = script_text("작고 연비 좋은 차로", 96, INK)
    A["s5_pill"] = pill("2020s", 56, BRICK, 50, -4)
    A["s5_stamp"] = stamp_text("전기차 · 자율주행", 116, BLUE, 51, -3)
    A["s5_script"] = script_text("엔진 대신 배터리,", 92, BRICK)
    A["s5_script2"] = script_text("운전자 대신 AI", 92, BRICK)
    A["s5_brush"] = brush(560, 100, MUSTARD, 52)
    A["s6_script"] = script_text("다음 140년은?", 230, BLUE, -4)
    A["s6_small"] = script_text("바퀴 위의 이야기는 계속됩니다", 80, BRICK, -3)
    # 찢어 나눈 배경(P14) 조각과 모서리 프레임(P15) 조각
    A["split"] = [
        torn_piece([(-60, -60), (1150, -60), (620, 1140), (-60, 1140)], MUSTARD, (W, H), 60),
        torn_piece([(1150, -60), (1980, -60), (1980, 520), (900, 560)], PINK, (W, H), 61),
        torn_piece([(900, 560), (1980, 520), (1980, 1140), (620, 1140)], TEAL, (W, H), 62),
    ]
    A["split"] = [halftone_overlay(s, 10, 0.08) for s in A["split"]]
    A["corners"] = [
        (torn_piece([(-80, 1140), (-80, 620), (560, 1140)], BRICK, (W, H), 70), (0, 1)),
        (torn_piece([(-80, 620), (-80, -80), (260, -80)], BLUE, (W, H), 71), (-1, 0)),
        (torn_piece([(260, -80), (1500, -80), (900, 150)], OLIVE, (W, H), 72), (0, -1)),
        (torn_piece([(1500, -80), (2000, -80), (2000, 900), (1700, 700)], MUSTARD, (W, H), 73), (1, 0)),
        (torn_piece([(2000, 900), (2000, 1160), (1250, 1160)], ORANGE, (W, H), 74), (1, 1)),
    ]
    # 대각선 색종이 띠(P10): 겹겹이 쌓인 산 모양(바깥 빨강 → 노랑 → 분홍 → 초록)
    bands = []
    for i, c in enumerate([BRICK, MUSTARD, PINK, OLIVE]):
        apex = (760 + i * 20, 90 + i * 190)
        poly = [(-500 + i * 120, H + 120), apex, (2100 - i * 160, H + 120)]
        bands.append(torn_piece(poly, c, (W, H), 80 + i, fiber=8))
    A["bands"] = [halftone_overlay(b, 10, 0.07) for b in bands]
    A["tear_sheet"] = torn_sheet(W + 60, H + 200, KRAFT, 99, fiber=12)
    return A


def background(A, t):
    return A["tex"][int(t * BOIL_FPS) % len(A["tex"])].convert("RGBA").copy()


def sec0(st, d, u, t, A):
    put(st, A["g_car"], 1380, 470, op=1.0 if u >= 0.9 else 0)
    blob_rise(st, A["blob_o"], 1300, 560, u, 0.15, t, 1)
    car_reveal(st, A["road"], 1300, 540, u, 0.35, t, 2, strip_seed=1)
    doodle(d, [(-20, 880), (180, 760), (330, 880), (470, 760), (620, 860)], seg(u, 0.9, 1.5), TEAL)
    script_write(st, A["s0_script"], 470, 360, u, 1.2, 0.55, t, 3)
    stamp(st, A["s0_stamp"], 470, 560, u, 1.8, t, 4)
    pill_pop(st, A["s0_pill"], 470, 760, u, 2.1, t, 5)


def sec1(st, d, u, t, A):
    put(st, A["g_1886"], 1240, 430, op=1.0 if u >= 0.8 else 0)
    blob_rise(st, A["blob_t"], 1250, 640, u, 0.15, t, 11)
    car_reveal(st, A["car1"], 1250, 610, u, 0.35, t, 12, strip_seed=2)
    doodle(d, [(1980, 300), (1780, 200), (1640, 330), (1500, 220)], seg(u, 0.9, 1.4), ORANGE)
    pill_pop(st, A["s1_pill"], 320, 250, u, 1.0, t, 13)
    stamp(st, A["s1_stamp"], 470, 420, u, 1.35, t, 14)
    script_write(st, A["s1_script"], 470, 570, u, 1.6, 0.8, t, 15)
    if u >= 2.4:
        jx, jy = jit(t, 16)
        put(st, wipe(A["s1_brush"], seg(u, 2.4, 2.6)), 470 + jx, 730 + jy)
        stamp(st, A["s1_btext"], 470, 728, u, 2.62, t, 17)


def sec2(st, d, u, t, A):
    # P10: 대각선 색종이 띠가 아래에서 쓸려 올라오고, 띠마다 문구 한 줄
    pos = [(780, 250), (790, 430), (800, 610), (810, 790)]
    for i, band in enumerate(A["bands"]):           # 띠를 먼저 모두 깔고
        st_i = 0.1 + i * 0.28
        if u < st_i:
            continue
        k = expo_out(seg(u, st_i, st_i + 0.35))
        jx, jy = jit(t, 20 + i, 1.5)
        st.paste(band, (int(jx), int((1 - k) * 900 + jy)), band)
    car_reveal(st, A["car2"], 1500, 820, u, 1.3, t, 25, strip_seed=3)
    for i, line in enumerate(A["s2_lines"]):        # 문구는 띠 위에
        stamp(st, line, pos[i][0], pos[i][1], u, 0.1 + i * 0.28 + 0.22, t, 30 + i)


def sec3(st, d, u, t, A):
    # P14: 찢어 나눈 배경 조각
    for i, pc in enumerate(A["split"]):
        if u >= 0.05 + i * 0.12:
            jx, jy = jit(t, 40 + i, 1.2)
            st.paste(pc, (int(jx), int(jy)), pc)
    car_reveal(st, A["car3"], 1180, 720, u, 0.9, t, 41, strip_seed=4)
    pill_pop(st, A["s3_pill"], 300, 170, u, 1.5, t, 42)
    stamp(st, A["s3_stamp"], 560, 320, u, 1.8, t, 43)
    script_write(st, A["s3_script"], 620, 470, u, 2.05, 0.8, t, 44)


def sec4(st, d, u, t, A):
    blob_rise(st, A["blob_m"], 960, 560, u, 0.15, t, 50)
    # P9: 같은 단어가 아래에서 위로 반복 적층
    rep = A["s4_rep"]
    for i in range(5):
        st_i = 0.5 + i * 0.1
        if u >= st_i:
            jx, jy = jit(t, 60 + i, 1.5)
            y = 860 - i * 140
            for x in (430, 1490):
                put(st, rep, x + jx, y + jy)
    car_reveal(st, A["car4"], 960, 650, u, 0.35, t, 51, strip_seed=5)
    if u >= 1.2:  # 하단 빨간 띠 + 흰 글자
        k = expo_out(seg(u, 1.2, 1.4))
        jx, jy = jit(t, 70)
        bar = Image.new("RGBA", (1000, 150), BRICK + (255,))
        bar = rough_alpha(grain(bar, 8, 3), 3, 0.3)
        put(st, bar, 960 + jx, 990 + (1 - k) * 200 + jy)
        stamp(st, A["s4_bar"], 960, 985, u, 1.35, t, 71)
    doodle(d, [(-20, 150), (180, 70), (330, 170), (500, 90)], seg(u, 1.0, 1.5), TEAL)
    script_write(st, A["s4_script"], 1000, 110, u, 1.7, 0.7, t, 72)


def sec5(st, d, u, t, A):
    put(st, A["g_ev"], 1380, 420, op=1.0 if u >= 0.8 else 0)
    blob_rise(st, A["blob_g"], 1380, 640, u, 0.15, t, 80)
    car_reveal(st, A["car5"], 1390, 650, u, 0.35, t, 81, strip_seed=6)
    doodle(d, [(1980, 900), (1760, 1000), (1600, 880), (1420, 1010)], seg(u, 0.9, 1.4), ORANGE)
    pill_pop(st, A["s5_pill"], 260, 230, u, 1.0, t, 82)
    stamp(st, A["s5_stamp"], 470, 400, u, 1.3, t, 83)
    if u >= 1.6:
        jx, jy = jit(t, 84)
        put(st, wipe(A["s5_brush"], seg(u, 1.6, 1.8)), 400 + jx, 560 + jy)
    script_write(st, A["s5_script"], 400, 555, u, 1.8, 0.6, t, 85)
    script_write(st, A["s5_script2"], 400, 680, u, 2.3, 0.6, t, 86)


def sec6(st, d, u, t, A):
    # P15: 모서리 색종이가 하나씩 슬며시 들어온다
    for i, (pc, (dx, dy)) in enumerate(A["corners"]):
        st_i = 0.35 + i * 0.18
        if u < st_i:
            continue
        k = expo_out(seg(u, st_i, st_i + 0.3))
        jx, jy = jit(t, 90 + i, 1.2)
        st.paste(pc, (int(dx * (1 - k) * 400 + jx), int(dy * (1 - k) * 400 + jy)), pc)
    script_write(st, A["s6_script"], 960, 500, u, 1.3, 1.1, t, 96)
    script_write(st, A["s6_small"], 960, 700, u, 2.2, 0.6, t, 97)


SEC = [sec0, sec1, sec2, sec3, sec4, sec5, sec6]


def render_section(A, i, t):
    a, _ = SECTIONS[i]
    st = background(A, t)
    SEC[i](st, ImageDraw.Draw(st), t - a, t, A)
    return st


def render_content(A, t):
    t = step_time(t)
    i = next(k for k, (a, b) in enumerate(SECTIONS) if a <= t < b or k == len(SECTIONS) - 1)
    cur = render_section(A, i, t)
    tr = TRANS.get(i)
    if not tr:
        return cur
    kind, dur = tr
    u = t - SECTIONS[i][0]
    if u >= dur:
        return cur
    prev = render_section(A, i - 1, SECTIONS[i][0] - 1e-3)   # 이전 장면은 마지막 모습으로 고정
    if kind in ("push_x", "push_y"):  # P11: 한 장의 종이처럼 밀려 나가고 다음 장이 붙어 들어온다
        k = expo_out(u / dur)
        out = Image.new("RGBA", (W, H))
        if kind == "push_x":
            off = int(k * W)
            out.paste(prev, (-off, 0))
            out.paste(cur, (W - off, 0))
            sh = Image.new("RGBA", (40, H), (40, 28, 20, 70))
            out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)), (max(0, min(W - 40, W - off - 20)), 0))
        else:
            off = int(k * H)
            out.paste(prev, (0, -off))
            out.paste(cur, (0, H - off))
            sh = Image.new("RGBA", (W, 40), (40, 28, 20, 70))
            out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)), (0, max(0, min(H - 40, H - off - 20))))
        return out
    if kind == "hole":  # P12: 구겨진 종이 뭉치 → 구멍이 커지며 다음 장면이 보인다
        k = ease_in_out(u / dur)
        cx, cy = lerp(1500, 960, k), lerp(260, 540, k)
        r = lerp(40, 1400, k ** 1.6)
        rng = random.Random(3)
        pts = []
        for j in range(90):
            a = 2 * math.pi * j / 90
            rr = r * (1 + 0.05 * math.sin(a * 3) + 0.03 * math.sin(a * 11) + rng.uniform(-0.035, 0.035))
            pts.append((cx + rr * math.cos(a), cy + rr * 0.8 * math.sin(a)))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon(pts, fill=255)
        out = prev.copy()
        out.paste(cur, (0, 0), m)
        # 구멍 가장자리: 말려 올라간 흰 종이 테두리 + 그림자
        ring = Image.new("L", (W, H), 0)
        ImageDraw.Draw(ring).line(pts + [pts[0]], fill=255, width=int(18 + 30 * (1 - k)))
        out.paste(Image.new("RGBA", (W, H), (60, 45, 35, 255)), (6, 8), ring.filter(ImageFilter.GaussianBlur(6)))
        out.paste(Image.new("RGBA", (W, H), PAPER_WHITE + (255,)), (0, 0), ring)
        return out
    if kind == "tear":  # P13: 윗변이 찢어진 새 종이가 아래에서 올라와 덮는다
        k = expo_out(u / dur)
        top = int(lerp(H + 40, -80, k))
        sheet = A["tear_sheet"]
        m = Image.new("L", (W, H), 0)
        m.paste(sheet.getchannel("A"), (-30, top))
        out = prev.copy()
        edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        edge.paste(sheet, (-30, top))
        out.alpha_composite(edge)                     # 흰 섬유층 + 새 종이
        body = m.point(lambda v: 255 if v > 250 else 0).filter(ImageFilter.MinFilter(9))
        out.paste(cur, (0, 0), body)                  # 새 종이 위에 이미 다음 장면이 올라와 있다
        return out
    return cur


def render_frame(A, fi, content):
    arr = np.asarray(content.convert("RGB"), np.int16) + A["film"][fi % len(A["film"])]
    return arr.clip(0, 255).astype(np.uint8)


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found")
    A = build_assets()
    A["film"] = [np.random.default_rng(k).normal(0, 3.5, (H, W, 1)).astype(np.int16) for k in range(5)]
    only = sys.argv[1:]
    if only:
        dd = os.environ.get("PREVIEW_DIR", HERE)
        for ts in only:
            fi = int(round(float(ts) * FPS))
            Image.fromarray(render_frame(A, fi, render_content(A, fi / FPS))).save(os.path.join(dd, f"pc_{ts}.png"))
        return
    n = int(DUR * FPS)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    last, content = None, None
    for fi in range(n):
        key = math.floor(fi / FPS * STEP_FPS + 1e-6)
        if key != last:
            content, last = render_content(A, fi / FPS), key
        proc.stdin.write(render_frame(A, fi, content).tobytes())
        if fi % 90 == 0:
            print(f"frame {fi}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
