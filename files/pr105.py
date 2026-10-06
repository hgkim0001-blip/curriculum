"""
파이썬 기반 자동 팩트체킹 데모
-------------------------------------------------
시나리오: AI가 7월 박스오피스에 대한 기사를 하나 썼습니다.
그 기사 안에 나온 숫자가, 우리가 실제로 수집한 정답 데이터(CSV/엑셀)와 맞는지
자동으로 대조해서 "이 문장은 사실과 일치/불일치"를 판정합니다.
"""

import pandas as pd
import re

# 1) "정답지" 역할을 할 실제 데이터를 불러옵니다
#    (오늘 실습에서 만든 boxoffice_2026_07_monthly.csv 와 같은 파일)
ground_truth = pd.read_csv("boxoffice_2026_07_monthly.csv")
print("=== 정답 데이터 ===")
print(ground_truth)

# 2) AI가 썼다고 가정한 기사 텍스트 (실제로는 ChatGPT API가 생성한 결과가 들어갑니다)
ai_generated_article = """
2026년 7월 극장가는 '호프'가 휩쓸었다. 호프는 누적 관객수 385만 명을 동원하며
압도적 1위를 차지했다. 2위는 스파이더맨: 브랜드 뉴 데이로, 166만 명을 모았다.
3위 토이 스토리 5는 120만 명의 관객을 불러들였다.
"""

# 3) 기사 문장 속에서 "검증 가능한 사실"(숫자+단위)을 정규식으로 뽑아냅니다
#    패턴: "숫자(만 명)" 형태를 찾습니다.
pattern = r"(\d+)만\s*명"
claims_in_article = re.findall(pattern, ai_generated_article)
print(f"\n기사에서 발견한 관객수 주장(만 명 단위): {claims_in_article}")

# 4) 기사에 등장한 영화 제목도 함께 뽑아서, 정답지의 실제 값과 짝지어 비교합니다
print("\n=== 팩트체크 결과 ===")
for _, row in ground_truth.iterrows():
    title = row["영화제목"]
    actual_audience_manmyeong = round(row["7월 누적관객수"] / 10000)  # 만 명 단위로 환산

    if title in ai_generated_article:
        # 기사 안에서 이 영화 제목 근처에 있는 숫자를 찾아 비교
        # (간단한 데모이므로, 실제로는 문장 단위로 더 정교하게 분리해야 합니다)
        match_found = str(actual_audience_manmyeong) in claims_in_article

        status = "✅ 일치" if match_found else "⚠️ 불일치 (확인 필요)"
        print(f"{title}: 기사 주장 대조 → 실제값 {actual_audience_manmyeong}만 명 | {status}")
    else:
        print(f"{title}: 기사에 언급되지 않음 (대조 생략)")
