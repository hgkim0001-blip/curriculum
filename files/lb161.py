"""배경음악 + 효과음을 콜라주 영상에 입히기 (numpy만 사용).

- BGM: flow_music.wav(Google Flow Music으로 만든 곡)가 있으면 그 곡을 편집해서 사용
        · 곡 13.0초부터 시작 → 곡의 브레이크 후 풀밴드 진입(17.00초)이 첫 장면 전환(4.0초)에 맞는다
        · 영상 약 23.7~25.7초(4박) 동안 본 구간이 곡의 아웃트로(166.30초~)로 박자 맞춰 디졸브된다
      없으면 120BPM 합성 팝으로 대체
- SFX: 장면 전환 종이 '휙', 종이 조각이 붙을 때 '톡', 연도 글자 '탁'
출력: bgm.wav, car_history_collage_music.mp4
"""
import os
import shutil
import subprocess
import wave

import numpy as np

import make_video_collage as mv

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
FLOW_WAV = os.path.join(HERE, "flow_music.wav")
USE_FLOW = os.path.exists(FLOW_WAV)
DUR = mv.DUR
N = int(SR * DUR)
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(42)


# ---------- DSP helpers ----------
def filt(x, lo=None, hi=None):
    """FFT 기반 필터: lo 이상 통과(하이패스), hi 이하 통과(로우패스)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi:
        g *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * g, len(x))


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    e = np.exp(-t / d)
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def add(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= buf.shape[0] or i + len(sig) <= 0:
        return
    j = min(buf.shape[0], i + len(sig))
    s = sig[: j - i] * gain
    buf[i:j, 0] += s * np.sqrt(0.5 * (1 - pan))
    buf[i:j, 1] += s * np.sqrt(0.5 * (1 + pan))


def hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


# ---------- instruments ----------
def kick():
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t / 0.03)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.14)
    click = rng.normal(0, 1, n) * env(n, 0.0005, 0.004) * 0.3
    return np.tanh((s + click) * 1.6)


def snare():
    n = int(0.25 * SR)
    noise = filt(rng.normal(0, 1, n), lo=1500, hi=9000) * env(n, 0.001, 0.07)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * env(n, 0.001, 0.05)
    return noise * 0.8 + tone * 0.5


def clap():
    n = int(0.25 * SR)
    s = np.zeros(n)
    base = filt(rng.normal(0, 1, n), lo=900, hi=6000)
    for k, off in enumerate([0, 0.011, 0.022]):
        i = int(off * SR)
        s[i:] += base[: n - i] * env(n - i, 0.0005, 0.012 if k < 2 else 0.09)
    return s * 0.8


def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    return filt(rng.normal(0, 1, n), lo=7000) * env(n, 0.0005, 0.12 if open_ else 0.02)


def bass(note, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = hz(note)
    s = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 6))  # 톱니파 근사
    s = filt(s, hi=700) * env(n, 0.004, length * 0.9)
    return np.tanh(s * 1.2)


def epiano(notes, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m in notes:
        f = hz(m)
        s += (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.08)
              + 0.1 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.04))
    return s / len(notes) * env(n, 0.003, 0.18)


def marimba(note, length=0.5):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = hz(note)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.22) + 0.4 * np.sin(2 * np.pi * 3.99 * f * t) * np.exp(-t / 0.03)
    return s * env(n, 0.001, 1.0)


def glock(note):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    f = hz(note)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.15)) * np.exp(-t / 0.5)


# ---------- SFX ----------
def whoosh(length=0.9):
    """찢은 종이가 스쳐 지나가는 소리: 대역이 움직이는 노이즈 + 종이 바스락."""
    n = int(length * SR)
    t = np.linspace(0, 1, n)
    noise = rng.normal(0, 1, n)
    lo = filt(noise, lo=300, hi=1800)
    hi_ = filt(noise, lo=2500, hi=9000)
    shape = np.sin(np.pi * t) ** 2
    mix = lo * (1 - t) + hi_ * t  # 대역이 위로 쓸려 올라가는 느낌
    crackle = (rng.random(n) < 0.004) * rng.normal(0, 3, n)
    crackle = filt(crackle, lo=2000)
    return (mix * shape + crackle * shape * 0.6) * 0.9


def paper_pop(pitch=1.0):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * 160 * pitch * t * (1 - t * 3)) * env(n, 0.001, 0.03)
    snap = filt(rng.normal(0, 1, n), lo=1800, hi=8000) * env(n, 0.0005, 0.012)
    return thump * 0.7 + snap * 0.6


def stamp():
    """연도 글자가 붙을 때: 짧고 단단한 '탁'."""
    n = int(0.1 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 420 * t) * env(n, 0.0005, 0.015)
    return body * 0.6 + filt(rng.normal(0, 1, n), lo=3000) * env(n, 0.0003, 0.006) * 0.5


# ---------- music ----------
CHORDS = [  # (베이스 루트, 코드 구성음)  C  Am  F  G
    (36, [60, 64, 67, 72]),
    (33, [57, 60, 64, 69]),
    (41, [57, 60, 65, 69]),
    (43, [59, 62, 67, 71]),
]
MELODY = [  # 마디별 (박 오프셋, 음) — C 펜타토닉 모티프
    [(0, 76), (0.75, 79), (1.5, 76), (2, 74), (3, 72)],
    [(0, 72), (0.75, 76), (1.5, 72), (2, 69), (3, 67)],
    [(0, 69), (0.75, 72), (1.5, 77), (2, 76), (2.5, 74), (3, 72)],
    [(0, 74), (0.5, 76), (1, 79), (2, 81), (3, 79), (3.5, 76)],
]


def compose():
    mus = np.zeros((N, 2))
    n_bars = int(np.ceil(DUR / BAR))
    for b in range(n_bars):
        t0 = b * BAR
        root, chord = CHORDS[b % 4]
        intro = b < 1                      # 0~2초: 마림바 + EP만
        drums = b >= 1 and t0 < DUR - 1.0
        # 드럼
        if drums:
            for beat in range(4):
                tb = t0 + beat * BEAT
                if beat in (0, 2) or (beat == 3 and b % 2 == 1):
                    add(mus, kick(), tb + (0.25 * BEAT if beat == 3 else 0), 0.9)
                if beat in (1, 3):
                    add(mus, snare(), tb, 0.45)
                    add(mus, clap(), tb, 0.35, 0.2)
                for e in range(2):
                    add(mus, hat(open_=(e == 1 and beat == 3)), tb + e * BEAT / 2, 0.18, 0.4 if e else -0.3)
            # 베이스: 8분음표 루트-옥타브 바운스
            if not intro:
                for e in range(8):
                    note = root + (12 if e % 4 == 3 else 0)
                    add(mus, bass(note, BEAT / 2 * 0.9), t0 + e * BEAT / 2, 0.42)
        # EP 스탭: 오프비트
        for beat in range(4):
            add(mus, epiano(chord, 0.35), t0 + beat * BEAT + BEAT / 2, 0.22, -0.25)
        # 마림바 멜로디
        for off, note in MELODY[b % 4]:
            add(mus, marimba(note), t0 + off * BEAT, 0.28, 0.25)
        if intro:
            for k, note in enumerate(chord):  # 인트로 아르페지오
                add(mus, marimba(note + 12, 0.4), t0 + k * BEAT / 2, 0.18, 0.1)
    # 엔딩: 마지막 화음 한 번 크게
    end_t = DUR - 1.4
    add(mus, epiano([48, 60, 64, 67, 72], 1.4) * 1.5, end_t, 0.35)
    add(mus, glock(84), end_t, 0.15)
    # LP판 잡음(종이 질감)
    crackle = (rng.random(N) < 0.0015) * rng.normal(0, 1, N)
    hiss = filt(rng.normal(0, 1, N), lo=3000, hi=8000) * 0.012
    mus += (filt(crackle, lo=1500) * 0.25 + hiss)[:, None]
    # 시작/끝 페이드
    fade = np.ones(N)
    fi = int(0.05 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fo = int(1.2 * SR)
    fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
    return mus * fade[:, None]


def sfx_track():
    sfx = np.zeros((N, 2))
    for s in mv.SCENES:
        st = s["start"]
        if s.get("kind") == "title":
            add(sfx, paper_pop(0.8), st + 0.02, 0.8)
            add(sfx, paper_pop(1.0), st + 0.55, 0.7, -0.2)
            add(sfx, paper_pop(1.3), st + 0.95, 0.6, 0.2)
            continue
        # 장면 전환 휙 (세 장의 시트)
        add(sfx, whoosh(1.0), st - 0.55, 0.55, 0.3)
        add(sfx, whoosh(0.8), st - 0.35, 0.35, -0.3)
        if not USE_FLOW:  # Flow 곡과는 음정이 부딪힐 수 있어 합성 BGM일 때만
            add(sfx, glock(84 + (mv.SCENES.index(s) % 3) * 2), st + 0.05, 0.12)
        add(sfx, paper_pop(0.8), st + 0.08, 0.75, 0.3)  # 사진 컷아웃
        for j in range(len(s["year"])):
            add(sfx, stamp(), st + 0.25 + j * 0.09, 0.5, -0.5 + j * 0.2)
        add(sfx, paper_pop(1.0), st + 0.77, 0.6, -0.3)   # 제목
        add(sfx, paper_pop(1.2), st + 1.02, 0.5, -0.3)   # 부제
        add(sfx, paper_pop(1.5), st + 1.37, 0.6, -0.2)   # 태그
    return sfx


def flow_music():
    """Flow Music 곡에서 30초를 편집: [본 구간] ⟶ 박자 맞춘 디졸브(크로스페이드) ⟶ [아웃트로]."""
    with wave.open(FLOW_WAV) as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels())
    a = a.astype(np.float64)[:, :2] / 32768
    beat = 60 / 121.82                      # 곡 17~40초 onset에 맞춘 템포
    offset = 17.00 - 4.0                    # 곡 17.00s(풀밴드 진입) ↔ 영상 4.0s(첫 장면 전환)
    hit_v = 4.0 + 42 * beat                 # 아웃트로 첫 타격이 놓일 박(영상 ≈24.69s)
    out_hit = 166.30                        # 곡의 아웃트로 첫 타격
    xf0, xf1 = hit_v - 2 * beat, hit_v + 2 * beat   # 디졸브 구간: 4박(영상 ≈23.7~25.7s)

    def take(song_t0, vid_t0, vid_t1):
        i0, j0, j1 = int(song_t0 * SR), int(vid_t0 * SR), int(vid_t1 * SR)
        return j0, a[i0:i0 + (j1 - j0)]

    def xfade_curve(n0, n1, out):
        """xf0~xf1 구간 equal-power 곡선 (out=True면 1→0, False면 0→1)."""
        t = np.clip((np.arange(n0, n1) / SR - xf0) / (xf1 - xf0), 0, 1)
        return np.cos(t * np.pi / 2) if out else np.sin(t * np.pi / 2)

    mus = np.zeros((N, 2))
    # 본 구간: 처음부터 디졸브 끝까지 재생, 디졸브 구간에서 서서히 사라진다
    j0, s1 = take(offset, 0.0, xf1)
    g1 = xfade_curve(j0, j0 + len(s1), out=True)
    fi = int(0.3 * SR)
    g1[:fi] *= np.linspace(0, 1, fi)
    mus[j0:j0 + len(s1)] += s1 * g1[:, None]

    # 아웃트로: 같은 박자 격자로 겹쳐 들어오며 서서히 커진다
    j0, s2 = take(out_hit - (hit_v - xf0), xf0, DUR)
    g2 = xfade_curve(j0, j0 + len(s2), out=False)
    fo = int(1.5 * SR)
    g2[-fo:] *= np.linspace(1, 0, fo) ** 1.5
    mus[j0:j0 + len(s2)] += s2 * g2[:, None]
    return mus / np.max(np.abs(mus))


def main():
    sfx = sfx_track()
    if USE_FLOW:
        mix = flow_music() * 0.85 + sfx * 0.45
    else:
        mix = compose() * 0.8 + sfx * 0.9
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # 부드러운 리미터
    mix *= 0.89 / np.max(np.abs(mix))       # -1 dBFS
    wav_path = os.path.join(HERE, "bgm.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print("saved", wav_path)

    video = os.path.join(HERE, "car_history_collage.mp4")
    out = os.path.join(HERE, "car_history_collage_music.mp4")
    subprocess.run([shutil.which("ffmpeg"), "-y", "-loglevel", "error", "-i", video, "-i", wav_path,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    print("saved", out)


if __name__ == "__main__":
    main()
