"""
코스닥피 레인 전략 백테스팅 실행 스크립트

4개 ETF 포트폴리오 전략:
- KODEX 코스닥150레버리지 (233740)
- KODEX 코스닥150선물인버스 (251340)
- KODEX 레버리지 (122630)
- KODEX 200선물인버스2X (252670)

각 ETF는 1/4 비중으로 운용
"""
import sys
import os
import pandas as pd
import logging
from datetime import datetime
from backtesting import Backtest
import kis_auth as ka
from data_loader import load_stock_data
from strategies.kosdaq_pi_rain_strategy import (
    Kosdaq150LevStrategy,
    Kosdaq150InvStrategy,
    Kospi200LevStrategy,
    Kospi200Inv2xStrategy,
    calculate_momentum_score1,
    calculate_momentum_score2,
    calculate_weight_adjustment
)

logging.getLogger('examples_llm_stock.search_stock_info.search_stock_info').setLevel(logging.WARNING)


# ETF 정보
ETF_INFO = {
    "233740": {"name": "코스닥150레버리지", "strategy": Kosdaq150LevStrategy},
    "251340": {"name": "코스닥150선물인버스", "strategy": Kosdaq150InvStrategy},
    "122630": {"name": "레버리지", "strategy": Kospi200LevStrategy},
    "252670": {"name": "200선물인버스2X", "strategy": Kospi200Inv2xStrategy}
}


def safe_float(value, default=0.0):
    """NaN 값을 안전하게 처리하는 헬퍼 함수"""
    if value is None:
        return default
    try:
        val = float(value)
        if val != val or val == float('inf') or val == float('-inf'):  # NaN, inf 체크
            return default
        return val
    except (ValueError, TypeError):
        return default


def run_single_etf_backtest(etf_code, etf_name, strategy_class, start_date, end_date, cash=2_500_000, commission=0.0015, period="D"):
    """
    단일 ETF 백테스팅 실행 (포트폴리오의 1/4 비중)

    Args:
        etf_code: ETF 종목코드
        etf_name: ETF 이름
        strategy_class: 전략 클래스
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)
        cash: 초기 자본 (기본값: 250만원 = 1000만원의 1/4)
        commission: 슬리피지 (기본값: 0.15%)
        period: 봉 주기 (기본값: "D" 일봉, "60" 1시간봉)

    Returns:
        백테스팅 결과 딕셔너리
    """
    try:
        print(f"\n  [{etf_code}] {etf_name} 백테스팅 중...")

        # 데이터 로드
        df = load_stock_data(
            stock_code=etf_code,
            start_date=start_date,
            end_date=end_date,
            adjusted=True,
            period=period
        )

        if df.empty or len(df) < 101:  # 모멘텀 스코어 계산을 위해 최소 101봉 필요
            print(f"    ✗ 데이터 부족 (최소 101봉 필요, 현재 {len(df)}봉)")
            return None

        # 백테스팅 실행
        bt = Backtest(
            df,
            strategy_class,
            cash=cash,
            commission=commission,
            exclusive_orders=True,
            trade_on_close=False,  # 변동성 돌파는 장중 매매
            finalize_trades=True
        )

        stats = bt.run()

        # 결과 추출
        equity_curve = stats['_equity_curve']['Equity']
        initial_equity = safe_float(equity_curve.iloc[0] if len(equity_curve) > 0 else cash)
        final_equity = safe_float(stats.get('Equity Final [$]', cash))
        total_trades = int(stats.get('# Trades', 0))
        return_pct = safe_float(stats.get('Return [%]', 0))
        mdd_pct = safe_float(stats.get('Max. Drawdown [%]', 0))
        win_rate = safe_float(stats.get('Win Rate [%]', 0))
        sharpe = safe_float(stats.get('Sharpe Ratio', 0))

        result = {
            "etf_code": etf_code,
            "etf_name": etf_name,
            "success": True,
            "initial_equity": initial_equity,
            "final_equity": final_equity,
            "return_pct": return_pct,
            "total_trades": total_trades,
            "max_drawdown_pct": mdd_pct,
            "win_rate": win_rate,
            "sharpe_ratio": sharpe,
            "stats": stats,
            "backtest": bt
        }

        print(f"    ✓ 거래 {total_trades}회, 수익률 {return_pct:>8.2f}%, MDD {mdd_pct:>8.2f}%, 승률 {win_rate:.1f}%")

        return result

    except Exception as e:
        print(f"    ✗ 오류: {e}")
        import traceback
        traceback.print_exc()
        return {
            "etf_code": etf_code,
            "etf_name": etf_name,
            "success": False,
            "error": str(e)
        }


def main():
    """
    코스닥피 레인 포트폴리오 백테스팅 메인 함수
    """
    print("=" * 80)
    print("코스닥피 레인 (Kosdaq-Pi Rain) 전략 백테스팅")
    print("=" * 80)
    print("\n4개 ETF 포트폴리오 (각 1/4 비중):")
    for code, info in ETF_INFO.items():
        print(f"  - {code}: {info['name']}")

    # 1. KIS API 인증
    print("\n[1/4] KIS API 인증 중...")
    ka.auth(svr="prod")
    print("✓ 인증 완료")

    # 2. 백테스팅 파라미터
    start_date = "20200101"
    end_date = "20241231"
    total_cash = 10_000_000  # 총 1000만원
    cash_per_etf = total_cash / 4  # 각 ETF당 250만원
    commission = 0.0015
    period = "60"  # 1시간봉

    print(f"\n[2/4] 백테스팅 설정:")
    print(f"  기간: {start_date} ~ {end_date}")
    print(f"  봉 주기: {'1시간봉' if period == '60' else '일봉'}")
    print(f"  총 자본: {total_cash:,}원")
    print(f"  ETF당 자본: {cash_per_etf:,}원 (1/4 비중)")
    print(f"  슬리피지: {commission * 100}%")

    # 3. 각 ETF 백테스팅 실행
    print(f"\n[3/4] 4개 ETF 백테스팅 실행 중...")

    results = {}
    for etf_code, info in ETF_INFO.items():
        result = run_single_etf_backtest(
            etf_code=etf_code,
            etf_name=info['name'],
            strategy_class=info['strategy'],
            start_date=start_date,
            end_date=end_date,
            cash=cash_per_etf,
            commission=commission,
            period=period
        )

        if result and result.get("success"):
            results[etf_code] = result

    # 4. 포트폴리오 전체 결과 계산
    print("\n" + "=" * 80)
    print("[4/4] 포트폴리오 전체 결과")
    print("=" * 80)

    if not results:
        print("\n✗ 백테스팅 결과가 없습니다.")
        return

    # 개별 ETF 결과 출력
    print(f"\n{'ETF':<25} {'거래':<6} {'수익률':<10} {'MDD':<10} {'승률':<8} {'샤프':<8}")
    print("-" * 80)

    total_initial = 0
    total_final = 0
    total_trades = 0

    for etf_code, result in results.items():
        total_initial += result['initial_equity']
        total_final += result['final_equity']
        total_trades += result['total_trades']

        name = f"{result['etf_name']} ({etf_code})"
        print(f"{name:<25} {result['total_trades']:<6} "
              f"{result['return_pct']:>9.2f}% {result['max_drawdown_pct']:>9.2f}% "
              f"{result['win_rate']:>7.1f}% {result['sharpe_ratio']:>7.2f}")

    # 포트폴리오 전체 수익률
    total_return_pct = ((total_final - total_initial) / total_initial * 100) if total_initial > 0 else 0

    # 연간 수익률 (CAGR) 계산
    # 2020-01-01 ~ 2024-12-31 = 5년
    years = 5
    if total_initial > 0 and total_final > 0:
        cagr = (((total_final / total_initial) ** (1 / years)) - 1) * 100
    else:
        cagr = 0

    print("\n" + "=" * 80)
    print("포트폴리오 전체 성과:")
    print(f"  총 초기 자본:          {total_initial:>15,.0f} 원")
    print(f"  총 최종 자산:          {total_final:>15,.0f} 원")
    print(f"  총 손익:              {total_final - total_initial:>15,.0f} 원")
    print(f"  총 수익률:            {total_return_pct:>15.2f} %")
    print(f"  연간 수익률 (CAGR):   {cagr:>15.2f} %")
    print(f"  총 거래 횟수:         {total_trades:>15} 회")

    # 개별 ETF 차트 저장
    print("\n차트 저장 중...")
    os.makedirs("charts/kosdaq_pi_rain", exist_ok=True)

    for etf_code, result in results.items():
        if result['total_trades'] > 0:
            chart_filename = f"charts/kosdaq_pi_rain/{etf_code}_{result['etf_name']}_return{result['return_pct']:.1f}pct.html"
            result['backtest'].plot(filename=chart_filename, open_browser=False)
            print(f"  ✓ {result['etf_name']}: {chart_filename}")

    # 5. 모멘텀 기반 비중 조절 포트폴리오 계산
    print("\n" + "=" * 80)
    print("모멘텀 스코어 기반 비중 조절 포트폴리오")
    print("=" * 80)

    try:
        adjusted_results = calculate_momentum_adjusted_portfolio(results, start_date, end_date, total_cash, period)

        if adjusted_results:
            print(f"\n모멘텀 조절 포트폴리오 성과:")
            print(f"  총 초기 자본:          {adjusted_results['initial']:>15,.0f} 원")
            print(f"  총 최종 자산:          {adjusted_results['final']:>15,.0f} 원")
            print(f"  총 손익:              {adjusted_results['profit']:>15,.0f} 원")
            print(f"  총 수익률:            {adjusted_results['return_pct']:>15.2f} %")
            print(f"  연간 수익률 (CAGR):   {adjusted_results['cagr']:>15.2f} %")
            print(f"\n비교:")
            print(f"  기본 포트폴리오:      {total_return_pct:>15.2f} %")
            print(f"  모멘텀 조절:          {adjusted_results['return_pct']:>15.2f} %")
            print(f"  개선:                 {adjusted_results['return_pct'] - total_return_pct:>15.2f} %p")
    except Exception as e:
        print(f"\n모멘텀 비중 조절 계산 실패: {e}")

    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)

    return results


def calculate_momentum_adjusted_portfolio(results, start_date, end_date, total_cash, period="D"):
    """
    모멘텀 스코어 기반 비중 조절 포트폴리오 계산

    Args:
        results: 개별 ETF 백테스팅 결과
        start_date: 시작일
        end_date: 종료일
        total_cash: 총 자본
        period: 봉 주기 (기본값: "D" 일봉, "60" 1시간봉)

    Returns:
        dict: 조정된 포트폴리오 성과
    """
    print("\n  모멘텀 스코어 계산 중...")

    # 1. 원본 데이터 로드
    etf_data = {}
    for etf_code in results.keys():
        df = load_stock_data(
            stock_code=etf_code,
            start_date=start_date,
            end_date=end_date,
            adjusted=True,
            period=period
        )
        etf_data[etf_code] = df

    # 2. 공통 날짜 찾기
    common_dates = None
    for df in etf_data.values():
        if common_dates is None:
            common_dates = set(df.index)
        else:
            common_dates = common_dates.intersection(set(df.index))

    common_dates = sorted(list(common_dates))

    # 3. 날짜별로 비중 계산
    portfolio_values = []
    current_value = total_cash

    for i, date in enumerate(common_dates):
        if i == 0:
            portfolio_values.append(current_value)
            continue

        # 이전 날짜 대비 수익률 계산
        prev_date = common_dates[i-1]

        # 기본 비중: 각 25%
        weights = {
            "233740": 0.25,  # 코스닥 레버리지
            "251340": 0.25,  # 코스닥 인버스
            "122630": 0.25,  # 레버리지
            "252670": 0.25   # 인버스2X
        }

        # 모멘텀 스코어 계산 (101봉 이상 데이터 필요)
        if i >= 101:
            try:
                # 코스닥 레버리지 모멘텀 스코어
                lev_data = etf_data["233740"].loc[:date]
                lev_score1 = calculate_momentum_score1(lev_data, -1)
                lev_score2 = calculate_momentum_score2(lev_data, -1)

                # 코스닥 인버스 모멘텀 스코어
                inv_data = etf_data["251340"].loc[:date]
                inv_score1 = calculate_momentum_score1(inv_data, -1)
                inv_score2 = calculate_momentum_score2(inv_data, -1)

                # 비중 조절
                lev_weight, inv_weight = calculate_weight_adjustment(
                    lev_score1, lev_score2,
                    inv_score1, inv_score2
                )

                # 코스닥 50% 비중 내에서 조절
                kosdaq_base = 0.5
                total_kosdaq_weight = lev_weight + inv_weight

                weights["233740"] = kosdaq_base * (lev_weight / total_kosdaq_weight)
                weights["251340"] = kosdaq_base * (inv_weight / total_kosdaq_weight)
                # 코스피는 각 25% 유지

            except Exception:
                pass  # 계산 실패 시 기본 비중 유지

        # 포트폴리오 수익률 계산
        portfolio_return = 0
        for etf_code in results.keys():
            if date in etf_data[etf_code].index and prev_date in etf_data[etf_code].index:
                price_curr = etf_data[etf_code].loc[date, 'Close']
                price_prev = etf_data[etf_code].loc[prev_date, 'Close']
                etf_return = (price_curr - price_prev) / price_prev
                portfolio_return += weights[etf_code] * etf_return

        current_value = current_value * (1 + portfolio_return)
        portfolio_values.append(current_value)

    # 4. 결과 계산
    final_value = portfolio_values[-1] if portfolio_values else total_cash
    profit = final_value - total_cash
    return_pct = (profit / total_cash) * 100

    years = 5
    cagr = (((final_value / total_cash) ** (1 / years)) - 1) * 100 if final_value > 0 else 0

    print(f"  ✓ {len(common_dates)}봉 시뮬레이션 완료")

    return {
        'initial': total_cash,
        'final': final_value,
        'profit': profit,
        'return_pct': return_pct,
        'cagr': cagr,
        'portfolio_values': portfolio_values,
        'dates': common_dates
    }


if __name__ == "__main__":
    try:
        results = main()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()