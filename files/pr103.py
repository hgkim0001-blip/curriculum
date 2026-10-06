"""
KOBIS(영화진흥위원회) 일일 박스오피스 순위 가져오기
-------------------------------------------------
1. KOBIS_KEY 자리에 본인이 발급받은 키를 넣으세요.
2. TARGET_DATE는 조회할 날짜(YYYYMMDD)입니다. 비워두면 어제 날짜로 자동 설정됩니다.
   (KOBIS는 보통 '어제까지'의 집계만 제공합니다.)
"""

import requests
from datetime import datetime, timedelta

# 1) 여기에 발급받은 키를 넣으세요
KOBIS_KEY = "여기에_발급받은_KOBIS_인증키_입력"

# 2) 조회할 날짜 (직접 지정하려면 "20260814" 처럼 문자열로)
TARGET_DATE = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

# 3) API 요청 주소 만들기
url = "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {
    "key": KOBIS_KEY,
    "targetDt": TARGET_DATE,
}

# 4) 요청 보내고 결과 받기
response = requests.get(url, params=params)
data = response.json()  # JSON 문자열을 파이썬 딕셔너리로 변환

# 5) 필요한 부분만 꺼내기
box_office_list = data["boxOfficeResult"]["dailyBoxOfficeList"]

print(f"=== {TARGET_DATE} 일일 박스오피스 TOP 10 ===\n")

for movie in box_office_list:
    rank = movie["rank"]                # 순위
    title = movie["movieNm"]            # 영화 제목
    audience_today = movie["audiCnt"]   # 당일 관객수
    audience_total = movie["audiAcc"]   # 누적 관객수
    sales_today = movie["salesAmt"]     # 당일 매출액

    print(f"{rank}위 | {title}")
    print(f"   당일 관객수: {int(audience_today):,}명")
    print(f"   누적 관객수: {int(audience_total):,}명")
    print(f"   당일 매출액: {int(sales_today):,}원")
    print("-" * 40)

# 6) 엑셀/구글시트에 넣기 좋게 CSV로 저장
import csv
import os

# 실행 위치와 상관없이, 항상 이 코드 파일이 있는 폴더에 저장되도록 경로를 고정합니다.
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_filename = os.path.join(script_dir, f"boxoffice_{TARGET_DATE}.csv")

with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
    # encoding="utf-8-sig"로 저장해야 엑셀에서 열 때 한글이 깨지지 않습니다.
    writer = csv.writer(f)
    writer.writerow(["순위", "영화제목", "당일관객수", "누적관객수", "당일매출액"])
    for movie in box_office_list:
        writer.writerow([
            movie["rank"], movie["movieNm"],
            movie["audiCnt"], movie["audiAcc"], movie["salesAmt"]
        ])

print(f"\n✅ 저장 완료! 파일 위치: {csv_filename}")
