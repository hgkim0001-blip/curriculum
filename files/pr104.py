"""
Matplotlib · Seaborn으로 7월 박스오피스 TOP10 시각화
-------------------------------------------------
엑셀 차트와 하는 일은 같지만(막대그래프), 코드로 그리는 방식입니다.
코드로 그리면 좋은 점: 데이터가 바뀌어도 코드를 다시 실행만 하면 그래프가 자동 갱신됩니다.

[한글 폰트 관련 안내]
전역 설정(rcParams)으로 폰트를 지정하면 컴퓨터마다 인식이 달라 깨지는 경우가 있어서,
이 코드는 글자가 들어가는 자리마다 폰트를 직접 못박아 넣는(fontproperties) 방식을 씁니다.
이 방식은 rcParams 인식 여부와 상관없이 항상 적용됩니다.
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import os

# 1) 한글 폰트 파일 경로를 직접 지정합니다.
#    윈도우: 맑은 고딕(malgun.ttf) / 맥: 애플고딕(AppleGothic.ttf)
WINDOWS_FONT = r"C:\Windows\Fonts\malgun.ttf"
MAC_FONT = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

if os.path.exists(WINDOWS_FONT):
    font_path = WINDOWS_FONT
elif os.path.exists(MAC_FONT):
    font_path = MAC_FONT
else:
    raise FileNotFoundError(
        "한글 폰트 파일을 찾지 못했습니다. font_path 변수에 본인 컴퓨터의 폰트 파일 경로를 직접 입력해주세요."
    )

kfont = fm.FontProperties(fname=font_path)  # 이 객체를 글자 넣는 곳마다 붙여줄 겁니다.
print(f"사용할 폰트 파일: {font_path}")

plt.rcParams["axes.unicode_minus"] = False   # 마이너스(-) 기호 깨짐 방지

# 2) 7월 실습에서 뽑았던 TOP10 데이터를 그대로 사용
titles = ["호프", "스파이더맨: 브랜드 뉴 데이", "토이 스토리 5", "눈동자", "모아나",
          "미니언즈 & 몬스터즈", "다윗", "군체", "마티 슈프림", "와일드 씽"]
audiences = [3855696, 1660405, 1190688, 1149351, 973831,
             664900, 231811, 207523, 123648, 87028]

# 3) Seaborn 스타일 적용 (배경, 격자선 등 디자인)
sns.set_style("whitegrid")

# 4) 그래프 그리기
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(titles, audiences, color=sns.color_palette("Blues_r", len(titles)))
ax.invert_yaxis()  # 1위가 맨 위로 오도록 뒤집기

# 5) 제목·축 이름에 한글 폰트를 직접 지정 (fontproperties=kfont)
ax.set_title("2026년 7월 박스오피스 TOP10 (누적 관객수)", fontsize=14, pad=15, fontproperties=kfont)
ax.set_xlabel("누적 관객수 (명)", fontproperties=kfont)

# 6) 영화 제목(y축 눈금 글자)에도 한글 폰트 직접 지정
ax.set_yticklabels(titles, fontproperties=kfont)

# 7) 막대 끝에 숫자 표시 (숫자는 한글이 아니라서 폰트 지정 없이도 괜찮습니다)
for bar, value in zip(bars, audiences):
    ax.text(value + 30000, bar.get_y() + bar.get_height() / 2,
             f"{value:,}", va="center", fontsize=9)

plt.tight_layout()
plt.savefig("july_boxoffice_chart.png", dpi=150)
plt.show()

print("✅ july_boxoffice_chart.png 로 저장 완료!")
