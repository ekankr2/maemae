"""
일일 매수 후보 스캐너

거래량 상위 종목을 스캔하여
풍선이론 (Balloon Theory) 전략 매수 조건에 맞는 종목을 찾아냅니다.

매수 조건:
1. 주가 1,000원 이상
2. 종가가 EMA60 위에 있음 (상승 추세)
3. 당일 거래량이 전일 거래량 대비 500% 이상 증가
4. 양봉이어야 함 (종가 > 시가)
5. 거래량이 50만개 이상
"""
import sys
sys.path.extend(['.'])

import kis_auth as ka
from examples_llm_stock.volume_rank.volume_rank import volume_rank
from examples_llm_stock.market_cap.market_cap import market_cap
from data_loader import load_stock_data
import pandas as pd
from datetime import datetime, timedelta


def calculate_ema(prices, period):
    """EMA 계산"""
    ema = sum(prices[:period]) / period
    multiplier = 2.0 / (period + 1)

    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def is_near_ema(price, ema_value, threshold=5.0):
    """주가가 EMA 근처인지 확인 (threshold % 이내)"""
    if ema_value == 0:
        return False
    diff_pct = abs((price - ema_value) / ema_value) * 100
    return diff_pct <= threshold


def get_ema_distance(price, ema_value):
    """주가와 EMA 사이 이격률 계산"""
    if ema_value == 0:
        return 999.0
    return ((price - ema_value) / ema_value) * 100


def scan_stock(code, name):
    """
    개별 종목 스캔 - 풍선이론 전략 조건

    매수 조건:
    1. 종가가 EMA60 위에 있음 (상승 추세)
    2. 주가가 1,000원 이상
    3. 당일 거래량이 전일 거래량 대비 500% 이상 증가
    4. 양봉이어야 함 (종가 > 시가)
    5. 거래량이 50만개 이상

    Returns:
        dict or None: 매수 조건 충족 시 종목 정보, 아니면 None
    """
    # ETF/ETN/SPAC/지수 제외 필터
    exclude_keywords = ['KODEX', 'TIGER', 'ARIRANG', 'KBSTAR', 'SMART',
                        '선물', '인버스', '레버리지', 'ETN', 'ETF', '스팩', 'SPAC',
                        '코스피', '코스닥', 'KOSPI', 'KOSDAQ']

    for keyword in exclude_keywords:
        if keyword in name:
            return None

    try:
        # 최근 데이터 로드 (EMA60 계산을 위해 최소 60일 필요)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")  # 약 6개월치면 충분

        df = load_stock_data(code, start_date, end_date, adjusted=True)

        if len(df) < 60:
            return None  # 데이터 부족 (최소 60일 필요)

        # 최소 2일치 데이터 필요 (전일 거래량 비교를 위해)
        if len(df) < 2:
            return None

        # 현재 데이터 (가장 최근 일봉)
        current_close = df['Close'].iloc[-1]
        current_open = df['Open'].iloc[-1]
        current_volume = df['Volume'].iloc[-1]

        # 전일 데이터
        prev_close = df['Close'].iloc[-2]
        prev_volume = df['Volume'].iloc[-2]

        # EMA60 계산
        closes = df['Close'].values
        ema60 = calculate_ema(closes, 60)

        # 조건 1: 종가가 EMA60 위에 있는지 확인
        if current_close <= ema60:
            return None

        # 조건 2: 주가가 1,000원 이상
        if current_close < 1000:
            return None

        # 조건 3: 양봉 확인 (종가 > 시가)
        if current_close <= current_open:
            return None

        # 조건 4: 전일 거래량이 0이면 계산 불가
        if prev_volume == 0:
            return None

        # 조건 5: 당일 거래량이 전일 거래량 대비 500% 이상 증가
        volume_ratio = current_volume / prev_volume
        if volume_ratio < 5.0:  # 500% = 5.0배
            return None

        # 조건 6: 거래량 절대값 확인 (50만개 이상)
        if current_volume < 500000:
            return None

        # EMA60 이격률 계산
        ema60_distance = get_ema_distance(current_close, ema60)

        # 모든 조건 충족!
        return {
            '종목코드': code,
            '종목명': name,
            '현재가': f"{current_close:,.0f}",
            'EMA60': f"{ema60:,.0f}",
            '이격률': f"{ema60_distance:+.2f}%",
            '거래량증가율': f"{volume_ratio:.2f}배",
            '전일거래량': f"{prev_volume:,.0f}",
            '당일거래량': f"{current_volume:,.0f}",
        }

    except Exception as e:
        print(f"  ✗ {name} ({code}) 오류: {e}")
        return None


def main():
    """일일 스캐너 실행"""
    print("=" * 80)
    print("풍선이론 (Balloon Theory) 일일 매수 후보 스캐너")
    print("=" * 80)

    # 1. KIS API 인증
    print("\n[1/4] KIS API 인증 중...")
    ka.auth(svr="prod")
    print("✓ 인증 완료")

    # 2. 거래량 상위 종목 리스트 가져오기 (여러 기준으로 조회해서 합치기)
    print("\n[2/4] 거래량 상위 종목 조회 중 (여러 기준 병합)...")

    # 2-1. 평균거래량 기준 (30개)
    print("  - 평균거래량 기준...")
    stocks_avg_volume = volume_rank(
        fid_cond_mrkt_div_code="J",
        fid_cond_scr_div_code="20171",
        fid_input_iscd="0000",
        fid_div_cls_code="0",
        fid_blng_cls_code="0",            # 0: 평균거래량
        fid_trgt_cls_code="111111111",
        fid_trgt_exls_cls_code="0000000000",
        fid_input_price_1="1000",         # 1000원 이상
        fid_input_price_2="",
        fid_vol_cnt="",
        fid_input_date_1=""
    )
    print(f"    {len(stocks_avg_volume)}개")

    # 2-2. 거래증가율 기준 (30개)
    print("  - 거래증가율 기준...")
    stocks_vol_increase = volume_rank(
        fid_cond_mrkt_div_code="J",
        fid_cond_scr_div_code="20171",
        fid_input_iscd="0000",
        fid_div_cls_code="0",
        fid_blng_cls_code="1",            # 1: 거래증가율
        fid_trgt_cls_code="111111111",
        fid_trgt_exls_cls_code="0000000000",
        fid_input_price_1="1000",
        fid_input_price_2="",
        fid_vol_cnt="",
        fid_input_date_1=""
    )
    print(f"    {len(stocks_vol_increase)}개")

    # 2-3. 거래금액순 기준 (30개)
    print("  - 거래금액순 기준...")
    stocks_amount = volume_rank(
        fid_cond_mrkt_div_code="J",
        fid_cond_scr_div_code="20171",
        fid_input_iscd="0000",
        fid_div_cls_code="0",
        fid_blng_cls_code="3",            # 3: 거래금액순
        fid_trgt_cls_code="111111111",
        fid_trgt_exls_cls_code="0000000000",
        fid_input_price_1="1000",
        fid_input_price_2="",
        fid_vol_cnt="",
        fid_input_date_1=""
    )
    print(f"    {len(stocks_amount)}개")

    # 2-4. 코스피 시총순 (30개)
    print("  - 코스피 시총순...")
    stocks_kospi_cap = market_cap(
        fid_input_price_2="",
        fid_cond_mrkt_div_code="J",
        fid_cond_scr_div_code="20174",
        fid_div_cls_code="0",
        fid_input_iscd="0001",            # 0001: 코스피
        fid_trgt_cls_code="0",
        fid_trgt_exls_cls_code="0",
        fid_input_price_1="1000",
        fid_vol_cnt=""
    )
    print(f"    {len(stocks_kospi_cap)}개")

    # 2-5. 코스닥 시총순 (30개)
    print("  - 코스닥 시총순...")
    stocks_kosdaq_cap = market_cap(
        fid_input_price_2="",
        fid_cond_mrkt_div_code="J",
        fid_cond_scr_div_code="20174",
        fid_div_cls_code="0",
        fid_input_iscd="1001",            # 1001: 코스닥
        fid_trgt_cls_code="0",
        fid_trgt_exls_cls_code="0",
        fid_input_price_1="1000",
        fid_vol_cnt=""
    )
    print(f"    {len(stocks_kosdaq_cap)}개")

    # 모든 결과 합치기
    all_stocks = pd.concat([
        stocks_avg_volume,
        stocks_vol_increase,
        stocks_amount,
        stocks_kospi_cap,
        stocks_kosdaq_cap
    ], ignore_index=True)

    # 중복 제거 (종목코드 기준)
    all_stocks = all_stocks.drop_duplicates(subset=['mksc_shrn_iscd'], keep='first')

    print(f"✓ 총 {len(all_stocks)}개 종목 로드 완료 (중복 제거 후)")

    # 3. 각 종목 스캔
    print(f"\n[3/4] {len(all_stocks)}개 종목 스캔 중...")
    print("  (EMA60 위 + 거래량 500% 증가 + 양봉)")
    print()

    candidates = []

    for i, (idx, row) in enumerate(all_stocks.iterrows(), start=1):
        code = row['mksc_shrn_iscd']
        name = row['hts_kor_isnm']

        print(f"  [{i}/{len(all_stocks)}] {name} ({code})... ", end="", flush=True)

        result = scan_stock(code, name)

        if result:
            print("✓ 매수 후보!")
            candidates.append(result)
        else:
            print("✗")

    # 4. 결과 출력
    print("\n" + "=" * 80)
    print(f"[4/4] 스캔 완료! 매수 후보: {len(candidates)}개")
    print("=" * 80)

    if candidates:
        df_candidates = pd.DataFrame(candidates)
        print("\n매수 후보 종목:")
        print(df_candidates.to_string(index=False))

        # CSV 저장
        today = datetime.now().strftime("%Y%m%d")
        filename = f"buy_candidates_{today}.csv"
        df_candidates.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ 결과 저장: {filename}")
    else:
        print("\n매수 조건을 충족하는 종목이 없습니다.")

    return candidates


if __name__ == "__main__":
    try:
        candidates = main()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()