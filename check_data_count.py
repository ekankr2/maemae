"""
1시간봉 데이터 개수 확인 스크립트
"""
import kis_auth as ka
from data_loader import load_stock_data

# ETF 정보
ETF_INFO = {
    "233740": "코스닥150레버리지",
    "251340": "코스닥150선물인버스",
    "122630": "레버리지",
    "252670": "200선물인버스2X"
}

print("=" * 80)
print("1시간봉 데이터 개수 확인")
print("=" * 80)

# KIS API 인증
print("\n[1/2] KIS API 인증 중...")
ka.auth(svr="prod")
print("✓ 인증 완료")

# 백테스팅 파라미터
start_date = "20200101"
end_date = "20241231"
period = "60"  # 1시간봉

print(f"\n[2/2] 데이터 로드 확인:")
print(f"  기간: {start_date} ~ {end_date}")
print(f"  봉 주기: 1시간봉")
print()

for etf_code, etf_name in ETF_INFO.items():
    print(f"[{etf_code}] {etf_name}")
    try:
        df = load_stock_data(
            stock_code=etf_code,
            start_date=start_date,
            end_date=end_date,
            adjusted=True,
            period=period
        )

        if not df.empty:
            print(f"  ✓ 총 {len(df)}개 봉 데이터 로드")
            print(f"  시작일: {df.index[0]}")
            print(f"  종료일: {df.index[-1]}")

            # 년도별 개수
            df['year'] = df.index.year
            yearly_counts = df.groupby('year').size()
            print(f"  년도별 개수:")
            for year, count in yearly_counts.items():
                print(f"    {year}년: {count}개")
        else:
            print(f"  ✗ 데이터가 비어있음")
    except Exception as e:
        print(f"  ✗ 오류: {e}")

    print()

print("=" * 80)
print("완료!")
print("=" * 80)