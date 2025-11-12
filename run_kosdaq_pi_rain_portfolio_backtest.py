"""
코스닥피 레인 전략 - 모멘텀 스코어 기반 포트폴리오 백테스팅 (vectorbt)

4개 ETF 포트폴리오 + 모멘텀 기반 비중 조절:
- KODEX 코스닥150레버리지 (233740) - 비중 조절 대상
- KODEX 코스닥150선물인버스 (251340) - 비중 조절 대상
- KODEX 레버리지 (122630) - 고정 비중
- KODEX 200선물인버스2X (252670) - 고정 비중

모멘텀 스코어로 코스닥 레버리지/인버스 비중 조절 (1.3배/0.7배)
"""
import pandas as pd
import numpy as np
import vectorbt as vbt
import kis_auth as ka
from data_loader import load_stock_data
from strategies.kosdaq_pi_rain_strategy import (
    check_kosdaq150_lev_buy_signal,
    check_kosdaq150_lev_sell_signal,
    check_kosdaq150_inv_buy_signal,
    check_kosdaq150_inv_sell_signal,
    check_kospi200_lev_buy_signal,
    check_kospi200_lev_sell_signal,
    check_kospi200_inv2x_buy_signal,
    check_kospi200_inv2x_sell_signal,
    calculate_momentum_score1,
    calculate_momentum_score2,
    calculate_weight_adjustment
)


# ETF 정보
ETF_CODES = {
    "kosdaq_lev": "233740",      # 코스닥150레버리지
    "kosdaq_inv": "251340",      # 코스닥150선물인버스
    "kospi_lev": "122630",       # 레버리지
    "kospi_inv": "252670"        # 200선물인버스2X
}

ETF_NAMES = {
    "233740": "코스닥150레버리지",
    "251340": "코스닥150선물인버스",
    "122630": "레버리지",
    "252670": "200선물인버스2X"
}


def load_etf_data(start_date, end_date):
    """
    4개 ETF 데이터 로드

    Returns:
        dict: {etf_name: DataFrame}
    """
    print("\n[데이터 로드 중...]")
    data = {}

    for name, code in ETF_CODES.items():
        print(f"  {ETF_NAMES[code]} ({code}) 로드 중...")
        df = load_stock_data(
            stock_code=code,
            start_date=start_date,
            end_date=end_date,
            adjusted=True
        )

        if df.empty:
            raise ValueError(f"{code} 데이터를 불러올 수 없습니다.")

        data[name] = df
        print(f"    ✓ {len(df)}일 데이터 로드 완료")

    return data


def align_dataframes(data_dict):
    """
    모든 DataFrame의 인덱스(날짜)를 동일하게 맞춤

    Returns:
        dict: 정렬된 데이터
    """
    # 공통 날짜 찾기
    common_dates = None
    for df in data_dict.values():
        if common_dates is None:
            common_dates = set(df.index)
        else:
            common_dates = common_dates.intersection(set(df.index))

    common_dates = sorted(list(common_dates))

    print(f"\n[데이터 정렬]")
    print(f"  공통 날짜 수: {len(common_dates)}일")

    # 공통 날짜로 필터링
    aligned_data = {}
    for name, df in data_dict.items():
        aligned_data[name] = df.loc[common_dates]

    return aligned_data


def generate_signals(data):
    """
    각 ETF의 매수/매도 신호 생성

    Returns:
        dict: {etf_name: {'entries': Series, 'exits': Series}}
    """
    print("\n[매수/매도 신호 생성 중...]")

    signals = {}

    # 코스닥150레버리지
    print("  코스닥150레버리지 신호 생성 중...")
    kosdaq_lev_entries = []
    kosdaq_lev_exits = []

    for idx in range(len(data['kosdaq_lev'])):
        if idx < 60:  # 최소 데이터 필요
            kosdaq_lev_entries.append(False)
            kosdaq_lev_exits.append(False)
            continue

        buy = check_kosdaq150_lev_buy_signal(data['kosdaq_lev'], idx)
        sell = check_kosdaq150_lev_sell_signal(data['kosdaq_lev'], idx)

        kosdaq_lev_entries.append(buy)
        kosdaq_lev_exits.append(sell)

    signals['kosdaq_lev'] = {
        'entries': pd.Series(kosdaq_lev_entries, index=data['kosdaq_lev'].index),
        'exits': pd.Series(kosdaq_lev_exits, index=data['kosdaq_lev'].index)
    }
    print(f"    ✓ 매수 신호: {sum(kosdaq_lev_entries)}회, 매도 신호: {sum(kosdaq_lev_exits)}회")

    # 코스닥150선물인버스
    print("  코스닥150선물인버스 신호 생성 중...")
    kosdaq_inv_entries = []
    kosdaq_inv_exits = []

    for idx in range(len(data['kosdaq_inv'])):
        if idx < 21:
            kosdaq_inv_entries.append(False)
            kosdaq_inv_exits.append(False)
            continue

        buy = check_kosdaq150_inv_buy_signal(data['kosdaq_inv'], idx)
        sell = check_kosdaq150_inv_sell_signal(data['kosdaq_inv'], idx)

        kosdaq_inv_entries.append(buy)
        kosdaq_inv_exits.append(sell)

    signals['kosdaq_inv'] = {
        'entries': pd.Series(kosdaq_inv_entries, index=data['kosdaq_inv'].index),
        'exits': pd.Series(kosdaq_inv_exits, index=data['kosdaq_inv'].index)
    }
    print(f"    ✓ 매수 신호: {sum(kosdaq_inv_entries)}회, 매도 신호: {sum(kosdaq_inv_exits)}회")

    # 레버리지
    print("  레버리지 신호 생성 중...")
    kospi_lev_entries = []
    kospi_lev_exits = []

    for idx in range(len(data['kospi_lev'])):
        if idx < 22:
            kospi_lev_entries.append(False)
            kospi_lev_exits.append(False)
            continue

        buy = check_kospi200_lev_buy_signal(data['kospi_lev'], idx)
        sell = check_kospi200_lev_sell_signal(data['kospi_lev'], idx)

        kospi_lev_entries.append(buy)
        kospi_lev_exits.append(sell)

    signals['kospi_lev'] = {
        'entries': pd.Series(kospi_lev_entries, index=data['kospi_lev'].index),
        'exits': pd.Series(kospi_lev_exits, index=data['kospi_lev'].index)
    }
    print(f"    ✓ 매수 신호: {sum(kospi_lev_entries)}회, 매도 신호: {sum(kospi_lev_exits)}회")

    # 200선물인버스2X
    print("  200선물인버스2X 신호 생성 중...")
    kospi_inv_entries = []
    kospi_inv_exits = []

    for idx in range(len(data['kospi_inv'])):
        if idx < 77:
            kospi_inv_entries.append(False)
            kospi_inv_exits.append(False)
            continue

        buy = check_kospi200_inv2x_buy_signal(data['kospi_inv'], idx)
        sell = check_kospi200_inv2x_sell_signal(data['kospi_inv'], idx)

        kospi_inv_entries.append(buy)
        kospi_inv_exits.append(sell)

    signals['kospi_inv'] = {
        'entries': pd.Series(kospi_inv_entries, index=data['kospi_inv'].index),
        'exits': pd.Series(kospi_inv_exits, index=data['kospi_inv'].index)
    }
    print(f"    ✓ 매수 신호: {sum(kospi_inv_entries)}회, 매도 신호: {sum(kospi_inv_exits)}회")

    return signals


def calculate_dynamic_weights(data):
    """
    모멘텀 스코어 기반 동적 비중 계산

    Returns:
        DataFrame: 각 ETF의 날짜별 비중 (4개 컬럼)
    """
    print("\n[모멘텀 스코어 기반 비중 계산 중...]")

    dates = data['kosdaq_lev'].index
    weights = []

    for idx in range(len(dates)):
        if idx < 101:  # 모멘텀 스코어 계산 불가
            # 기본 비중: 각 1/4
            weights.append({
                'kosdaq_lev': 0.25,
                'kosdaq_inv': 0.25,
                'kospi_lev': 0.25,
                'kospi_inv': 0.25
            })
            continue

        try:
            # 코스닥 레버리지 모멘텀 스코어
            lev_score1 = calculate_momentum_score1(data['kosdaq_lev'], idx)
            lev_score2 = calculate_momentum_score2(data['kosdaq_lev'], idx)

            # 코스닥 인버스 모멘텀 스코어
            inv_score1 = calculate_momentum_score1(data['kosdaq_inv'], idx)
            inv_score2 = calculate_momentum_score2(data['kosdaq_inv'], idx)

            # 비중 조절
            lev_weight, inv_weight = calculate_weight_adjustment(
                lev_score1, lev_score2,
                inv_score1, inv_score2
            )

            # 코스닥 2개 ETF의 기본 비중 = 0.5 (전체의 절반)
            # 코스피 2개 ETF의 기본 비중 = 0.5 (전체의 절반)
            kosdaq_base = 0.5
            kospi_base = 0.5

            # 코스닥 레버리지/인버스 비중 조절
            # lev_weight + inv_weight = 2.0 (1.3 + 0.7)
            # 정규화: 합이 1.0이 되도록
            total_kosdaq_weight = lev_weight + inv_weight
            norm_lev = lev_weight / total_kosdaq_weight
            norm_inv = inv_weight / total_kosdaq_weight

            weights.append({
                'kosdaq_lev': kosdaq_base * norm_lev,   # 0.5 * (1.3/2.0) = 0.325 or 0.5 * (0.7/2.0) = 0.175
                'kosdaq_inv': kosdaq_base * norm_inv,   # 0.5 * (0.7/2.0) = 0.175 or 0.5 * (1.3/2.0) = 0.325
                'kospi_lev': kospi_base * 0.5,          # 0.25 (고정)
                'kospi_inv': kospi_base * 0.5           # 0.25 (고정)
            })

        except (ValueError, Exception) as e:
            # 계산 실패 시 기본 비중
            weights.append({
                'kosdaq_lev': 0.25,
                'kosdaq_inv': 0.25,
                'kospi_lev': 0.25,
                'kospi_inv': 0.25
            })

    weights_df = pd.DataFrame(weights, index=dates)

    # 비중 변경 횟수 확인
    kosdaq_lev_changes = (weights_df['kosdaq_lev'].diff() != 0).sum()
    print(f"  ✓ 코스닥 레버리지 비중 변경: {kosdaq_lev_changes}회")
    print(f"  ✓ 비중 범위: {weights_df['kosdaq_lev'].min():.3f} ~ {weights_df['kosdaq_lev'].max():.3f}")

    return weights_df


def run_portfolio_backtest(data, signals, weights, init_cash=10_000_000, fees=0.0015):
    """
    vectorbt를 사용한 포트폴리오 백테스팅

    Args:
        data: ETF 데이터
        signals: 매수/매도 신호
        weights: 동적 비중
        init_cash: 초기 자본
        fees: 수수료

    Returns:
        Portfolio 객체
    """
    print("\n[포트폴리오 백테스팅 실행 중...]")

    # 종가 데이터 통합
    close_prices = pd.DataFrame({
        'kosdaq_lev': data['kosdaq_lev']['Close'],
        'kosdaq_inv': data['kosdaq_inv']['Close'],
        'kospi_lev': data['kospi_lev']['Close'],
        'kospi_inv': data['kospi_inv']['Close']
    })

    # 매수/매도 신호 통합
    entries = pd.DataFrame({
        'kosdaq_lev': signals['kosdaq_lev']['entries'],
        'kosdaq_inv': signals['kosdaq_inv']['entries'],
        'kospi_lev': signals['kospi_lev']['entries'],
        'kospi_inv': signals['kospi_inv']['entries']
    })

    exits = pd.DataFrame({
        'kosdaq_lev': signals['kosdaq_lev']['exits'],
        'kosdaq_inv': signals['kosdaq_inv']['exits'],
        'kospi_lev': signals['kospi_lev']['exits'],
        'kospi_inv': signals['kospi_inv']['exits']
    })

    # vectorbt 포트폴리오 백테스팅
    # size_type='percent': 매수 신호 발생 시 포트폴리오의 X% 투자
    pf = vbt.Portfolio.from_signals(
        close=close_prices,
        entries=entries,
        exits=exits,
        size=weights * 100,  # 퍼센트로 변환 (0.25 → 25%)
        size_type='percent',
        init_cash=init_cash,
        fees=fees,
        freq='D'
    )

    print("  ✓ 백테스팅 완료")

    return pf


def print_results(pf):
    """
    백테스팅 결과 출력

    Args:
        pf: vectorbt Portfolio 객체
    """
    print("\n" + "=" * 80)
    print("포트폴리오 백테스팅 결과")
    print("=" * 80)

    stats = pf.stats()

    print(f"\n기본 정보:")
    print(f"  시작일:               {stats.get('Start', 'N/A')}")
    print(f"  종료일:               {stats.get('End', 'N/A')}")
    print(f"  기간:                 {stats.get('Period', 'N/A')}")

    print(f"\n수익 정보:")
    print(f"  초기 자본:            {stats.get('Start Value', 0):>15,.0f} 원")
    print(f"  최종 자산:            {stats.get('End Value', 0):>15,.0f} 원")
    print(f"  총 수익률:            {stats.get('Total Return [%]', 0):>15.2f} %")
    print(f"  최대 낙폭 (MDD):      {stats.get('Max Drawdown [%]', 0):>15.2f} %")

    print(f"\n거래 정보:")
    print(f"  총 거래 횟수:         {int(stats.get('Total Trades', 0)):>15} 회")
    print(f"  승률:                 {stats.get('Win Rate [%]', 0):>15.2f} %")
    print(f"  평균 거래 수익률:     {stats.get('Avg Winning Trade [%]', 0):>15.2f} %")
    print(f"  평균 거래 손실률:     {stats.get('Avg Losing Trade [%]', 0):>15.2f} %")

    print(f"\n성과 지표:")
    print(f"  샤프 비율:            {stats.get('Sharpe Ratio', 0):>15.2f}")
    print(f"  Calmar 비율:          {stats.get('Calmar Ratio', 0):>15.2f}")

    print("\n" + "=" * 80)


def main():
    """
    메인 함수
    """
    print("=" * 80)
    print("코스닥피 레인 - 모멘텀 스코어 기반 포트폴리오 백테스팅")
    print("=" * 80)

    # 1. KIS API 인증
    print("\n[1/6] KIS API 인증 중...")
    ka.auth(svr="prod")
    print("✓ 인증 완료")

    # 2. 백테스팅 파라미터
    start_date = "20200101"
    end_date = "20241231"
    init_cash = 10_000_000
    fees = 0.0015

    print(f"\n[2/6] 백테스팅 설정:")
    print(f"  기간: {start_date} ~ {end_date}")
    print(f"  초기 자본: {init_cash:,}원")
    print(f"  수수료: {fees * 100}%")

    # 3. 데이터 로드
    data = load_etf_data(start_date, end_date)

    # 4. 데이터 정렬
    print("\n[3/6] 데이터 정렬 중...")
    data = align_dataframes(data)

    # 5. 신호 생성
    print("\n[4/6] 매수/매도 신호 생성")
    signals = generate_signals(data)

    # 6. 동적 비중 계산
    print("\n[5/6] 모멘텀 기반 비중 계산")
    weights = calculate_dynamic_weights(data)

    # 7. 포트폴리오 백테스팅
    print("\n[6/6] 포트폴리오 백테스팅")
    pf = run_portfolio_backtest(data, signals, weights, init_cash, fees)

    # 8. 결과 출력
    print_results(pf)

    # 9. 차트 저장
    print("\n[차트 저장]")
    try:
        import os
        os.makedirs("charts/portfolio", exist_ok=True)

        # 포트폴리오 수익률 곡선 저장
        fig = pf.plot()
        fig.write_html("charts/portfolio/kosdaq_pi_rain_portfolio.html")
        print("  ✓ 포트폴리오 차트: charts/portfolio/kosdaq_pi_rain_portfolio.html")
    except Exception as e:
        print(f"  ✗ 차트 저장 실패: {e}")

    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)

    return pf


if __name__ == "__main__":
    try:
        pf = main()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()