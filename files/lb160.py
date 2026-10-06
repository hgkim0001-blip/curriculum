"""구겨진 종이 펴기 전환 (그린/블루 이중 키 소스).

소스: Paper Crumple Effect Green Screen (1920x1080, 29.97fps, 61프레임)
  - 파랑 = 종이 바깥 → 이전 장면(A)
  - 초록 = 종이 안쪽 면 → 다음 장면(B). 초록의 밝기 변화(구김 음영)를 B에 곱해 구겨진 종이에 인쇄된 것처럼
  - 흰색 = 종이 뒷면·접힌 가장자리 → 그대로
사용: frames = load_crumple(path, scale) → composite(frame, A, B)
"""
import os
import shutil
import subprocess

import numpy as np
from PIL import Image

W, H = 1920, 1080
DEFAULT_SRC = r"E:\SSD외장하드\01_수업자료\2025_2\02_소스자산\paper ani소스들\Paper Crumple Effect Green Screen   Free To Use.mp4"


def load_crumple(path=DEFAULT_SRC, scale=1.0, cx=0.5, cy=0.5):
    """소스 영상을 RGB 프레임 배열로 읽는다. scale>1이면 종이를 확대(평평해진 종이가 화면을 덮게)."""
    ffmpeg = shutil.which("ffmpeg")
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    if abs(scale - 1) < 1e-3:
        return fr
    out = []
    for f in fr:
        im = Image.fromarray(f)
        w, h = int(W / scale), int(H / scale)
        x0, y0 = int(W * cx - w / 2), int(H * cy - h / 2)
        # 확대 시 화면 밖은 파랑(=이전 장면)으로 채운다
        big = Image.new("RGB", (W, H), (0, 100, 255))
        crop = im.crop((x0, y0, x0 + w, y0 + h)).resize((W, H), Image.BICUBIC)
        big.paste(crop)
        out.append(np.asarray(big))
    return np.stack(out)


SRC_FPS = 30000 / 1001
ELEMENT_FPS = 12   # 기준: 전환·요소는 Posterize Time 12


def frame_at(frames, u, speed=1.0, step_fps=ELEMENT_FPS):
    """전환 시작 후 u초 시점의 소스 프레임(12fps로 끊어서). 끝나면 마지막 프레임(펴진 종이)을 유지."""
    us = int(u * step_fps + 1e-6) / step_fps
    i = int(us * SRC_FPS * speed)
    return frames[min(max(i, 0), len(frames) - 1)]


def duration(frames, speed=1.0):
    return len(frames) / SRC_FPS / speed


def mattes(frame):
    """(파랑 알파, 초록 알파, 초록 음영) — 모두 0~1 float."""
    f = frame.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    blue = np.clip((b - np.maximum(r, g) - 40) / 70, 0, 1)
    green = np.clip((g - np.maximum(r, b) - 30) / 60, 0, 1)
    # 초록 면의 밝기(구김 음영) → 평균 1.0 근처
    shade = g / 215.0
    shade = np.clip(shade, 0.55, 1.25)
    return blue, green, shade


def composite(frame, A, B, shade_strength=0.9):
    """frame: 소스 한 프레임(RGB uint8), A: 이전 장면, B: 다음 장면(RGB uint8 배열)."""
    blue, green, shade = mattes(frame)
    f = frame.astype(np.float32)
    # 흰 종이(스필 제거): 파랑·초록 번짐을 회색으로 눌러 준다
    paper = f.copy()
    m = paper.min(axis=2, keepdims=True)
    paper = np.minimum(paper, m + 18)
    Bs = B.astype(np.float32) * (1 + (shade[..., None] - 1) * shade_strength)
    out = paper * (1 - blue - green)[..., None] + A.astype(np.float32) * blue[..., None] + Bs * green[..., None]
    return out.clip(0, 255).astype(np.uint8)


if __name__ == "__main__":
    import sys
    # 테스트: 두 이미지로 전환 클립 만들기  python crumple_transition.py A.png B.png out.mp4 [scale]
    a = np.asarray(Image.open(sys.argv[1]).convert("RGB").resize((W, H)))
    b = np.asarray(Image.open(sys.argv[2]).convert("RGB").resize((W, H)))
    scale = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    frames = load_crumple(scale=scale)
    ffmpeg = shutil.which("ffmpeg")
    p = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", sys.argv[3]],
                         stdin=subprocess.PIPE)
    hold = [a] * 15
    for x in hold:
        p.stdin.write(x.tobytes())
    for f in frames:
        p.stdin.write(composite(f, a, b).tobytes())
    for _ in range(20):
        p.stdin.write(b.tobytes())
    p.stdin.close()
    p.wait()
    print("saved", sys.argv[3], len(frames), "frames")
