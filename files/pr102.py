"""
KOBIS 월간(7월) 누적 박스오피스 통계
-------------------------------------------------
KOBIS는 '월간' API가 따로 없어서, 하루하루(일별 API)를 31번 반복 호출한 뒤
영화별로 관객수를 계속 더해서 우리가 직접 '월간 집계'를 만듭니다.
"""

import requests
import csv
import os
import time
from datetime import datetime, timedelta

KOBIS_KEY = "여기에_발급받은_KOBIS_인증키_입력"
url = "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"

# 1) 7월 1일부터 31일까지 날짜 목록 만들기
start_date = datetime(2026, 7, 1)
end_date = datetime(2026, 7, 31)

date_list = []
current = start_date
while current <= end_date:
    date_list.append(current.strftime("%Y%m%d"))
    current += timedelta(days=1)

print(f"조회할 날짜 수: {len(date_list)}일\n")

# 2) 영화별 누적 관객수·매출액을 저장할 '딕셔너리' 준비
#    형태: {"영화제목": {"audience": 누적관객수, "sales": 누적매출액}}
movie_totals = {}

# 3) 날짜 하나씩(31번) 반복하면서 그날의 박스오피스(10개)를 또 반복 처리
for i, date_str in enumerate(date_list):
    params = {"key": KOBIS_KEY, "targetDt": date_str}
    response = requests.get(url, params=params)
    data = response.json()

    daily_list = data["boxOfficeResult"]["dailyBoxOfficeList"]

    for movie in daily_list:
        title = movie["movieNm"]
        audience = int(movie["audiCnt"])   # 문자열 -> 숫자로 변환
        sales = int(movie["salesAmt"])     # 문자열 -> 숫자로 변환

        # 이미 등장한 영화면 더하고, 처음 등장이면 새로 등록
        if title in movie_totals:
            movie_totals[title]["audience"] += audience
            movie_totals[title]["sales"] += sales
        else:
            movie_totals[title] = {"audience": audience, "sales": sales}

    # API 서버에 너무 빠르게 연속 요청하지 않도록 짧게 쉬어줍니다 (매너 있는 크롤링/API 사용)
    time.sleep(0.2)
    print(f"[{i+1}/{len(date_list)}] {date_str} 처리 완료")

# 4) 전체 누적 관객수·매출액 합계 구하기
total_audience = sum(v["audience"] for v in movie_totals.values())
total_sales = sum(v["sales"] for v in movie_totals.values())

# 5) 관객수 많은 순으로 정렬해서 TOP 10 뽑기
top10 = sorted(movie_totals.items(), key=lambda x: x[1]["audience"], reverse=True)[:10]

print(f"\n=== 2026년 7월 총 누적 관객수: {total_audience:,}명 / 총 매출액: {total_sales:,}원 ===\n")
print("=== 7월 박스오피스 TOP 10 (월간 누적 기준) ===\n")
for rank, (title, stats) in enumerate(top10, start=1):
    print(f"{rank}위 | {title} | 관객수 {stats['audience']:,}명 | 매출액 {stats['sales']:,}원")

# 6) CSV로 저장 (스크립트 파일과 같은 폴더에)
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_filename = os.path.join(script_dir, "boxoffice_2026_07_monthly.csv")

with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["순위", "영화제목", "7월 누적관객수", "7월 누적매출액"])
    for rank, (title, stats) in enumerate(top10, start=1):
        writer.writerow([rank, title, stats["audience"], stats["sales"]])

print(f"\n✅ 저장 완료! 파일 위치: {csv_filename}")
