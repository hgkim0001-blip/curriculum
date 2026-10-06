"""Vox-style motion graphic v3: 자동차의 변천사 (30s, 1920x1080, 30fps).

비디오하이브 샘플/모션패턴_분석_VOX_Typography.md 의 형식을 적용한 버전.
- 비주얼: 회백색 종이 + 가는 모눈, 명조 제목(핵심 단어만 굵게), 타자기체 캡션, 흑백·세피아 사진 + 톱니 테두리, 빨강 하나만 강조
- 모션: 12fps 스텝, Whip-In(모션블러+디포커스), 단어 단위 타이핑, 빨간 손그림 write-on(타원·화살표·밑줄·취소선),
        Slide Push, Zoom-Through 매치컷, Scatter Pop-In + Pull-Back Defocus, Snap Zoom 엔딩, 섹션 사이 하드컷
출력: car_history_vox_v3.mp4
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
PAPER = os.path.join(HERE, "assets", "paper_bg.jpg")
OUT = os.path.join(HERE, "car_history_vox_v3.mp4")

W, H, FPS, DUR = 1920, 1080, 30, 30.0
STEP_FPS = 12                     # 12fps 스텝 애니메이션
SHUTTER = 1 / 24                  # 모션 블러 셔터

BG = (243, 241, 237)
GRID = (222, 221, 217)
INK = (22, 22, 22)
RED = (214, 32, 38)
CARD_WHITE = (250, 249, 245)

USER_FONTS = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts")


def find_font(*names):
    for n in names:
        for d in (USER_FONTS, r"C:\Windows\Fonts"):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise FileNotFoundError(names)


F_SERIF = find_font("NanumMyeongjo.ttf", "batang.ttc")
F_SERIF_B = find_font("NanumMyeongjoExtraBold.ttf", "NanumMyeongjoBold.ttf")
F_YEAR = find_font("timesbd.ttf")
F_TYPE = find_font("courbd.ttf", "cour.ttf")                          # 타자기체(영문·숫자)
F_TYPE_KO = find_font("NanumMyeongjoBold.ttf", "NanumMyeongjo.ttf")  # 한글 타자기 대체

_font_cache = {}


def font(path, size):
    key = (path, int(size))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, int(size))
    return _font_cache[key]


# ---------------- easing / time ----------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def step_time(t):
    return math.floor(t * STEP_FPS + 1e-6) / STEP_FPS


def expo_out(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def zoom_curve(x):
    """M5: 짧게 가속한 뒤 길게 감속."""
    return expo_out(clamp(x) ** 1.6)


def snap(x):
    """M6: 거의 선형으로 가다가 끝에서 급정지."""
    x = clamp(x)
    return x / 0.85 * 0.9 if x < 0.85 else 0.9 + 0.1 * (1 - (1 - (x - 0.85) / 0.15) ** 3)


def seg(u, a, b):
    return clamp((u - a) / (b - a))


# ---------------- background ----------------
def build_background():
    bg = np.ones((H, W, 3), np.float32) * np.array(BG, np.float32)
    if os.path.exists(PAPER):  # 구겨진 종이 질감을 은은하게 곱한다
        p = ImageOps.fit(Image.open(PAPER).convert("L"), (W, H), Image.LANCZOS)
        lum = np.asarray(p, np.float32) / 255
        bg *= (1 - 0.22 * (1 - lum / lum.max()))[..., None]
    img = Image.fromarray(bg.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 36):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 36):
        d.line([(0, y), (W, y)], fill=GRID, width=1)
    return img


# ---------------- text ----------------
def type_sprite(text, size, color=INK):
    """타자기체: 영문·숫자는 Courier, 한글은 명조로 run 단위 렌더링."""
    runs, cur, cur_ascii = [], "", None
    for ch in text:
        a = ord(ch) < 128
        if cur and a != cur_ascii:
            runs.append((cur, cur_ascii))
            cur = ""
        cur += ch
        cur_ascii = a
    if cur:
        runs.append((cur, cur_ascii))
    fa, fk = font(F_TYPE, size), font(F_TYPE_KO, size * 0.92)
    wsum = sum((fa if a else fk).getlength(r) for r, a in runs)
    asc = max(fa.getmetrics()[0], fk.getmetrics()[0])
    desc = max(fa.getmetrics()[1], fk.getmetrics()[1])
    im = Image.new("RGBA", (int(wsum) + 20, asc + desc + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 10
    for r, a in runs:
        f = fa if a else fk
        d.text((x, 10 + asc), r, font=f, fill=color, anchor="ls")
        x += f.getlength(r)
    return im, wsum, asc + desc


def serif_sprite(text, size, bold=False, color=INK):
    f = font(F_SERIF_B if bold else F_SERIF, size)
    asc, desc = f.getmetrics()
    w = f.getlength(text)
    im = Image.new("RGBA", (int(w) + 20, asc + desc + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10 + asc), text, font=f, fill=color, anchor="ls")
    return im, w, asc + desc


def layout(words, size, bold=(), kind="serif"):
    """단어별 스프라이트와 줄 안에서의 x 위치."""
    items, x, h = [], 0, 0
    space = font(F_SERIF, size).getlength(" ") * (1.0 if kind == "serif" else 0.9)
    for i, wd in enumerate(words):
        spr, w, hh = serif_sprite(wd, size, i in bold) if kind == "serif" else type_sprite(wd, size)
        items.append(dict(spr=spr, x=x, w=w))
        x += w + space
        h = max(h, hh)
    return dict(items=items, h=h, width=x - space)


def draw_words(stage, L, X, Y, u, start, per=0.2):
    """M2: 단어 단위 타이핑 — 새 단어는 흐림→선명, 살짝 떠오른다. 단어 박스 목록을 돌려준다."""
    boxes = []
    for i, it in enumerate(L["items"]):
        boxes.append((X + it["x"], Y, X + it["x"] + it["w"], Y + L["h"]))
        p = (u - (start + i * per)) / 0.14
        if p < 0:
            continue
        spr = it["spr"]
        if p < 1:
            spr = spr.filter(ImageFilter.GaussianBlur(5 * (1 - p)))
        stage.paste(spr, (int(X + it["x"] - 10), int(Y - 10 + 8 * (1 - clamp(p)))), spr)
    return boxes


def words_done(L, start, per=0.2):
    return start + (len(L["items"]) - 1) * per + 0.14


def box_union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


# ---------------- red hand-drawn annotations (M3) ----------------
def hand_ellipse(d, box, p, seed=0, width=6):
    if p <= 0:
        return
    x0, y0, x1, y1 = box
    px, py = 0.16 * (y1 - y0) + 6, 0.08 * (y1 - y0) + 4   # 글자 크기에 비례한 여백
    x0, y0, x1, y1 = x0 - px, y0 - py, x1 + px, y1 + py
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    a0 = -2.5 + random.Random(seed).uniform(-0.3, 0.3)
    total = 2 * math.pi * 1.14                     # 시작점을 지나쳐 튀어나오게
    n = max(2, int(140 * clamp(p)))
    pts = []
    for i in range(n):
        a = a0 + total * i / 140
        wob = 1 + 0.035 * math.sin(a * 3 + seed)   # 손떨림
        pts.append((cx + rx * wob * math.cos(a), cy + ry * wob * math.sin(a) - 9 * (i / 140)))
    d.line(pts, fill=RED, width=width, joint="curve")


def hand_arrow(d, p0, p1, p, bend=0.25, width=5):
    if p <= 0:
        return
    (x0, y0), (x1, y1) = p0, p1
    cx = (x0 + x1) / 2 - (y1 - y0) * bend
    cy = (y0 + y1) / 2 + (x1 - x0) * bend
    n = max(2, int(60 * clamp(p)))
    pts = []
    for i in range(n):
        s = i / 59
        pts.append(((1 - s) ** 2 * x0 + 2 * (1 - s) * s * cx + s * s * x1,
                    (1 - s) ** 2 * y0 + 2 * (1 - s) * s * cy + s * s * y1))
    d.line(pts, fill=RED, width=width, joint="curve")
    if p >= 1:
        ang = math.atan2(y1 - cy, x1 - cx)
        for da in (2.6, -2.6):
            d.line([(x1, y1), (x1 + 30 * math.cos(ang + da), y1 + 30 * math.sin(ang + da))], fill=RED, width=width)


def hand_underline(d, box, p, width=5):
    if p <= 0:
        return
    x0, _, x1, y1 = box
    n = max(2, int(50 * clamp(p)))
    pts = [(lerp(x0 - 8, x1 + 14, i / 49), y1 + 8 + 3 * math.sin(i / 49 * 7) - 4 * (i / 49)) for i in range(n)]
    d.line(pts, fill=RED, width=width, joint="curve")


def hand_strike(d, box, p, width=6):
    if p <= 0:
        return
    x0, y0, x1, y1 = box
    ym = (y0 + y1) / 2
    d.line([(x0 - 6, ym + 4), (lerp(x0 - 6, x1 + 8, clamp(p)), ym + 4 - 8 * clamp(p))], fill=RED, width=width)


# ---------------- photo cards ----------------
def treat(im, mode):
    g = ImageEnhance.Contrast(ImageOps.grayscale(im)).enhance(1.15)
    if mode == "sepia":
        return ImageOps.colorize(g, black=(38, 28, 20), white=(244, 232, 210))
    return ImageOps.colorize(g, black=(18, 18, 18), white=(246, 244, 239))


BORDER, BOTTOM = 20, 66


def make_card(name, mode, inner_w, caption):
    """흑백·세피아 사진 + 흰 톱니 테두리(deckled edge) + 타자기체 캡션 + 부드러운 그림자."""
    im = Image.open(os.path.join(IMG_DIR, name)).convert("RGB")
    iw, ih = im.size
    im = im.crop((0, 0, int(iw * 0.9), int(ih * 0.9)))   # 우하단 ✦ 워터마크 제거
    inner_h = int(inner_w * 9 / 16)
    im = treat(ImageOps.fit(im, (inner_w, inner_h), Image.LANCZOS), mode)
    cw, ch = inner_w + 2 * BORDER, inner_h + BORDER + BOTTOM
    pad = 50
    out = Image.new("RGBA", (cw + 2 * pad, ch + 2 * pad), (0, 0, 0, 0))
    rng = random.Random(inner_w)
    pts = []

    def edge(xa, ya, xb, yb, nx, ny):
        n = int(math.hypot(xb - xa, yb - ya) / 7)
        for i in range(n):
            s = i / n
            o = (3 if i % 2 else 0) + rng.uniform(0, 1.2)
            pts.append((pad + lerp(xa, xb, s) + nx * o, pad + lerp(ya, yb, s) + ny * o))
    edge(0, 0, cw, 0, 0, -1)
    edge(cw, 0, cw, ch, 1, 0)
    edge(cw, ch, 0, ch, 0, 1)
    edge(0, ch, 0, 0, -1, 0)
    shadow = Image.new("L", out.size, 0)
    ImageDraw.Draw(shadow).polygon([(x + 8, y + 12) for x, y in pts], fill=85)
    out.paste(Image.new("RGBA", out.size, (30, 25, 20, 255)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(out).polygon(pts, fill=CARD_WHITE + (255,))
    out.paste(im, (pad + BORDER, pad + BORDER))
    cap, cwid, chh = type_sprite(caption, 26, (60, 58, 55))
    out.alpha_composite(cap, (int(pad + cw / 2 - cwid / 2 - 10), int(pad + BORDER + inner_h + (BOTTOM - chh) / 2 - 10)))
    a = np.asarray(out).astype(np.int16)
    a[..., :3] = np.clip(a[..., :3] + np.random.default_rng(inner_w).normal(0, 4, a.shape[:2])[..., None], 0, 255)
    out = Image.fromarray(a.astype(np.uint8), "RGBA")
    return dict(spr=out, inner_w=inner_w, inner_h=inner_h, photo_dy=-(BOTTOM - BORDER) / 2)


def rotated(card, angle):
    return card["spr"].rotate(angle, expand=True, resample=Image.BICUBIC)


# ---------------- compositing ----------------
def smear(spr, vx, vy, n=8):
    """모션 블러: 이동 반대 방향으로 n장을 평균. (새 이미지, 원래 좌상단의 위치) 반환."""
    a = np.asarray(spr, np.float32) / 255
    pm = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
    h, w = pm.shape[:2]
    offs = [(-vx * i / (n - 1), -vy * i / (n - 1)) for i in range(n)]
    mnx, mny = min(o[0] for o in offs), min(o[1] for o in offs)
    mxx, mxy = max(o[0] for o in offs), max(o[1] for o in offs)
    acc = np.zeros((h + int(math.ceil(mxy - mny)) + 1, w + int(math.ceil(mxx - mnx)) + 1, 4), np.float32)
    for ox, oy in offs:
        x, y = int(round(ox - mnx)), int(round(oy - mny))
        acc[y:y + h, x:x + w] += pm
    acc /= n
    al = acc[..., 3:4]
    rgb = np.where(al > 1e-4, acc[..., :3] / np.maximum(al, 1e-4), 0)
    img = Image.fromarray((np.concatenate([rgb, al], -1) * 255).clip(0, 255).astype(np.uint8), "RGBA")
    return img, (-mnx, -mny)


def place(stage, spr, cx, cy, blur=0.0, vel=(0, 0)):
    """중심 (cx, cy)에 붙이기. blur=흐림 반경, vel=이번 셔터 동안의 이동량(모션 블러)."""
    if blur > 0.4:
        spr = spr.filter(ImageFilter.GaussianBlur(blur))
    bw, bh = spr.size
    ox = oy = 0
    if math.hypot(*vel) > 4:
        spr, (ox, oy) = smear(spr, vel[0], vel[1])
    stage.paste(spr, (int(round(cx - bw / 2 - ox)), int(round(cy - bh / 2 - oy))), spr)


def whip(stage, spr, cx, cy, u, start, frm=(0, 900), dur=0.35, focus=0.8):
    """M1: 화면 밖에서 Expo Out으로 날아와 멈추고, 모션 블러 + 흐림→선명."""
    if u < start:
        return

    def pos(uu):
        k = expo_out((uu - start) / dur)
        return cx + frm[0] * (1 - k), cy + frm[1] * (1 - k)
    x, y = pos(u)
    xp, yp = pos(u - SHUTTER)
    place(stage, spr, x, y, blur=7 * (1 - clamp((u - start) / focus)), vel=(x - xp, y - yp))


def camera(img, scale, fx, fy, blur=0.0):
    if scale <= 1.0005 and blur < 0.4:
        return img
    if scale > 1.0005:
        cw, ch = W / scale, H / scale
        x0 = clamp(fx - cw / 2, 0, W - cw)
        y0 = clamp(fy - ch / 2, 0, H - ch)
        img = img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    if blur >= 0.4:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return img


def draw_year(stage, x, y, u, start, y_from, y_to, suffix=""):
    """연도 카운트업(12fps 스텝) + 흐림→선명 등장."""
    if u < start:
        return
    k = expo_out((u - start) / 0.6)
    label = f"{int(round(lerp(y_from, y_to, k)))}{suffix if k >= 0.999 else ''}"
    f = font(F_YEAR, 170)
    l, t, r, b = f.getbbox(label)
    spr = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(spr).text((10 - l, 10 - t), label, font=f, fill=INK)
    p = clamp((u - start) / 0.25)
    if p < 1:
        spr = spr.filter(ImageFilter.GaussianBlur(7 * (1 - p)))
    stage.paste(spr, (int(x - 10), int(y - 10)), spr)


# ---------------- sections ----------------
CARD_C = (1300, 470)
SECTIONS = [(0.0, 3.6), (3.6, 8.4), (8.4, 13.8), (13.8, 19.0), (19.0, 24.2), (24.2, 30.0)]


def build_assets():
    A = {"bg": build_background()}
    A["c0"] = make_card("s0_title.jpg", "bw", 980, "THE ROAD · 1886 - 2026")
    A["c1"] = make_card("s1_1886.jpg", "sepia", 860, "1886 · Benz Patent-Motorwagen")
    A["c2"] = make_card("s2_1908.jpg", "sepia", 860, "1908 · Ford Model T")
    A["c3"] = make_card("s3_1950s.jpg", "bw", 860, "1950s · American Dream")
    A["c3b"] = make_card("s2_1908.jpg", "sepia", 380, "1908")
    A["c4"] = make_card("s4_1973.jpg", "bw", 820, "1973 · Oil Crisis")
    A["c5"] = make_card("s5_2020s.jpg", "bw", 800, "2020s · Electric & Autonomous")
    A["r0"] = rotated(A["c0"], -2)
    A["r1"] = rotated(A["c1"], 3)
    A["r3b"] = rotated(A["c3b"], 8)
    A["r4"] = rotated(A["c4"], -2)
    A["r5"] = rotated(A["c5"], 2)
    A["L0"] = layout(["바퀴", "위의", "140년"], 112, bold={2})
    A["L0s"] = layout(["자동차의", "변천사", "1886", "-", "2026"], 34, kind="type")
    A["L1"] = layout(["최초의", "자동차"], 96, bold={1})
    A["L1s"] = layout(["카를", "벤츠의", "‘페이턴트", "모터바겐’"], 34, kind="type")
    A["L1n"] = layout(["최고", "시속", "16km"], 34, kind="type")
    A["L2"] = layout(["포드", "모델", "T"], 96, bold={1, 2})
    A["L2s"] = layout(["귀족의", "사치품", "→", "모두의", "자동차"], 36, kind="type")
    A["L2n"] = layout(["조립", "라인", "·", "1,500만", "대", "판매"], 30, kind="type")
    A["L3"] = layout(["자동차의", "황금기"], 96, bold={1})
    A["L3s"] = layout(["고속도로", "·", "교외", "·", "테일핀"], 34, kind="type")
    A["L4"] = layout(["오일", "쇼크"], 96, bold={1})
    A["L4s"] = layout(["작고", "연비", "좋은", "차의", "시대로"], 34, kind="type")
    A["L4b"] = [layout(["1973년", "10월"], 30, kind="type"), layout(["중동", "산유국"], 30, kind="type"),
                layout(["석유", "수출", "금지"], 30, kind="type")]
    A["L4c"] = layout(["휘발유", "값", "약", "4배", "상승"], 34, kind="type")
    A["L5a"] = layout(["엔진", "대신", "배터리,"], 76, bold={2})
    A["L5b"] = layout(["운전자", "대신", "AI"], 76, bold={2})
    A["L5c"] = layout(["다음", "140년은?"], 112, bold={1})
    rng = np.random.default_rng(3)
    A["grain"] = [rng.normal(0, 4.5, (H, W, 1)).astype(np.int16) for _ in range(6)]
    return A


def full_scale(card):
    return W / card["inner_w"]


def sec0(st, d, u, A):
    whip(st, A["r0"], 960, 390, u, 0.15, frm=(0, 900))
    L = A["L0"]
    b = draw_words(st, L, 960 - L["width"] / 2, 760, u, 0.65)
    t_ell = words_done(L, 0.65) + 0.12
    hand_ellipse(d, b[2], seg(u, t_ell, t_ell + 0.5), seed=1)
    hand_arrow(d, (b[2][2] + 30, b[2][1] - 6), (b[2][2] + 190, 690), seg(u, t_ell + 0.5, t_ell + 0.8), bend=0.35)
    S = A["L0s"]
    draw_words(st, S, 960 - S["width"] / 2, 920, u, 2.0, per=0.12)


def sec1(st, d, u, A):
    whip(st, A["r1"], *CARD_C, u, 0.15, frm=(0, 900))
    draw_year(st, 130, 130, u, 0.35, 1880, 1886)
    b = draw_words(st, A["L1"], 135, 400, u, 0.7)
    draw_words(st, A["L1s"], 140, 545, u, 1.2, per=0.14)
    nb = draw_words(st, A["L1n"], 140, 612, u, 1.75, per=0.14)
    hand_ellipse(d, b[0], seg(u, 1.3, 1.8), seed=2)
    hand_arrow(d, ((b[0][0] + b[0][2]) / 2 + 40, b[0][1] - 18), (855, 300), seg(u, 1.8, 2.1), bend=-0.18)
    hand_underline(d, box_union(nb), seg(u, 2.3, 2.65))


def sec2(st, d, u, A):
    draw_year(st, 130, 130, u, 0.15, 1886, 1908)
    draw_words(st, A["L2"], 135, 400, u, 0.35)
    if u >= 0.6:  # M4 Slide Push: 오른쪽 밖에서 수평으로 밀고 들어온다
        def xk(uu):
            return CARD_C[0] + 1200 * (1 - expo_out((uu - 0.6) / 0.7))
        place(st, A["c2"]["spr"], xk(u), CARD_C[1], blur=5 * (1 - seg(u, 0.6, 1.4)), vel=(xk(u) - xk(u - SHUTTER), 0))
    sb = draw_words(st, A["L2s"], 140, 545, u, 1.2, per=0.14)
    draw_words(st, A["L2n"], 140, 615, u, 2.0, per=0.12)
    hand_strike(d, sb[1], seg(u, 2.15, 2.4))
    hand_ellipse(d, sb[3], seg(u, 2.45, 2.95), seed=3)
    hand_arrow(d, ((sb[3][0] + sb[3][2]) / 2 + 10, sb[3][1] - 12), (860, 480), seg(u, 2.95, 3.25), bend=-0.15)
    z = zoom_curve(seg(u, 4.4, 5.3))  # M5 Zoom-Through: 사진 속으로 줌인
    if z > 0:
        s = math.exp(lerp(0, math.log(full_scale(A["c2"])), z))
        return (s, CARD_C[0], CARD_C[1] + A["c2"]["photo_dy"], 3.5 * math.sin(math.pi * z))


def sec3(st, d, u, A):
    small = A["r3b"]
    st.paste(small, (int(1760 - small.width / 2), int(150 - small.height / 2)), small)
    c = A["c3"]["spr"]
    st.paste(c, (int(CARD_C[0] - c.width / 2), int(CARD_C[1] - c.height / 2)), c)
    draw_year(st, 130, 130, u, 1.0, 1908, 1950, "s")
    b = draw_words(st, A["L3"], 135, 400, u, 1.25)
    draw_words(st, A["L3s"], 140, 545, u, 1.75, per=0.14)
    hand_ellipse(d, b[1], seg(u, 2.2, 2.7), seed=4)
    hand_arrow(d, (b[1][2] + 26, b[1][3] + 4), (862, 610), seg(u, 2.7, 3.0), bend=-0.35)
    z = zoom_curve(seg(u, 0.1, 0.95))  # M5 후반: 가득 찬 사진에서 줌아웃
    if z < 1:
        s = math.exp(lerp(math.log(full_scale(A["c3"])), 0, z))
        return (s, CARD_C[0], CARD_C[1] + A["c3"]["photo_dy"], 3.5 * math.sin(math.pi * z))


def sec4(st, d, u, A):
    whip(st, A["r4"], 1250, 470, u, 0.15, frm=(1300, 0))
    draw_year(st, 150, 120, u, 0.3, 1950, 1973)
    b = draw_words(st, A["L4"], 155, 330, u, 0.6)
    draw_words(st, A["L4s"], 160, 470, u, 1.1, per=0.13)
    y, k0 = 640, 0.45
    for L in A["L4b"]:  # M8: 타자기 메모가 차례로 붙는다
        draw_words(st, L, 160, y, u, k0, per=0.1)
        k0 += len(L["items"]) * 0.1
        y += 48
    cb = draw_words(st, A["L4c"], 1060, 845, u, 1.5, per=0.12)
    hand_ellipse(d, b[1], seg(u, 1.2, 1.6), seed=5)
    hand_ellipse(d, cb[3], seg(u, 2.1, 2.5), seed=6)
    hand_arrow(d, (cb[3][0] + 10, cb[3][1] - 18), (1180, 770), seg(u, 2.5, 2.8), bend=0.3)
    k = ease_in_out(seg(u, 3.9, 4.8))  # M7 Pull-Back Defocus
    return (lerp(1.1, 1.0, k), W / 2, H / 2, 5 * math.sin(math.pi * k))


def sec5(st, d, u, A):
    whip(st, A["r5"], 1330, 420, u, 0.15, frm=(1300, 0))
    draw_year(st, 130, 110, u, 0.35, 1973, 2020, "s")
    a = draw_words(st, A["L5a"], 135, 330, u, 0.7, per=0.17)
    b = draw_words(st, A["L5b"], 135, 440, u, 1.25, per=0.17)
    hand_ellipse(d, a[2], seg(u, 1.85, 2.25), seed=7)
    hand_ellipse(d, b[2], seg(u, 2.25, 2.65), seed=8)
    c = draw_words(st, A["L5c"], 135, 690, u, 2.8, per=0.22)
    hand_ellipse(d, c[1], seg(u, 3.35, 3.85), seed=9, width=7)
    k = snap(seg(u, 4.0, 4.55))  # M6 Snap Zoom Push-In
    if k > 0:
        bx = box_union(c)
        return (lerp(1.0, 1.7, k), (bx[0] + bx[2]) / 2 + 60, (bx[1] + bx[3]) / 2, 0)


SEC_FUNCS = [sec0, sec1, sec2, sec3, sec4, sec5]


def render_content(A, t):
    ts = step_time(t)
    idx = next(i for i, (a, b) in enumerate(SECTIONS) if a <= ts < b or i == len(SECTIONS) - 1)
    stage = A["bg"].copy()
    cam = SEC_FUNCS[idx](stage, ImageDraw.Draw(stage), ts - SECTIONS[idx][0], A)
    return camera(stage, *cam) if cam else stage


def render_frame(A, fi, content=None):
    if content is None:
        content = render_content(A, fi / FPS)
    arr = np.asarray(content, np.int16) + A["grain"][fi % len(A["grain"])]  # 그레인은 30fps로 계속 움직인다
    return arr.clip(0, 255).astype(np.uint8)


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found")
    A = build_assets()
    only = sys.argv[1:]
    if only:
        dd = os.environ.get("PREVIEW_DIR", HERE)
        for ts in only:
            Image.fromarray(render_frame(A, int(round(float(ts) * FPS)))).save(os.path.join(dd, f"vox3_{ts}.png"))
        return
    n = int(DUR * FPS)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    last_key, content = None, None
    for fi in range(n):
        key = math.floor(fi / FPS * STEP_FPS + 1e-6)
        if key != last_key:
            content, last_key = render_content(A, fi / FPS), key
        proc.stdin.write(render_frame(A, fi, content).tobytes())
        if fi % 90 == 0:
            print(f"frame {fi}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
