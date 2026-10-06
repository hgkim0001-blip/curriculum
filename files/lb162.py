"""흰 배경 차량 이미지(images_cars/*.jpg) → 차량만 남긴 투명 PNG(cutouts/*.png).

방식: 이미지 테두리와 연결된 '밝고 채도 낮은' 픽셀만 배경으로 판단(flood fill)해 지운다.
     → 차량 안쪽의 흰 부분(크롬, 흰 타이어 띠)은 테두리와 끊겨 있어 남는다.
     가장자리는 1px 안쪽으로 줄이고 살짝 부드럽게(feather) 처리, 흰 테두리 번짐(fringe)을 제거한다.
"""
import glob
import os
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "images_cars")
DST = os.path.join(HERE, "cutouts")
OPEN_TYPES = ("1886", "1908")   # 바퀴살·개방형 차체


def background_mask(rgb, thresh=28):
    """테두리에서 시작하는 flood fill. 배경=True."""
    h, w, _ = rgb.shape
    f = rgb.astype(np.int16)
    # 흰 배경과의 거리(밝기 + 채도)
    dist = (255 - f.min(axis=2)) + (f.max(axis=2) - f.min(axis=2))
    cand = dist < thresh
    bg = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if cand[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if cand[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))
    return bg


def enclosed_white(rgb, bg, thresh=16, min_area=40):
    """테두리와 끊긴 흰 영역(바퀴살 사이, 유리창 너머 배경 등) 중 '순백에 가깝고 일정 크기 이상'인 것을 배경으로."""
    h, w, _ = rgb.shape
    f = rgb.astype(np.int16)
    dist = (255 - f.min(axis=2)) + (f.max(axis=2) - f.min(axis=2))
    cand = (dist < thresh) & ~bg
    seen = np.zeros((h, w), bool)
    extra = np.zeros((h, w), bool)
    ys, xs = np.nonzero(cand)
    for sy, sx in zip(ys, xs):
        if seen[sy, sx]:
            continue
        comp = [(sy, sx)]
        seen[sy, sx] = True
        i = 0
        while i < len(comp):
            y, x = comp[i]
            i += 1
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    comp.append((ny, nx))
        if len(comp) >= min_area:
            cy, cx = zip(*comp)
            extra[list(cy), list(cx)] = True
    return extra


def ground_shadow(rgb, bg, rows=0.10):
    """맨 아래쪽의 밝은 무채색(바닥 그림자)을 배경으로."""
    h = rgb.shape[0]
    f = rgb.astype(np.int16)
    light_gray = (f.min(axis=2) > 165) & ((f.max(axis=2) - f.min(axis=2)) < 16)
    m = np.zeros_like(bg)
    y0 = int(h * (1 - rows))
    m[y0:] = light_gray[y0:]
    return m


def cutout(path):
    im = Image.open(path).convert("RGB")
    iw, ih = im.size
    im = im.crop((0, 0, int(iw * 0.93), int(ih * 0.93)))   # 우하단 ✦ 워터마크 제거
    rgb = np.asarray(im)
    bg = background_mask(rgb)
    # 바퀴살이 있는 개방형 차량(1886, 1908)만: 바퀴살 사이 흰 배경 + 바닥 그림자 제거.
    # 창문이 있는 차량에 적용하면 유리 반사·흰 타이어 띠까지 뚫리므로 제외한다.
    name = os.path.basename(path)
    open_type = any(k in name for k in OPEN_TYPES)
    if open_type:
        bg |= enclosed_white(rgb, bg)
    bbox0 = Image.fromarray((~bg * 255).astype(np.uint8)).getbbox()
    if bbox0 and open_type:                # 차량 하단 10% 구간의 바닥 그림자
        sub = ground_shadow(rgb[bbox0[1]:bbox0[3]], bg[bbox0[1]:bbox0[3]])
        bg[bbox0[1]:bbox0[3]] |= sub
    alpha = Image.fromarray(np.where(bg, 0, 255).astype(np.uint8))
    alpha = alpha.filter(ImageFilter.MinFilter(3))          # 1px 안쪽으로 → 흰 번짐 제거
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))     # 부드러운 가장자리
    out = im.convert("RGBA")
    out.putalpha(alpha)
    bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    pad = 6
    out = out.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                    min(out.width, bbox[2] + pad), min(out.height, bbox[3] + pad)))
    return out, bg.mean()


def main():
    os.makedirs(DST, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(SRC, "*.jpg"))):
        out, frac = cutout(p)
        name = os.path.splitext(os.path.basename(p))[0] + ".png"
        out.save(os.path.join(DST, name))
        print(f"{name}: {out.size}, 배경 비율 {frac:.0%}")


if __name__ == "__main__":
    main()
