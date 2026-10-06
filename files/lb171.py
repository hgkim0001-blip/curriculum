"""Retro Collage Opener 레시피 모음 (모션패턴_분석_Retro_Collage_Opener.md 6장).

제작 기준: 요소 Posterize 12fps / 배경 Posterize 4fps / 위글 wiggle(1,10)
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
EL_FPS, BG_FPS = 12, 4
WIGGLE_FREQ, WIGGLE_AMP = 1, 10


# ---------------- 시간 ----------------
def t_el(t):
    return math.floor(t * EL_FPS + 1e-6) / EL_FPS


def t_bg(t):
    return math.floor(t * BG_FPS + 1e-6) / BG_FPS


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def seg(u, a, b):
    return clamp((u - a) / (b - a))


def expo_out(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def _noise1d(x, seed):
    k = math.floor(x)
    f = x - k
    a = random.Random(seed * 7919 + k).uniform(-1, 1)
    b = random.Random(seed * 7919 + k + 1).uniform(-1, 1)
    return lerp(a, b, f * f * (3 - 2 * f))


def wiggle(t, seed):
    """After Effects wiggle(1,10)."""
    def ax(sd):
        return (_noise1d(t * WIGGLE_FREQ, sd) + 0.5 * _noise1d(t * WIGGLE_FREQ * 2, sd + 17)) / 1.5 * WIGGLE_AMP
    return ax(seed), ax(seed + 101)


# ---------------- R1 선버스트 ----------------
def sunburst(t, colors, n=16, rpm=4, cx=W / 2, cy=H / 2, swirl=0.0):
    img = Image.new("RGB", (W, H), colors[0])
    d = ImageDraw.Draw(img)
    rot = t * rpm * 2 * math.pi / 60
    R = math.hypot(W, H)
    for i in range(n):
        a0 = rot + 2 * math.pi * i / n
        a1 = a0 + math.pi / n
        pts = [(cx, cy)]
        for k in range(24):
            r = R * (k + 1) / 24
            pts.append((cx + r * math.cos(a0 + swirl * r / R), cy + r * math.sin(a0 + swirl * r / R)))
        for k in range(23, -1, -1):
            r = R * (k + 1) / 24
            pts.append((cx + r * math.cos(a1 + swirl * r / R), cy + r * math.sin(a1 + swirl * r / R)))
        d.polygon(pts, fill=colors[1 + i % (len(colors) - 1)])
    return img


def halftone(img, color, spacing=18, rmax=4.5, cx=W / 2, cy=H / 2, reach=0.55):
    """중심에서 멀수록 커지는 하프톤 망점(선버스트 위에 얹는 팝아트 점)."""
    d = ImageDraw.Draw(img)
    R = math.hypot(W, H) * reach
    for y in range(0, H, spacing):
        for x in range((y // spacing % 2) * spacing // 2, W, spacing):
            k = math.hypot(x - cx, y - cy) / R
            r = rmax * clamp(k - 0.35) * 1.6
            if r > 0.6:
                d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    return img


# ---------------- R3 스플랫 / R4 아이리스 ----------------
def splat(size, color, spikes=30, seed=0):
    rng = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    for i in range(spikes):
        a = 2 * math.pi * i / spikes + rng.uniform(-0.05, 0.05)
        L = c * rng.uniform(0.55, 0.98)
        d.line([(c, c), (c + L * math.cos(a), c + L * math.sin(a))], fill=color + (255,),
               width=max(2, int(size / 120 * rng.uniform(1.5, 3))))
    d.ellipse([c - c * 0.12, c - c * 0.12, c + c * 0.12, c + c * 0.12], fill=color + (255,))
    return im


def iris_mask(p, cx=W / 2, cy=H / 2):
    m = Image.new("L", (W, H), 0)
    R = math.hypot(W, H) / 2 * 1.08
    r = R * (clamp(p) ** 1.4)
    ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return m


# ---------------- R2 간판 ----------------
def sign_panel(text, fnt, fg=(200, 50, 50), bg=(250, 240, 228), outline=(50, 40, 60), skew=0.06, pad=38,
               shadow=(12, 14), border=7):
    l, t, r, b = fnt.getbbox(text)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    sx = int(w * skew)
    out = Image.new("RGBA", (w + sx * 2 + shadow[0] + 24, h + shadow[1] + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    poly = [(12 + sx, 12), (12 + w + sx * 2, 12 + h * 0.08), (12 + w + sx, 12 + h), (12, 12 + h * 0.92)]
    d.polygon([(x + shadow[0], y + shadow[1]) for x, y in poly], fill=outline + (255,))
    d.polygon(poly, fill=bg + (255,))
    d.line(poly + [poly[0]], fill=outline + (255,), width=border, joint="curve")
    d.text((12 + sx + pad - l, 12 + pad - t), text, font=fnt, fill=fg)
    return out


def pop_scale(p, overshoot=1.25):
    p = clamp(p)
    if p <= 0:
        return 0.0
    if p < 0.5:
        return overshoot * (p / 0.5) ** 0.7
    if p < 0.75:
        return lerp(overshoot, 0.95, (p - 0.5) / 0.25)
    return lerp(0.95, 1.0, (p - 0.75) / 0.25)


# ---------------- R9 압출 글자 ----------------
def extrude_text(text, fnt, face, side, depth=14, angle=(1, 1), outline=None):
    l, t, r, b = fnt.getbbox(text)
    im = Image.new("RGBA", (r - l + depth + 50, b - t + depth + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(depth, 0, -1):
        d.text((25 - l + k * angle[0], 25 - t + k * angle[1]), text, font=fnt, fill=side)
    if outline:
        d.text((25 - l, 25 - t), text, font=fnt, fill=face, stroke_width=3, stroke_fill=outline)
    else:
        d.text((25 - l, 25 - t), text, font=fnt, fill=face)
    return im


def write_on(spr, p, feather=40):
    if p >= 1:
        return spr
    w = spr.width
    edge = int((w + feather) * clamp(p))
    m = np.clip((edge - np.arange(w)) / feather, 0, 1).astype(np.float32)
    s = spr.copy()
    s.putalpha(Image.fromarray((np.asarray(spr.getchannel("A"), np.float32) * m[None, :]).astype(np.uint8)))
    return s


# ---------------- 장식 ----------------
def star_points(cx, cy, r_out, r_in, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def marquee_star(size, fill=(250, 240, 228), outline=(50, 40, 60), bulb=(200, 60, 50)):
    """극장 간판의 전구 박힌 별."""
    im = Image.new("RGBA", (size + 30, size + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (size + 30) / 2
    outer = star_points(c + 10, c + 12, size / 2, size / 4.6)
    d.polygon(outer, fill=outline + (255,))
    outer = star_points(c, c, size / 2, size / 4.6)
    d.polygon(outer, fill=fill + (255,))
    d.line(outer + [outer[0]], fill=outline + (255,), width=7, joint="curve")
    inner = star_points(c, c, size / 2 * 0.72, size / 4.6 * 0.72)
    for i in range(len(inner)):
        (x0, y0), (x1, y1) = inner[i], inner[(i + 1) % len(inner)]
        for k in range(3):
            x, y = lerp(x0, x1, k / 3), lerp(y0, y1, k / 3)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=bulb + (255,))
    return im


def star3d(size, face=(250, 206, 70), side=(214, 120, 40), outline=(50, 40, 60)):
    im = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (size + 40) / 2
    for k in range(12, 0, -2):
        d.polygon(star_points(c + k, c + k, size / 2, size / 4.2), fill=side + (255,))
    pts = star_points(c, c, size / 2, size / 4.2)
    d.polygon(pts, fill=face + (255,))
    d.line(pts + [pts[0]], fill=outline + (255,), width=5, joint="curve")
    return im


def sparkle(size, color=(50, 40, 90)):
    """4포인트 반짝이 별."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    pts = []
    for i in range(8):
        r = c if i % 2 == 0 else c * 0.16
        a = math.pi / 4 * i - math.pi / 2
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=color + (255,))
    return im


def paste_c(st, spr, cx, cy, scale=1.0, angle=0.0):
    if spr is None or scale <= 0.02:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if abs(angle) > 0.05:
        spr = spr.rotate(angle, expand=True, resample=Image.BICUBIC)
    st.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


# ---------------- R11 필름 룩 ----------------
class FilmLook:
    def __init__(self, seed=0):
        yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
        self.xx, self.yy = xx * 1, yy * 1
        v = 1 - 0.38 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        self.vig = np.asarray(Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                              np.float32)[..., None] / 255
        gate = Image.new("L", (W, H), 0)
        ImageDraw.Draw(gate).rounded_rectangle([20, 16, W - 20, H - 16], radius=52, fill=255)
        self.gate = np.asarray(gate.filter(ImageFilter.GaussianBlur(7)), np.float32)[..., None] / 255
        rng = random.Random(seed)
        self.ph = [rng.uniform(0, 6.28) for _ in range(3)]
        rs = np.random.default_rng(seed)
        self.dust = [rs.random((H, W)) < 0.00025 for _ in range(4)]

    def apply(self, img, t, strength=0.26):
        a = np.asarray(img.convert("RGB"), np.float32)
        leak = np.zeros((self.xx.shape[0], self.xx.shape[1], 3), np.float32)
        for i, col in enumerate([(255, 70, 170), (90, 255, 140), (130, 90, 255)]):
            cx = W * (0.5 + 0.6 * math.sin(t * 0.33 + self.ph[i] + i * 2.1))
            cy = H * (0.5 + 0.5 * math.cos(t * 0.26 + self.ph[i] * 1.3))
            s = W * 0.33
            g = np.exp(-(((self.xx - cx) ** 2 + (self.yy - cy) ** 2) / (2 * s * s)))
            leak += g[..., None] * np.array(col, np.float32)
        leak = np.asarray(Image.fromarray(np.clip(leak * strength, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                          np.float32)
        a = 255 - (255 - a) * (255 - leak) / 255
        a *= 1 + 0.035 * random.Random(int(t * EL_FPS)).uniform(-1, 1)
        a *= self.vig
        dust = self.dust[int(t * EL_FPS) % 4]
        a[dust] = a[dust] * 0.25 + 30
        a = a * self.gate + np.array([16, 10, 22], np.float32) * (1 - self.gate)
        return Image.fromarray(a.clip(0, 255).astype(np.uint8))
