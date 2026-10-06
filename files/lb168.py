"""Retro Paper Collage v2: 자동차의 변천사 (30s, 1920x1080, 30fps).

test_1886_v2(make_scene_1886_v2.py)에서 확정한 방식을 전체 영상에 적용한다.
- 재료: Flow로 만든 실제 종이 스캔(assets/paper) — 배경 보일, 모든 색면·글자에 종이 결 인쇄
- 차량 리빌: 누끼 차량을 알파 매트(눈 끈 복제 레이어)로 써서 찢어진 흰 종이 띠를 차량 실루엣 안에만 보이게,
             띠 아래쪽 차량만 보이다가 띠가 올라가며 드러난다 (After Effects Track Matte 구성과 동일)
- 찢긴 가장자리: 실제 찢어진 종이 띠 스캔 + 여러 단계 노이즈로 만든 불규칙한 가장자리와 흰 섬유층
- 폰트: Black Han Sans(도장), 나눔 붓글씨(필기체), Yeon Sung(라벨)
- 모든 위글: wiggle(1,10) / 최종본: Posterize Time 4 (초당 4번 그림 갱신, 필름 그레인만 30fps)
출력: car_history_paper_collage_v2.mp4
"""
import math
import os
import random
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

import make_scene_1886_v2 as K   # 재료·요소 함수 재사용
from make_scene_1886_v2 import (W, H, FPS, STEP_FPS, BOIL_FPS, TEAL, ORANGE, MUSTARD, BRICK, BLUE, OLIVE, INK, WHITE,
                                F_STAMP, F_SCRIPT, F_LABEL, clamp, lerp, seg, expo_out, back_out, ease_in_out,
                                step_time, jit, load_paper, texture_field, print_on, riso_map, extract_strips,
                                text_img, rot, blob, brush_stroke, doodle_line, draw_doodle, giant_news, put,
                                with_shadow)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "car_history_paper_collage_v2.mp4")

# ---- 사용자 기본값: 모든 위글 = wiggle(1,10), 최종본 = Posterize Time 4 ----
POSTERIZE_FPS = 4
WIGGLE_FREQ, WIGGLE_AMP = 1, 10


def step_time(t):
    return math.floor(t * POSTERIZE_FPS + 1e-6) / POSTERIZE_FPS


def _noise1d(x, seed):
    k = math.floor(x)
    f = x - k
    a = random.Random(seed * 7919 + k).uniform(-1, 1)
    b = random.Random(seed * 7919 + k + 1).uniform(-1, 1)
    return lerp(a, b, f * f * (3 - 2 * f))


def jit(t, seed, amp=None):
    """After Effects wiggle(1,10)과 같은 방식: 초당 1회, 최대 ±10px, 부드러운 2옥타브 노이즈."""
    def axis(sd):
        return (_noise1d(t * WIGGLE_FREQ, sd) + 0.5 * _noise1d(t * WIGGLE_FREQ * 2, sd + 17)) / 1.5 * WIGGLE_AMP
    return axis(seed), axis(seed + 101)
DUR = 30.0
PINK = (222, 128, 122)

SECTIONS = [(0.0, 4.2), (4.2, 8.8), (8.8, 13.2), (13.2, 18.0), (18.0, 22.6), (22.6, 26.8), (26.8, 30.0)]
TRANS = {1: ("push_x", 0.5), 2: ("push_y", 0.5), 3: ("hole", 1.0), 4: ("tear", 0.45), 5: ("tear", 0.45),
         6: ("tear", 0.45)}


# ---------------- 불규칙한 찢긴 가장자리 ----------------
def _vnoise(n, freq, rng):
    """1차원 값 노이즈(부드럽게 보간)."""
    k = max(2, int(n * freq) + 2)
    pts = [rng.uniform(-1, 1) for _ in range(k)]
    out = []
    for i in range(n):
        x = i * freq
        j = int(x)
        f = x - j
        f = f * f * (3 - 2 * f)
        out.append(pts[j] * (1 - f) + pts[j + 1] * f)
    return out


def rough_polygon(pts, seed, amp=14, step=5):
    """다각형 둘레를 여러 옥타브 노이즈로 불규칙하게(찢긴 종이 가장자리)."""
    rng = random.Random(seed)
    res = []
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(L / step))
        nx, ny = -(y1 - y0) / (L + 1e-6), (x1 - x0) / (L + 1e-6)
        o1, o2, o3 = _vnoise(n, 1 / 16, rng), _vnoise(n, 1 / 5, rng), _vnoise(n, 1 / 1.6, rng)
        for k in range(n):
            s = k / n
            off = amp * (0.6 * o1[k] + 0.3 * o2[k] + 0.12 * o3[k])
            res.append((lerp(x0, x1, s) + nx * off, lerp(y0, y1, s) + ny * off))
    return res


def torn_piece(poly, color, seed, fld, riso, fiber=7, size=(W, H), shadow=True):
    """실제처럼 찢긴 색종이 조각: 불규칙한 가장자리 + 가는 흰 섬유층 + 종이 결 인쇄 + 그림자."""
    w, h = size
    body = Image.new("L", size, 0)
    ImageDraw.Draw(body).polygon(rough_polygon(poly, seed), fill=255)
    fib = body.filter(ImageFilter.MaxFilter(fiber * 2 + 1))
    noise = np.asarray(Image.fromarray((np.random.default_rng(seed).random((h // 6 + 1, w // 6 + 1)) * 255)
                                       .astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    fa = np.asarray(fib, np.float32) * np.clip((noise - 0.15) * 3, 0, 1)
    fa = np.maximum(fa, np.asarray(body, np.float32))
    out = Image.new("RGBA", size, WHITE + (0,))
    out.putalpha(Image.fromarray(fa.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)))
    col = Image.new("RGBA", size, color + (255,))
    col.putalpha(body.filter(ImageFilter.GaussianBlur(0.6)))
    out.alpha_composite(col)
    out = print_on(out, fld, 1.0, riso, 0.10, seed * 37 % 400, seed * 53 % 300)
    if shadow:
        sh = Image.new("RGBA", size, (50, 34, 22, 0))
        sh.putalpha(Image.fromarray((fa * 0.35).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8)))
        base = Image.new("RGBA", size, (0, 0, 0, 0))
        base.paste(sh, (6, 9), sh)
        base.alpha_composite(out)
        out = base
    return out


# ---------------- 차량 / 사진 + 알파 매트 리빌 ----------------
def prep_subject(img, width, sat, fld, strip, ox=0, oy=0):
    """피사체(RGBA) → 세피아/약한 컬러 + 종이 결 + 그림자, 그리고 그림자 없는 알파 매트와 리빌 띠."""
    rgb = img.convert("RGB")
    g = ImageEnhance.Contrast(ImageOps.grayscale(rgb)).enhance(1.15)
    sep = ImageOps.colorize(g, black=(40, 28, 20), white=(240, 222, 190))
    if sat > 0:
        sep = Image.blend(sep, ImageEnhance.Color(rgb).enhance(0.85), sat)
    sep = sep.convert("RGBA")
    sep.putalpha(img.getchannel("A"))
    s = width / sep.width
    sep = sep.resize((int(sep.width * s), int(sep.height * s)), Image.LANCZOS)
    raw = print_on(sep, fld, 0.35, ox=ox, oy=oy)
    car = with_shadow(raw, (12, 16), 14, 95)
    pad = 14 * 2 + 16
    matte = Image.new("L", car.size, 0)
    matte.paste(raw.getchannel("A"), (pad, pad))
    return dict(car=car, matte=np.asarray(matte, np.float32) / 255,
                strip=strip.resize((car.width, 118), Image.LANCZOS))


def matte_reveal(st, S, cx, cy, u, start, seed):
    """P2: 아래에서 올라오고, 흰 띠(차량 알파 매트 안에서만 보임)가 2스텝 늦게 벗겨지며 드러난다."""
    if u < start:
        return
    car = S["car"]
    k = expo_out(seg(u, start, start + 0.5))
    y_c = cy + (1 - k) * 700
    r = ease_in_out(seg(u, start + 0.17, start + 0.95))
    strip_y = lerp(car.height * 0.55, -120, r)
    cut = max(0, int(strip_y))
    jx, jy = jit(u, seed)
    x0, y0 = int(cx - car.width / 2 + jx), int(y_c - car.height / 2 + jy)
    layer = Image.new("RGBA", car.size, (0, 0, 0, 0))
    if cut < car.height:
        layer.paste(car.crop((0, cut, car.width, car.height)), (0, cut))
    if r < 1:
        s = S["strip"]
        sl = Image.new("RGBA", car.size, (0, 0, 0, 0))
        sl.paste(s, (0, int(strip_y - s.height * 0.55)))
        a = np.asarray(sl.getchannel("A"), np.float32) * S["matte"]
        sl.putalpha(Image.fromarray(a.astype(np.uint8)))
        layer.alpha_composite(sl)
    st.paste(layer, (x0, y0), layer)


# ---------------- 글자 동작 ----------------
def stamp(st, spr, cx, cy, u, start, seed):
    """P5: 흐리고 110%에서 선명하고 100%로."""
    if u < start:
        return
    p = seg(u, start, start + 0.2)
    jx, jy = jit(u, seed)
    put(st, spr, cx + jx, cy + jy, 1.1 - 0.1 * p, 6 * (1 - p))


def write(st, spr, cx, cy, u, start, dur, seed):
    """P6: 필기체를 왼쪽부터 써 내려감."""
    if u < start:
        return
    p = seg(u, start, start + dur)
    w = spr.width
    edge = int((w + 30) * p)
    m = np.clip((edge - np.arange(w)) / 30, 0, 1).astype(np.float32)
    s2 = spr.copy()
    s2.putalpha(Image.fromarray((np.asarray(spr.getchannel("A"), np.float32) * m[None, :]).astype(np.uint8)))
    jx, jy = jit(u, seed)
    put(st, s2, cx + jx, cy + jy)


def label(st, L, cx, cy, u, start, seed):
    """P4: 찢어진 종이 라벨이 튀어나오고, 2~3스텝 뒤 글자가 찍힌다."""
    if u < start:
        return
    bg, tx = L
    jx, jy = jit(u, seed)
    put(st, bg, cx + jx, cy + jy, back_out(seg(u, start, start + 0.2)))
    p = seg(u, start + 0.22, start + 0.4)
    if p > 0:
        put(st, tx, cx + jx, cy - 4 + jy, 1.1 - 0.1 * p, 5 * (1 - p))


def brush_in(st, b, cx, cy, u, start, seed):
    """P7: 붓 자국을 왼쪽부터 칠한다."""
    if u < start:
        return
    w = max(1, int(b.width * seg(u, start, start + 0.2)))
    bb = Image.new("RGBA", b.size, (0, 0, 0, 0))
    bb.paste(b.crop((0, 0, w, b.height)), (0, 0))
    jx, jy = jit(u, seed)
    put(st, bb, cx + jx, cy + jy)


def blob_rise(st, bl, cx, cy, u, start, seed):
    """P1: 아래 밖에서 솟아오르며 80→100%."""
    if u < start:
        return
    k = expo_out(seg(u, start, start + 0.4))
    jx, jy = jit(u, seed)
    put(st, bl, cx + jx, cy + (1 - k) * 800 + jy, 0.8 + 0.2 * k)


def cut_in(st, spr, cx, cy, u, start, seed):
    """P8: 대형 배경 글자 컷인."""
    if u >= start:
        jx, jy = jit(u, seed)
        put(st, spr, cx + jx, cy + jy)


# ---------------- 조립 ----------------
def build():
    A = {}
    k1 = load_paper("kraft1.jpg")
    crumple_f = texture_field(load_paper("crumple.jpg"))
    tint = np.asarray(k1, np.float32).mean((0, 1)) * 0.98
    A["bg"] = [k1, load_paper("kraft2.jpg"),
               Image.fromarray((crumple_f[..., None] * tint).clip(0, 255).astype(np.uint8))]
    A["crumple_field"] = crumple_f
    fld = A["field"] = texture_field(load_paper("kraft1.jpg", (2400, 1400)))
    riso = A["riso"] = riso_map(load_paper("riso.jpg", (2400, 1400)))
    news = load_paper("news.jpg", (2400, 1400))
    strips = extract_strips(Image.open(os.path.join(K.PAPER, "strips.jpg")))
    strips = strips or [Image.new("RGBA", (1600, 120), WHITE + (255,))]

    def P(spr, s=1.0, knock=0.3, seed=0):
        return print_on(spr, fld, s, riso, knock, seed * 97 % 900, seed * 61 % 500)

    def T(text, size, color, angle, seed, fnt=F_STAMP, knock=0.35):
        return rot(P(text_img(text, fnt, size, color), 1.0, knock, seed), angle)

    def LBL(text, size, color, angle, seed, width=None):
        tx = text_img(text, F_LABEL, size, color)
        wdt = width or tx.width + 70
        piece = ImageOps.fit(strips[(seed % (len(strips) - 1)) + 1 if len(strips) > 1 else 0], (wdt, int(size * 1.45)))
        return rot(with_shadow(piece, (4, 6), 5, 70), angle), rot(P(tx, 0.6, 0.25, seed), angle)

    cut = os.path.join(HERE, "cutouts")
    A["c1886"] = prep_subject(Image.open(os.path.join(cut, "car_1886.png")).convert("RGBA"), 1340, 0.0, fld, strips[0], 500, 100)
    A["c1908"] = prep_subject(Image.open(os.path.join(cut, "car_1908.png")).convert("RGBA"), 860, 0.0, fld, strips[0], 300, 200)
    A["c1950"] = prep_subject(Image.open(os.path.join(cut, "car_1950s.png")).convert("RGBA"), 1320, 0.45, fld, strips[0], 100, 300)
    A["c1973"] = prep_subject(Image.open(os.path.join(cut, "car_1973.png")).convert("RGBA"), 980, 0.45, fld, strips[0], 700, 50)
    A["c2020"] = prep_subject(Image.open(os.path.join(cut, "car_2020s.png")).convert("RGBA"), 1100, 0.6, fld, strips[0], 200, 400)
    # 타이틀 도로 사진: 찢긴 가장자리 사진 조각
    road = Image.open(os.path.join(HERE, "images", "s0_title.jpg")).convert("RGB")
    rw, rh = road.size
    road = ImageOps.fit(road.crop((0, 0, int(rw * 0.9), int(rh * 0.9))), (1000, 580)).convert("RGBA")
    m = Image.new("L", road.size, 0)
    ImageDraw.Draw(m).polygon(rough_polygon([(14, 14), (986, 14), (986, 566), (14, 566)], 5, amp=8), fill=255)
    road.putalpha(m)
    A["road"] = prep_subject(road, 1000, 0.0, fld, strips[0], 50, 50)

    # 블롭
    def BL(size, color, seed):
        return with_shadow(P(blob(size, color, seed), 1.0, 0.12, seed), (6, 10), 10, 60)
    A["blob_o"] = BL((1150, 980), ORANGE, 1)
    A["blob_t"] = BL((1180, 1000), TEAL, 7)
    A["blob_m"] = BL((1200, 900), MUSTARD, 3)
    A["blob_g"] = BL((1250, 950), OLIVE, 4)
    # 대형 배경 글자(신문)
    A["g_140"] = giant_news("140", 560, news, 1)
    A["g_1886"] = giant_news("1886", 560, news, 3)
    A["g_ev"] = giant_news("EV", 700, news, 5)
    # 낙서 선
    A["d_tr"] = doodle_line((W, H), [(1960, 170), (1760, 70), (1560, 210), (1380, 100), (1230, 190)], ORANGE)
    A["d_bl"] = doodle_line((W, H), [(-30, 980), (160, 880), (330, 1010), (520, 900)], TEAL)
    A["d_tl"] = doodle_line((W, H), [(-30, 140), (170, 60), (320, 170), (500, 80)], TEAL)
    A["d_br"] = doodle_line((W, H), [(1960, 900), (1760, 1010), (1600, 880), (1420, 1010)], ORANGE)

    # S0 타이틀
    A["s0_script"] = rot(P(text_img("바퀴 위의", F_SCRIPT, 190, BRICK), 0.8, 0.15, 1), -5)
    A["s0_stamp"] = T("140년", 280, BLUE, -3, 2)
    A["s0_label"] = LBL("자동차의 변천사", 70, INK, -4, 3)
    # S1 1886
    A["s1_label"] = LBL("1886년", 74, BRICK, -5, 4)
    A["s1_first"] = T("최초의", 170, OLIVE, -4, 5)
    A["s1_car"] = T("자동차", 250, BLUE, -3, 6)
    A["s1_script1"] = rot(P(text_img("카를 벤츠의", F_SCRIPT, 130, BRICK), 0.8, 0.15, 7), -5)
    A["s1_script2"] = rot(P(text_img("모터바겐", F_SCRIPT, 130, BRICK), 0.8, 0.15, 8), -5)
    A["s1_brush"] = rot(P(brush_stroke(560, 120, MUSTARD, 3), 1.0, 0.3, 9), -3)
    A["s1_speed"] = T("최고 시속 16km", 76, BRICK, -3, 10, knock=0.3)
    # S2 1908: 겹겹이 쌓인 산 모양 색종이 띠
    A["bands"] = []
    for i, c in enumerate([BRICK, MUSTARD, PINK, OLIVE]):
        apex = (820 + i * 20, 70 + i * 185)
        A["bands"].append(torn_piece([(-600 + i * 130, H + 160), apex, (2250 - i * 170, H + 160)], c, 80 + i, fld, riso))
    A["s2_lines"] = [with_shadow(T(s, sz, c, -3, 20 + i), (4, 6), 4, 80) for i, (s, sz, c) in enumerate(
        [("1908", 150, WHITE), ("포드 모델 T", 132, BLUE), ("모두의 자동차", 140, WHITE), ("1,500만 대 판매", 110, MUSTARD)])]
    # S3 1950s: 찢어 나눈 색종이 배경
    A["split"] = [
        torn_piece([(-80, -80), (1180, -80), (640, H + 80), (-80, H + 80)], MUSTARD, 60, fld, riso),
        torn_piece([(1180, -80), (W + 80, -80), (W + 80, 520), (920, 560)], PINK, 61, fld, riso),
        torn_piece([(920, 560), (W + 80, 520), (W + 80, H + 80), (640, H + 80)], TEAL, 62, fld, riso),
    ]
    A["s3_label"] = LBL("1950s", 74, BRICK, -4, 30)
    A["s3_stamp"] = T("자동차의 황금기", 150, BRICK, -3, 31)
    A["s3_script"] = rot(P(text_img("고속도로, 교외, 테일핀", F_SCRIPT, 120, INK), 0.8, 0.15, 32), -4)
    # S4 1973
    A["s4_rep"] = T("오일쇼크", 150, BRICK, 0, 40, knock=0.25)
    bar = Image.new("RGBA", (1060, 160), (0, 0, 0, 0))
    ImageDraw.Draw(bar).polygon(rough_polygon([(0, 0), (1060, 0), (1060, 160), (0, 160)], 41, amp=6), fill=BRICK + (255,))
    A["s4_bar"] = with_shadow(P(bar, 1.0, 0.2, 41), (6, 8), 6, 70)
    A["s4_bartext"] = T("1973 OIL SHOCK", 104, WHITE, 0, 42, knock=0.2)
    A["s4_script"] = rot(P(text_img("작고 연비 좋은 차로", F_SCRIPT, 130, INK), 0.8, 0.15, 43), -4)
    # S5 2020s
    A["s5_label"] = LBL("2020s", 74, BRICK, -4, 50)
    A["s5_ev"] = T("전기차", 210, BLUE, -4, 51)
    A["s5_auto"] = T("자율주행", 160, BRICK, -3, 52)
    A["s5_brush"] = rot(P(brush_stroke(620, 120, MUSTARD, 53), 1.0, 0.3, 53), -3)
    A["s5_script1"] = rot(P(text_img("엔진 대신 배터리,", F_SCRIPT, 112, INK), 0.8, 0.15, 54), -4)
    A["s5_script2"] = rot(P(text_img("운전자 대신 AI", F_SCRIPT, 112, BRICK), 0.8, 0.15, 55), -4)
    # S6 엔딩: 모서리 색종이
    A["corners"] = [
        (torn_piece([(-120, H + 120), (-120, 600), (560, H + 120)], BRICK, 70, fld, riso), (0, 1)),
        (torn_piece([(-120, 620), (-120, -120), (300, -120)], BLUE, 71, fld, riso), (-1, 0)),
        (torn_piece([(280, -120), (1520, -120), (900, 150)], OLIVE, 72, fld, riso), (0, -1)),
        (torn_piece([(1500, -120), (W + 120, -120), (W + 120, 900), (1720, 700)], MUSTARD, 73, fld, riso), (1, 0)),
        (torn_piece([(W + 120, 880), (W + 120, H + 120), (1240, H + 120)], ORANGE, 74, fld, riso), (1, 1)),
    ]
    A["s6_script"] = rot(P(text_img("다음 140년은?", F_SCRIPT, 280, BLUE), 0.8, 0.15, 60), -4)
    A["s6_small"] = rot(P(text_img("바퀴 위의 이야기는 계속됩니다", F_LABEL, 76, BRICK), 0.6, 0.2, 61), -3)
    # 전환용 종이: 크라프트지 + 불규칙한 윗변 + 흰 섬유
    sheet_h = H + 260
    sheet = load_paper("kraft2.jpg", (W + 80, sheet_h)).convert("RGBA")
    body = Image.new("L", sheet.size, 0)
    ImageDraw.Draw(body).polygon(rough_polygon([(-60, 40), (W + 140, 40), (W + 140, sheet_h + 60), (-60, sheet_h + 60)],
                                               99, amp=16), fill=255)
    fib = np.asarray(body.filter(ImageFilter.MaxFilter(15)), np.float32)
    noise = np.random.default_rng(9).random(fib.shape)
    fib = np.maximum(fib * (noise > 0.25), np.asarray(body, np.float32))
    tear = Image.new("RGBA", sheet.size, WHITE + (0,))
    tear.putalpha(Image.fromarray(fib.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)))
    sheet.putalpha(body)
    tear.alpha_composite(sheet)
    A["tear_sheet"] = with_shadow(tear, (0, -10), 14, 110)
    A["tear_body"] = body
    return A


def bg(A, t):
    return A["bg"][int(t * BOIL_FPS) % 3].convert("RGBA")


def sec0(st, u, A):
    fld = A["field"]
    cut_in(st, A["g_140"], 1300, 330, u, 0.8, 1)
    blob_rise(st, A["blob_o"], 1260, 620, u, 0.1, 2)
    draw_doodle(st, A["d_tr"], seg(u, 0.9, 1.5), ORANGE, 18, fld)
    matte_reveal(st, A["road"], 1270, 600, u, 0.3, 3)
    draw_doodle(st, A["d_bl"], seg(u, 1.1, 1.6), TEAL, 16, fld)
    write(st, A["s0_script"], 470, 300, u, 1.1, 0.6, 4)
    stamp(st, A["s0_stamp"], 500, 560, u, 1.75, 5)
    label(st, A["s0_label"], 480, 810, u, 2.1, 6)


def sec1(st, u, A):
    fld = A["field"]
    cut_in(st, A["g_1886"], 1300, 360, u, 0.7, 11)
    blob_rise(st, A["blob_t"], 1300, 690, u, 0.1, 12)
    draw_doodle(st, A["d_tr"], seg(u, 0.9, 1.5), ORANGE, 18, fld)
    matte_reveal(st, A["c1886"], 1340, 720, u, 0.3, 13)
    draw_doodle(st, A["d_bl"], seg(u, 1.1, 1.6), TEAL, 16, fld)
    label(st, A["s1_label"], 300, 190, u, 1.0, 14)
    stamp(st, A["s1_first"], 350, 350, u, 1.3, 15)
    stamp(st, A["s1_car"], 520, 550, u, 1.5, 16)
    write(st, A["s1_script1"], 330, 760, u, 1.8, 0.45, 17)
    write(st, A["s1_script2"], 300, 870, u, 2.2, 0.35, 18)
    brush_in(st, A["s1_brush"], 420, 990, u, 2.6, 19)
    stamp(st, A["s1_speed"], 420, 985, u, 2.82, 20)


def sec2(st, u, A):
    for i, band in enumerate(A["bands"]):          # P10: 띠가 차례로 쓸려 올라온다
        t0 = 0.1 + i * 0.28
        if u >= t0:
            k = expo_out(seg(u, t0, t0 + 0.35))
            jx, jy = jit(u, 20 + i)
            st.paste(band, (int(jx), int((1 - k) * 1000 + jy)), band)
    matte_reveal(st, A["c1908"], 1560, 820, u, 1.35, 25)
    pos = [(860, 200), (840, 400), (820, 600), (800, 790)]
    for i, line in enumerate(A["s2_lines"]):
        stamp(st, line, pos[i][0], pos[i][1], u, 0.32 + i * 0.28, 30 + i)


def sec3(st, u, A):
    for i, pc in enumerate(A["split"]):             # P14: 찢어 나눈 배경
        if u >= 0.05 + i * 0.12:
            jx, jy = jit(u, 40 + i)
            st.paste(pc, (int(jx), int(jy)), pc)
    matte_reveal(st, A["c1950"], 1180, 800, u, 0.9, 41)
    label(st, A["s3_label"], 300, 170, u, 1.5, 42)
    stamp(st, A["s3_stamp"], 640, 340, u, 1.75, 43)
    write(st, A["s3_script"], 660, 500, u, 2.05, 0.7, 44)


def sec4(st, u, A):
    fld = A["field"]
    blob_rise(st, A["blob_m"], 960, 580, u, 0.1, 50)
    for i in range(5):                              # P9: 반복 적층
        if u >= 0.5 + i * 0.1:
            jx, jy = jit(u, 60 + i)
            for x in (400, 1520):
                put(st, A["s4_rep"], x + jx, 860 - i * 140 + jy)
    matte_reveal(st, A["c1973"], 960, 660, u, 0.3, 51)
    if u >= 1.2:
        k = expo_out(seg(u, 1.2, 1.4))
        jx, jy = jit(u, 70)
        put(st, A["s4_bar"], 960 + jx, 990 + (1 - k) * 220 + jy)
        stamp(st, A["s4_bartext"], 960, 982, u, 1.38, 71)
    draw_doodle(st, A["d_tl"], seg(u, 1.0, 1.5), TEAL, 16, fld)
    write(st, A["s4_script"], 1020, 110, u, 1.7, 0.7, 72)


def sec5(st, u, A):
    fld = A["field"]
    cut_in(st, A["g_ev"], 1420, 380, u, 0.8, 80)
    blob_rise(st, A["blob_g"], 1400, 660, u, 0.1, 81)
    draw_doodle(st, A["d_br"], seg(u, 0.9, 1.4), ORANGE, 18, fld)
    matte_reveal(st, A["c2020"], 1420, 680, u, 0.3, 82)
    label(st, A["s5_label"], 260, 190, u, 1.0, 83)
    stamp(st, A["s5_ev"], 340, 370, u, 1.25, 84)
    stamp(st, A["s5_auto"], 420, 560, u, 1.45, 85)
    brush_in(st, A["s5_brush"], 400, 745, u, 1.7, 86)
    write(st, A["s5_script1"], 400, 740, u, 1.85, 0.5, 87)
    write(st, A["s5_script2"], 380, 870, u, 2.3, 0.45, 88)


def sec6(st, u, A):
    for i, (pc, (dx, dy)) in enumerate(A["corners"]):   # P15
        t0 = 0.35 + i * 0.18
        if u >= t0:
            k = expo_out(seg(u, t0, t0 + 0.3))
            jx, jy = jit(u, 90 + i)
            st.paste(pc, (int(dx * (1 - k) * 420 + jx), int(dy * (1 - k) * 420 + jy)), pc)
    write(st, A["s6_script"], 960, 490, u, 1.3, 1.0, 96)
    write(st, A["s6_small"], 960, 720, u, 2.1, 0.5, 97)


SEC = [sec0, sec1, sec2, sec3, sec4, sec5, sec6]


def render_section(A, i, t):
    st = bg(A, t)
    SEC[i](st, t - SECTIONS[i][0], A)
    return st


def crumple_ring(A, pts, width):
    """P12: 구멍 가장자리 — 구겨진 종이 질감이 말려 올라간 테두리."""
    ring = Image.new("L", (W, H), 0)
    ImageDraw.Draw(ring).line(pts + [pts[0]], fill=255, width=int(width), joint="curve")
    ring = ring.filter(ImageFilter.GaussianBlur(1.2))
    cf = A["crumple_field"]
    shade = np.clip(cf * 1.05, 0.6, 1.3)[..., None] * np.array([236, 228, 212], np.float32)
    col = Image.fromarray(shade.clip(0, 255).astype(np.uint8)).convert("RGBA")
    col.putalpha(ring)
    return col, ring


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
    prev = render_section(A, i - 1, SECTIONS[i][0] - 1e-3)
    if kind in ("push_x", "push_y"):                    # P11
        k = expo_out(u / dur)
        out = Image.new("RGBA", (W, H))
        if kind == "push_x":
            off = int(k * W)
            out.paste(prev, (-off, 0))
            out.paste(cur, (W - off, 0))
            sh = Image.new("RGBA", (60, H), (40, 28, 20, 90)).filter(ImageFilter.GaussianBlur(12))
            out.alpha_composite(sh, (int(clamp(W - off - 60, 0, W - 60)), 0))
        else:
            off = int(k * H)
            out.paste(prev, (0, -off))
            out.paste(cur, (0, H - off))
            sh = Image.new("RGBA", (W, 60), (40, 28, 20, 90)).filter(ImageFilter.GaussianBlur(12))
            out.alpha_composite(sh, (0, int(clamp(H - off - 60, 0, H - 60))))
        return out
    if kind == "hole":                                  # P12
        k = ease_in_out(u / dur)
        cx, cy = lerp(1500, 960, k), lerp(260, 540, k)
        r = lerp(40, 1400, k ** 1.6)
        rng = random.Random(3)
        pts = []
        for j in range(120):
            a = 2 * math.pi * j / 120
            rr = r * (1 + 0.05 * math.sin(a * 3) + 0.03 * math.sin(a * 11) + rng.uniform(-0.03, 0.03))
            pts.append((cx + rr * math.cos(a), cy + rr * 0.8 * math.sin(a)))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon(pts, fill=255)
        out = prev.copy()
        out.paste(cur, (0, 0), m)
        col, ring = crumple_ring(A, pts, 26 + 50 * (1 - k))
        shadow = Image.new("RGBA", (W, H), (50, 36, 26, 0))
        shadow.putalpha(ring.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.6)))
        out.alpha_composite(shadow, (8, 10))
        out.alpha_composite(col)
        return out
    if kind == "tear":                                  # P13
        k = expo_out(u / dur)
        top = int(lerp(H + 60, -120, k))
        sheet = A["tear_sheet"]
        out = prev.copy()
        out.paste(sheet, (-40, top - 44), sheet)
        body = Image.new("L", (W, H), 0)
        body.paste(A["tear_body"], (-40, top))
        body = body.filter(ImageFilter.MinFilter(11))
        out.paste(cur, (0, 0), body)                    # 올라오는 종이 위에 다음 장면이 이미 있다
        return out
    return cur


def main():
    A = build()
    film = [np.random.default_rng(k).normal(0, 3.5, (H, W, 1)).astype(np.int16) for k in range(5)]
    only = sys.argv[1:]
    if only:
        dd = os.environ.get("PREVIEW_DIR", HERE)
        for ts in only:
            render_content(A, float(ts)).convert("RGB").save(os.path.join(dd, f"pc2_{ts}.png"))
        return
    ffmpeg = shutil.which("ffmpeg")
    n = int(DUR * FPS)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    last, frame = None, None
    for fi in range(n):
        key = math.floor(fi / FPS * POSTERIZE_FPS + 1e-6)
        if key != last:
            frame, last = np.asarray(render_content(A, fi / FPS).convert("RGB"), np.int16), key
        proc.stdin.write((frame + film[fi % 5]).clip(0, 255).astype(np.uint8).tobytes())
        if fi % 90 == 0:
            print(f"frame {fi}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
