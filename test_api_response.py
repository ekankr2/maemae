"""
KIS API 1시간봉 응답 데이터 확인
"""
import kis_auth as ka
from examples_llm_stock.inquire_daily_itemchartprice.inquire_daily_itemchartprice import inquire_daily_itemchartprice

# KIS API 인증
print("KIS API 인증 중...")
ka.auth(svr="prod")
print("✓ 인증 완료\n")

# 1시간봉 데이터 요청
print("=" * 80)
print("1시간봉 데이터 요청")
print("=" * 80)

stock_code = "233740"  # 코스닥150레버리지
start_date = "20241220"
end_date = "20241230"

print(f"종목: {stock_code}")
print(f"기간: {start_date} ~ {end_date}")
print(f"주기: 60분봉\n")

_, df = inquire_daily_itemchartprice(
    env_dv="real",
    fid_cond_mrkt_div_code="J",
    fid_input_iscd=stock_code,
    fid_input_date_1=start_date,
    fid_input_date_2=end_date,
    fid_period_div_code="60",  # 1시간봉
    fid_org_adj_prc="0"
)

print("=" * 80)
print("반환된 데이터:")
print("=" * 80)
print(f"총 {len(df)}개 데이터\n")

print("컬럼 목록:")
print(df.columns.tolist())
print()

print("처음 5개 데이터:")
print(df.head(10))
print()

print("=" * 80)
print("일봉 데이터 요청 (비교)")
print("=" * 80)

_, df_daily = inquire_daily_itemchartprice(
    env_dv="real",
    fid_cond_mrkt_div_code="J",
    fid_input_iscd=stock_code,
    fid_input_date_1=start_date,
    fid_input_date_2=end_date,
    fid_period_div_code="D",  # 일봉
    fid_org_adj_prc="0"
)

print(f"총 {len(df_daily)}개 데이터\n")
print("컬럼 목록:")
print(df_daily.columns.tolist())
print()

print("처음 5개 데이터:")
print(df_daily.head(10))