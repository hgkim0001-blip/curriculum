"""세 번째 모션패턴(Retro Collage Opener) 테스트 — 약 11.5초.

S1 타이틀(잉크 스플랫 → 선버스트 → 간판 팝 → 마키 별)
  → 구겨진 종이 전환(실제 그린/블루 소스, crumple_transition.py)
S2 1950s 황금기(핑크 선버스트 + 해 원 + 차량 솟기 + 간판 + 3D 필기체 + 3D 별)
  → 원형 아이리스(잉크 스플랫)
S3 2020s(파랑 선버스트 + 해 원 + 전기차 + 3D 글자)
제작 기준: 요소 12fps / 배경 4fps / wiggle(1,10) / 필름 룩 오버레이
출력: test_retro_opener.mp4
"""
import math
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import crumple_transition as CT
import retro_kit as R
from retro_kit import W, H, t_el, t_bg, seg, expo_out, lerp, clamp, paste_c, wiggle

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "assets", "fonts")
OUT = os.path.join(HERE, "test_retro_opener.mp4")
FPS, DUR = 30, 11.5

CREAM = (247, 238, 222)
MUSTARD = (232, 170, 60)
CORAL = (240, 140, 110)
RED = (200, 48, 52)
HOTPINK = (232, 72, 122)
PINK = (246, 166, 186)
PURPLE = (112, 62, 172)
BLUE = (70, 102, 212)
LBLUE = (124, 162, 236)
SUN = (246, 200, 62)
NAVY = (50, 40, 70)

F_HAN = os.path.join(FONTS, "BlackHanSans-Regular.ttf")
F_DO = os.path.join(FONTS, "DoHyeon-Regular.ttf")
F_LOB = os.path.join(FONTS, "Lobster-Regular.ttf")


def F(p, s):
    return ImageFont.truetype(p, s)


SCENES = [(0.0, 4.0), (4.0, 8.6), (8.6, DUR)]
CRUMPLE = (1, 1.1)      # S2 시작에서 1.1초 동안 구겨진 종이 전환
IRIS = (2, 0.45)        # S3 시작에서 0.45초 아이리스


def sticker(img, border=10, color=(252, 248, 240), shadow=NAVY):
    """컷아웃에 흰 스티커 테두리 + 딱딱한 오프셋 그림자."""
    a = img.getchannel("A")
    pad = border + 18
    big = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    am = Image.new("L", big.size, 0)
    am.paste(a, (pad, pad))
    edge = am.filter(ImageFilter.MaxFilter(border * 2 + 1)).point(lambda v: 255 if v > 60 else 0)
    sh = Image.new("RGBA", big.size, shadow + (255,))
    big.paste(sh, (10, 12), edge)
    wh = Image.new("RGBA", big.size, color + (255,))
    big.paste(wh, (0, 0), edge)
    big.alpha_composite(img, (pad, pad))
    return big


def load_car(name, width, sat=0.9):
    im = Image.open(os.path.join(HERE, "cutouts", name)).convert("RGBA")
    rgb = ImageEnhance.Contrast(ImageEnhance.Color(im.convert("RGB")).enhance(sat)).enhance(1.08)
    out = rgb.convert("RGBA")
    out.putalpha(im.getchannel("A"))
    s = width / out.width
    return sticker(out.resize((int(out.width * s), int(out.height * s)), Image.LANCZOS))


def paper_field():
    p = os.path.join(HERE, "assets", "paper", "crumple.jpg")
    im = ImageOps.fit(Image.open(p).convert("L"), (W, H))
    a = np.asarray(im, np.float32)
    return (a / a.mean())[..., None]


def build():
    A = {"paper": paper_field()}
    A["splat_navy"] = R.splat(420, NAVY, seed=1)
    A["splat_pink"] = R.splat(420, (150, 40, 90), seed=2)
    A["mstar"] = R.marquee_star(560)
    A["s1"] = [
        R.sign_panel("바퀴 위의", F(F_DO, 86), fg=RED),
        R.sign_panel("140년", F(F_HAN, 230), fg=RED, pad=30),
        R.sign_panel("자동차의 변천사", F(F_DO, 80), fg=(196, 110, 30)),
        R.sign_panel("1886 - 2026", F(F_HAN, 64), fg=NAVY, bg=(250, 214, 110)),
    ]
    A["sparkle"] = R.sparkle(90, NAVY)
    A["sparkle_w"] = R.sparkle(90, (252, 248, 240))
    A["car50"] = load_car("car_1950s.png", 1250)
    A["car20"] = load_car("car_2020s.png", 1120, 0.95)
    A["s2_sign"] = R.sign_panel("자동차의 황금기", F(F_HAN, 110), fg=RED)
    A["s2_script"] = R.extrude_text("1950s", F(F_LOB, 240), (250, 222, 72), (190, 40, 64), depth=16, outline=NAVY)
    A["s2_sub"] = R.sign_panel("고속도로, 교외, 테일핀", F(F_DO, 58), fg=NAVY, bg=(250, 214, 110), pad=26)
    A["star3d"] = R.star3d(170)
    A["star3d_s"] = R.star3d(110)
    A["s3_sign"] = R.sign_panel("전기차 + 자율주행", F(F_HAN, 96), fg=BLUE)
    A["s3_script"] = R.extrude_text("다음 140년은?", F(F_HAN, 150), (252, 246, 236), PURPLE, depth=14, outline=NAVY)
    A["crumple"] = CT.load_crumple(scale=1.8)
    A["film"] = R.FilmLook(3)
    A["bg_cache"] = {}
    return A


# ---------------- 배경 (4fps) ----------------
def background(A, i, ub):
    key = (i, round(ub, 3))
    if key in A["bg_cache"]:
        return A["bg_cache"][key].copy()
    if i == 0:
        img = R.sunburst(ub, [CREAM, MUSTARD, CORAL, CREAM], n=18, rpm=7)
        R.halftone(img, (214, 120, 60), spacing=20, rmax=5)
    elif i == 1:
        img = R.sunburst(ub, [PINK, HOTPINK, PINK], n=20, rpm=-7, cx=1150, cy=520)
        R.halftone(img, (190, 50, 100), spacing=20, rmax=5, cx=1150, cy=520)
    else:
        img = R.sunburst(ub, [LBLUE, BLUE, LBLUE], n=20, rpm=7, cx=960, cy=560, swirl=0.6)
        R.halftone(img, (60, 70, 170), spacing=20, rmax=5, cx=960, cy=560)
    a = np.asarray(img, np.float32) * (0.9 + 0.1 * A["paper"])      # 종이 결
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    if len(A["bg_cache"]) > 64:
        A["bg_cache"].clear()
    A["bg_cache"][key] = out
    return out.copy()


def twinkles(st, A, ue, spots, spr_key="sparkle", seed=0):
    for k, (x, y, s) in enumerate(spots):
        ph = (ue * 1.5 + k * 0.37 + seed * 0.13) % 1.0
        sc = math.sin(math.pi * ph) * s
        if sc > 0.08:
            wx, wy = wiggle(ue, 300 + k + seed * 20)
            paste_c(st, A[spr_key], x + wx, y + wy, sc)


def pop(st, spr, cx, cy, ue, start, angle=0.0, dur=0.3, wig=None):
    if ue < start:
        return
    s = R.pop_scale(seg(ue, start, start + dur))
    wx, wy = wiggle(ue, wig) if wig is not None else (0, 0)
    paste_c(st, spr, cx + wx, cy + wy, s, angle)


def rise(st, spr, cx, cy, ue, start, dur=0.45):
    if ue < start:
        return
    k = expo_out(seg(ue, start, start + dur))
    paste_c(st, spr, cx, cy + (1 - k) * 800, 1.0, -7 * (1 - k))


def scene0(A, ue, ub):
    bg = background(A, 0, ub)
    st = Image.new("RGBA", (W, H), CREAM + (255,))
    st = Image.fromarray((np.asarray(st, np.float32)[..., :3] * (0.9 + 0.1 * A["paper"])).clip(0, 255)
                         .astype(np.uint8)).convert("RGBA")
    # 선버스트가 가운데서 원형으로 퍼지며 드러난다 (요소 12fps)
    p = expo_out(seg(ue, 0.12, 0.55))
    if p > 0:
        st.paste(bg, (0, 0), R.iris_mask(p, 960, 540))
    if ue < 0.4:  # 잉크 스플랫
        paste_c(st, A["splat_navy"], 960, 540, 0.25 + 0.9 * expo_out(seg(ue, 0.0, 0.2)))
    pop(st, A["mstar"], 1440, 400, ue, 0.35, angle=8, dur=0.35, wig=1)
    pos = [(760, 250, -4, 0.45), (820, 480, 2, 0.55), (720, 710, -3, 0.7), (1210, 780, 4, 0.82)]
    for spr, (x, y, a, t0) in zip(A["s1"], pos):
        pop(st, spr, x, y, ue, t0, angle=a)
    if ue > 1.0:
        twinkles(st, A, ue, [(260, 200, 0.9), (1700, 180, 1.0), (1760, 760, 0.8), (230, 820, 1.0),
                             (1380, 900, 0.7), (520, 120, 0.6)])
    return st


def scene1(A, ue, ub):
    st = background(A, 1, ub)
    d = ImageDraw.Draw(st)
    k = expo_out(seg(ue, 0.75, 1.05))
    if k > 0:  # 해 원
        r = 400 * k
        d.ellipse([1150 - r + 14, 520 - r + 16, 1150 + r + 14, 520 + r + 16], fill=(170, 40, 90))
        d.ellipse([1150 - r, 520 - r, 1150 + r, 520 + r], fill=SUN)
    rise(st, A["car50"], 1230, 760, ue, 0.95)
    pop(st, A["s2_sign"], 1180, 170, ue, 1.45, angle=-3)
    if ue >= 1.7:
        wx, wy = wiggle(ue, 7)
        paste_c(st, R.write_on(A["s2_script"], seg(ue, 1.7, 2.3)), 430 + wx * 0.3, 470 + wy * 0.3, 1.0, 8)
    pop(st, A["s2_sub"], 360, 660, ue, 2.35, angle=3)
    pop(st, A["star3d"], 1760, 400, ue, 2.0, angle=12, wig=2)
    pop(st, A["star3d_s"], 170, 170, ue, 2.15, angle=-10, wig=3)
    if ue > 2.2:
        twinkles(st, A, ue, [(1820, 900, 0.8), (700, 110, 0.7), (100, 560, 0.9), (1560, 90, 0.7)], "sparkle_w", 1)
    return st


def scene2(A, ue, ub):
    st = background(A, 2, ub)
    d = ImageDraw.Draw(st)
    k = expo_out(seg(ue, 0.4, 0.7))
    if k > 0:
        r = 420 * k
        d.ellipse([960 - r + 14, 560 - r + 16, 960 + r + 14, 560 + r + 16], fill=NAVY)
        d.ellipse([960 - r, 560 - r, 960 + r, 560 + r], fill=SUN)
    rise(st, A["car20"], 960, 790, ue, 0.55)
    pop(st, A["s3_sign"], 960, 930, ue, 0.95, angle=-2)
    if ue >= 1.3:
        wx, wy = wiggle(ue, 9)
        paste_c(st, R.write_on(A["s3_script"], seg(ue, 1.3, 2.0)), 960 + wx * 0.3, 190 + wy * 0.3, 1.0, -3)
    pop(st, A["star3d"], 1680, 380, ue, 1.1, angle=-12, wig=4)
    pop(st, A["star3d_s"], 250, 420, ue, 1.2, angle=10, wig=5)
    if ue > 1.2:
        twinkles(st, A, ue, [(160, 160, 0.8), (1760, 160, 0.9), (1780, 820, 0.7), (180, 860, 0.9)], "sparkle_w", 2)
    return st


SCENE = [scene0, scene1, scene2]


def render_scene(A, i, te, tb):
    a = SCENES[i][0]
    return SCENE[i](A, max(0.0, te - a), max(0.0, tb - a)).convert("RGB")


def render(A, t):
    te, tb = t_el(t), t_bg(t)
    i = next(k for k, (a, b) in enumerate(SCENES) if a <= te < b or k == len(SCENES) - 1)
    u = te - SCENES[i][0]
    cur = render_scene(A, i, te, tb)
    if i == CRUMPLE[0] and u < CRUMPLE[1]:            # R5: 실제 구겨진 종이 소스
        prev = render_scene(A, i - 1, te, tb)          # 이전 장면도 계속 살아 있다
        src = CT.frame_at(A["crumple"], u)
        out = Image.fromarray(CT.composite(src, np.asarray(prev), np.asarray(cur)))
    elif i == IRIS[0] and u < IRIS[1]:                 # R4: 아이리스 + 잉크 스플랫
        prev = render_scene(A, i - 1, te, tb)
        p = u / IRIS[1]
        out = prev.copy()
        out.paste(cur, (0, 0), R.iris_mask(p, 960, 560))
        o = out.convert("RGBA")
        paste_c(o, A["splat_pink"], 960, 560, 0.3 + 1.2 * expo_out(p))
        out = o.convert("RGB")
    else:
        out = cur
    return A["film"].apply(out, te)


def main():
    A = build()
    grain = [np.random.default_rng(k).normal(0, 4, (H, W, 1)).astype(np.int16) for k in range(5)]
    only = sys.argv[1:]
    if only:
        dd = os.environ.get("PREVIEW_DIR", HERE)
        for ts in only:
            render(A, float(ts)).save(os.path.join(dd, f"retro_{ts}.png"))
        return
    ffmpeg = shutil.which("ffmpeg")
    n = int(DUR * FPS)
    p = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
                          "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    last, frame = None, None
    for fi in range(n):
        t = fi / FPS
        key = (t_el(t), t_bg(t))
        if key != last:
            frame, last = np.asarray(render(A, t), np.int16), key
        p.stdin.write((frame + grain[fi % 5]).clip(0, 255).astype(np.uint8).tobytes())
        if fi % 60 == 0:
            print(f"frame {fi}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
