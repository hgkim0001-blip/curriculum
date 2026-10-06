"""페이퍼 콜라주 개선 테스트: 1886 장면 한 컷 (4.6초).

개선점
- 재료: Flow로 만든 실제 종이 스캔(assets/paper/*)을 배경·블롭·글자·색면 전부에 '인쇄된 것처럼' 곱해 입힌다
- 찢긴 가장자리: Flow로 만든 실제 찢어진 흰 종이 띠(strips.jpg)를 잘라 라벨·리빌 띠로 사용
- 구성: 차량을 화면 높이 가득, 아래로 잘려 나가게. 블롭·글자가 차량과 겹쳐 한 덩어리
- 대형 배경 글자: 글자 모양으로 신문 스캔을 오려 채움
- 폰트: Black Han Sans(도장), 나눔 붓글씨(필기체), Yeon Sung(라벨) — OFL 무료 폰트
출력: test_1886_v2.mp4
"""
import math
import os
import random
import shutil
import subprocess
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.join(HERE, "assets", "paper")
FONTS = os.path.join(HERE, "assets", "fonts")
OUT = os.path.join(HERE, "test_1886_v2.mp4")

W, H, FPS, DUR = 1920, 1080, 30, 4.6
STEP_FPS, BOIL_FPS = 12, 3

TEAL = (72, 158, 166)
ORANGE = (218, 128, 36)
MUSTARD = (234, 188, 76)
BRICK = (178, 58, 40)
BLUE = (52, 104, 168)
OLIVE = (104, 128, 50)
INK = (44, 32, 26)
WHITE = (246, 240, 226)

F_STAMP = os.path.join(FONTS, "BlackHanSans-Regular.ttf")
F_SCRIPT = os.path.join(FONTS, "NanumBrushScript-Regular.ttf")
F_LABEL = os.path.join(FONTS, "YeonSung-Regular.ttf")
_fc = {}


def font(p, s):
    k = (p, int(s))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(p, int(s))
    return _fc[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def seg(u, a, b):
    return clamp((u - a) / (b - a))


def expo_out(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def back_out(x, s=2.2):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def step_time(t):
    return math.floor(t * STEP_FPS + 1e-6) / STEP_FPS


def jit(t, seed, amp=1.6):
    r = random.Random(int(t * STEP_FPS + 1e-6) * 7919 + seed)
    return r.uniform(-amp, amp), r.uniform(-amp, amp)


# ---------------- 실제 종이 재료 ----------------
def load_paper(name, size=(W, H)):
    im = Image.open(os.path.join(PAPER, name)).convert("RGB")
    iw, ih = im.size
    im = im.crop((0, 0, int(iw * 0.92), int(ih * 0.92)))   # 워터마크 제거
    return ImageOps.fit(im, size, Image.LANCZOS)


def texture_field(img):
    """종이 스캔 → 평균 1.0 근처의 밝기 변조 맵(섬유·주름)."""
    a = np.asarray(img.convert("L"), np.float32)
    return a / a.mean()


def print_on(sprite, field, strength=0.9, riso=None, knock=0.10, ox=0, oy=0):
    """스프라이트(RGBA)를 종이에 인쇄한 것처럼: 종이 결을 곱하고, 잉크가 덜 묻은 반점을 알파에서 뺀다."""
    w, h = sprite.size
    fh, fw = field.shape
    x0, y0 = ox % max(1, fw - w), oy % max(1, fh - h)
    f = field[y0:y0 + h, x0:x0 + w]
    if f.shape != (h, w):
        f = np.asarray(Image.fromarray((field * 100).clip(0, 255).astype(np.uint8)).resize((w, h)), np.float32) / 100
    a = np.asarray(sprite).astype(np.float32)
    a[..., :3] *= (1 + (f[..., None] - 1) * strength)
    if riso is not None:
        rh, rw = riso.shape
        r = riso[(np.arange(h)[:, None] + oy) % rh, (np.arange(w)[None, :] + ox) % rw]
        a[..., 3] *= 1 - knock * r
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def riso_map(img):
    """리소 잉크 스캔 → 0~1 '잉크 빠짐' 맵(밝은 곳=빠짐)."""
    a = np.asarray(img.convert("L"), np.float32) / 255
    return np.clip((a - 0.35) / 0.5, 0, 1)


def extract_strips(img, min_w=300):
    """검은 배경 위 흰 찢어진 종이 띠 → 각 띠를 RGBA로 잘라 낸다."""
    rgb = img.convert("RGB")
    L = np.asarray(rgb.convert("L"), np.float32)
    alpha = np.clip((L - 55) / 70, 0, 1)
    small = alpha[::4, ::4] > 0.5
    h, w = small.shape
    seen = np.zeros_like(small)
    boxes = []
    for sy in range(h):
        for sx in range(w):
            if small[sy, sx] and not seen[sy, sx]:
                q = deque([(sy, sx)])
                seen[sy, sx] = True
                ys, xs = [sy], [sx]
                while q:
                    y, x = q.popleft()
                    for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                        if 0 <= ny < h and 0 <= nx < w and small[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                            ys.append(ny)
                            xs.append(nx)
                bx = (min(xs) * 4, min(ys) * 4, max(xs) * 4 + 4, max(ys) * 4 + 4)
                if bx[2] - bx[0] >= min_w:
                    comp = np.zeros((h, w), bool)
                    comp[ys, xs] = True
                    boxes.append((bx, comp))
    out = []
    for bx, comp in boxes:
        # 이 띠에 속한 픽셀만(이웃 띠 제외): 작은 마스크를 키워 살짝 넓힌 뒤 원래 알파와 곱한다
        cm = Image.fromarray((comp * 255).astype(np.uint8)).resize((w * 4, h * 4), Image.NEAREST)
        cm = np.asarray(cm.filter(ImageFilter.MaxFilter(9)), np.float32)[:alpha.shape[0], :alpha.shape[1]] / 255
        a = alpha * cm
        piece = rgb.crop(bx).convert("RGBA")
        piece.putalpha(Image.fromarray((a[bx[1]:bx[3], bx[0]:bx[2]] * 255).astype(np.uint8)))
        area = comp.sum()
        fill = area * 16 / ((bx[2] - bx[0]) * (bx[3] - bx[1]))   # 1에 가까울수록 수평 직사각형 띠
        out.append((fill, area, piece))
    out.sort(key=lambda o: (-int(o[0] > 0.6), -int(o[1])))                # 수평 띠 우선, 큰 것 우선
    return [p for _, _, p in out]


# ---------------- 요소 ----------------
def text_img(text, fpath, size, color, pad=24):
    f = font(fpath, size)
    l, t, r, b = f.getbbox(text)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=color)
    return im


def rot(im, a):
    return im.rotate(a, expand=True, resample=Image.BICUBIC)


def blob(size, color, seed):
    w, h = size
    rng = random.Random(seed)
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    pts = []
    for i in range(160):
        a = 2 * math.pi * i / 160
        r = (1 + 0.11 * math.sin(2 * a + ph[0]) + 0.07 * math.sin(3 * a + ph[1])
             + 0.035 * math.sin(5 * a + ph[2]) + 0.015 * math.sin(9 * a + ph[3]))
        pts.append((w / 2 + w / 2 * 0.88 * r * math.cos(a), h / 2 + h / 2 * 0.88 * r * math.sin(a)))
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(out).polygon(pts, fill=color + (255,))
    return out


def brush_stroke(w, h, color, seed):
    """붓 자국: 가장자리가 들쭉날쭉하고 끝이 갈라진 띠."""
    rng = random.Random(seed)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    top, bot = [], []
    for x in range(0, w + 1, 10):
        taper = min(1, x / 40, (w - x) / 60)
        top.append((x, h * 0.5 - h * 0.42 * taper + rng.uniform(-4, 4)))
        bot.append((x, h * 0.5 + h * 0.42 * taper + rng.uniform(-4, 4)))
    d.polygon(top + bot[::-1], fill=color + (255,))
    a = np.asarray(out).astype(np.float32)
    streak = np.random.default_rng(seed).random((h, 1))
    a[..., 3] *= np.where(streak < 0.2, 0.45, 1.0)          # 붓결
    return Image.fromarray(a.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.7))


def doodle_line(size, pts, color, width=16):
    w, h = size
    dense = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(24):
            s = k / 24
            dense.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * s + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * s * s
                                      + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * s ** 3) for j in range(2)))
    return dense


def draw_doodle(st, dense, p, color, width, field):
    if p <= 0:
        return
    n = max(2, int(len(dense) * clamp(p)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(n - 1):                                   # 손으로 그은 듯 굵기 변화
        wv = width * (0.8 + 0.25 * math.sin(i / 9))
        d.line([dense[i], dense[i + 1]], fill=color + (255,), width=int(wv))
    r = width / 2
    for x, y in (dense[0], dense[n - 1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))
    st.alpha_composite(print_on(layer, field, 0.8))


def giant_news(text, size, news, seed):
    """P8: 글자 모양으로 신문 스캔을 오려 낸 대형 배경 글자."""
    f = font(F_STAMP, size)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + 40, b - t + 40
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((20 - l, 20 - t), text, font=f, fill=255)
    rng = random.Random(seed)
    x0, y0 = rng.randint(0, max(0, news.width - w)), rng.randint(0, max(0, news.height - h))
    src = news.crop((x0, y0, x0 + w, y0 + h)) if news.width >= w and news.height >= h else news.resize((w, h))
    src = ImageEnhance.Contrast(ImageOps.grayscale(src)).enhance(1.2)
    src = ImageOps.colorize(src, black=(70, 55, 45), white=(236, 226, 206)).convert("RGBA")
    # 가장자리를 살짝 찢긴 듯 거칠게
    ma = np.asarray(m.filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    noise = np.random.default_rng(seed).random(ma.shape) * 90
    ma = np.clip((ma - noise) * 2.2, 0, 255)
    src.putalpha(Image.fromarray(ma.astype(np.uint8)))
    return src


def put(st, spr, cx, cy, scale=1.0, blur=0.0):
    if spr is None or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if blur > 0.4:
        spr = spr.filter(ImageFilter.GaussianBlur(blur))
    st.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


def with_shadow(spr, off=(10, 14), blur=12, alpha=90):
    pad = blur * 2 + max(off)
    out = Image.new("RGBA", (spr.width + 2 * pad, spr.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    sh.paste(spr.getchannel("A").point(lambda v: alpha if v > 20 else 0), (pad + off[0], pad + off[1]))
    out.paste(Image.new("RGBA", out.size, (50, 34, 22, 255)), (0, 0), sh.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(spr, (pad, pad))
    return out


# ---------------- 조립 ----------------
def build():
    A = {}
    k1 = load_paper("kraft1.jpg")
    crumple = texture_field(load_paper("crumple.jpg"))            # 구겨진 종이 음영만 가져와
    tint = np.asarray(k1, np.float32).mean((0, 1)) * 0.98         # 크라프트 색에 곱한다
    crumple = Image.fromarray((crumple[..., None] * tint).clip(0, 255).astype(np.uint8))
    A["bg"] = [k1, load_paper("kraft2.jpg"), crumple]
    A["field"] = texture_field(load_paper("kraft1.jpg", (2400, 1400)))
    A["riso"] = riso_map(load_paper("riso.jpg", (2400, 1400)))
    news = load_paper("news.jpg", (2400, 1400))
    strips = extract_strips(Image.open(os.path.join(PAPER, "strips.jpg")))
    fld, riso = A["field"], A["riso"]

    # 대형 배경 글자: 신문 오려 붙이기
    A["giant"] = giant_news("1886", 560, news, 3)

    # 블롭(종이 결 인쇄)
    A["blob"] = with_shadow(print_on(blob((1180, 1000), TEAL, 7), fld, 1.0, riso, 0.12, 300, 200), (6, 10), 10, 60)

    # 차량: 세피아 + 필름 그레인 + 종이 결 살짝, 그림자
    car = Image.open(os.path.join(HERE, "cutouts", "car_1886.png")).convert("RGBA")
    g = ImageEnhance.Contrast(ImageOps.grayscale(car.convert("RGB"))).enhance(1.15)
    sep = ImageOps.colorize(g, black=(40, 28, 20), white=(240, 222, 190)).convert("RGBA")
    sep.putalpha(car.getchannel("A"))
    s = 1340 / sep.width
    sep = sep.resize((int(sep.width * s), int(sep.height * s)), Image.LANCZOS)
    raw = print_on(sep, fld, 0.35, ox=500, oy=100)
    A["car"] = with_shadow(raw, (12, 16), 14, 95)
    # 알파 매트: 그림자 없는 차량 실루엣(에펙의 Track Matte용 복제 레이어, 눈 끔)
    pad = 14 * 2 + 16
    matte = Image.new("L", A["car"].size, 0)
    matte.paste(raw.getchannel("A"), (pad, pad))
    A["car_matte"] = matte

    # 리빌 띠(실제 찢어진 흰 종이)
    strip = strips[0] if strips else Image.new("RGBA", (1600, 120), WHITE + (255,))
    A["reveal_strip"] = strip.resize((A["car"].width, 118), Image.LANCZOS)   # 차량 폭 전체를 덮는 얇은 띠

    # 라벨: 실제 찢어진 종이 띠 조각 + 글자
    lab = strips[1] if len(strips) > 1 else strip
    lab = lab.resize((340, max(90, int(lab.height * 340 / lab.width))), Image.LANCZOS)
    lab = ImageOps.fit(lab, (340, 110))
    A["pill_bg"] = rot(with_shadow(lab, (4, 6), 5, 70), -5)
    A["pill_tx"] = rot(print_on(text_img("1886년", F_LABEL, 74, BRICK), fld, 0.6, riso, 0.25, 90, 40), -5)

    # 도장 글자(굵은 헤드라인): 종이 결 + 잉크 빠짐
    A["t_first"] = rot(print_on(text_img("최초의", F_STAMP, 170, OLIVE), fld, 1.0, riso, 0.35, 120, 300), -4)
    A["t_car"] = rot(print_on(text_img("자동차", F_STAMP, 250, BLUE), fld, 1.0, riso, 0.35, 700, 500), -3)
    # 필기체
    A["t_script"] = rot(print_on(text_img("카를 벤츠의 모터바겐", F_SCRIPT, 150, BRICK), fld, 0.8, riso, 0.15, 60, 900), -5)
    # 붓 하이라이트 + 문구
    A["brush"] = rot(print_on(brush_stroke(560, 120, MUSTARD, 3), fld, 1.0, riso, 0.3, 300, 700), -3)
    A["t_speed"] = rot(print_on(text_img("최고 시속 16km", F_STAMP, 76, BRICK), fld, 0.9, riso, 0.3, 30, 60), -3)
    # 낙서 선
    A["doodle1"] = doodle_line((W, H), [(1960, 170), (1760, 70), (1560, 210), (1380, 100), (1230, 190)], ORANGE)
    A["doodle2"] = doodle_line((W, H), [(-30, 980), (160, 880), (330, 1010), (520, 900)], TEAL)
    return A


CAR_C = (1300, 720)


def render(A, t):
    u = step_time(t)
    st = A["bg"][int(u * BOIL_FPS) % 3].convert("RGBA")
    fld = A["field"]

    # P8 대형 배경 글자(0.7초 컷인)
    if u >= 0.7:
        jx, jy = jit(u, 1)
        put(st, A["giant"], 1250 + jx, 360 + jy)
    # P1 블롭 솟기
    if u >= 0.1:
        k = expo_out(seg(u, 0.1, 0.5))
        jx, jy = jit(u, 2)
        put(st, A["blob"], 1230 + jx, 690 + (1 - k) * 800 + jy, scale=0.8 + 0.2 * k)
    # P3 낙서 선(블롭 뒤를 지나 앞으로)
    draw_doodle(st, A["doodle1"], seg(u, 0.9, 1.5), ORANGE, 18, fld)
    # P2 차량이 올라오며 찢어진 흰 종이 띠가 늦게 벗겨짐
    if u >= 0.3:
        car = A["car"]
        k = expo_out(seg(u, 0.3, 0.8))
        cy = CAR_C[1] + (1 - k) * 700
        r = ease_in_out(seg(u, 0.47, 1.25))
        strip_y = lerp(car.height * 0.55, -120, r)
        cut = max(0, int(strip_y))
        jx, jy = jit(u, 3)
        x0, y0 = int(CAR_C[0] - car.width / 2 + jx), int(cy - car.height / 2 + jy)
        layer = Image.new("RGBA", car.size, (0, 0, 0, 0))
        if cut < car.height:                                   # 띠 아래쪽의 차량만 보인다
            part = car.crop((0, cut, car.width, car.height))
            layer.paste(part, (0, cut))
        if r < 1:                                              # 흰 띠는 차량 실루엣 안에서만(알파 매트)
            s = A["reveal_strip"]
            sl = Image.new("RGBA", car.size, (0, 0, 0, 0))
            sl.paste(s, (0, int(strip_y - s.height * 0.55)))
            a = np.asarray(sl.getchannel("A"), np.float32) * np.asarray(A["car_matte"], np.float32) / 255
            sl.putalpha(Image.fromarray(a.astype(np.uint8)))
            layer.alpha_composite(sl)
        st.paste(layer, (x0, y0), layer)
    draw_doodle(st, A["doodle2"], seg(u, 1.1, 1.6), TEAL, 16, fld)

    # P4 라벨 → P5 도장 → P6 필기체 → P7 붓
    if u >= 1.0:
        jx, jy = jit(u, 4)
        put(st, A["pill_bg"], 300 + jx, 200 + jy, scale=back_out(seg(u, 1.0, 1.2)))
        p = seg(u, 1.22, 1.4)
        if p > 0:
            put(st, A["pill_tx"], 300 + jx, 196 + jy, 1.1 - 0.1 * p, 5 * (1 - p))
    for key, (x, y), t0, seed in (("t_first", (360, 360), 1.3, 5), ("t_car", (560, 560), 1.5, 6)):
        if u >= t0:
            p = seg(u, t0, t0 + 0.2)
            jx, jy = jit(u, seed)
            put(st, A[key], x + jx, y + jy, 1.1 - 0.1 * p, 6 * (1 - p))
    if u >= 1.8:  # 필기체 쓰기(왼쪽부터)
        spr = A["t_script"]
        p = seg(u, 1.8, 2.5)
        w = spr.width
        edge = int((w + 30) * p)
        m = np.clip((edge - np.arange(w)) / 30, 0, 1).astype(np.float32)
        s2 = spr.copy()
        s2.putalpha(Image.fromarray((np.asarray(spr.getchannel("A"), np.float32) * m[None, :]).astype(np.uint8)))
        jx, jy = jit(u, 7)
        put(st, s2, 640 + jx, 770 + jy)
    if u >= 2.55:
        b = A["brush"]
        w = max(1, int(b.width * seg(u, 2.55, 2.75)))
        bb = Image.new("RGBA", b.size, (0, 0, 0, 0))
        bb.paste(b.crop((0, 0, w, b.height)), (0, 0))
        jx, jy = jit(u, 8)
        put(st, bb, 470 + jx, 930 + jy)
        if u >= 2.78:
            p = seg(u, 2.78, 2.98)
            put(st, A["t_speed"], 470 + jx, 925 + jy, 1.1 - 0.1 * p, 5 * (1 - p))
    return st.convert("RGB")


def main():
    A = build()
    film = [np.random.default_rng(k).normal(0, 3.5, (H, W, 1)).astype(np.int16) for k in range(5)]
    only = sys.argv[1:]
    if only:
        dd = os.environ.get("PREVIEW_DIR", HERE)
        for ts in only:
            render(A, float(ts)).save(os.path.join(dd, f"t1886_{ts}.png"))
        return
    ffmpeg = shutil.which("ffmpeg")
    n = int(DUR * FPS)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    last, frame = None, None
    for fi in range(n):
        key = math.floor(fi / FPS * STEP_FPS + 1e-6)
        if key != last:
            frame, last = render(A, fi / FPS), key
        arr = np.asarray(frame, np.int16) + film[fi % 5]
        proc.stdin.write(arr.clip(0, 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    print("saved", OUT)


if __name__ == "__main__":
    main()
