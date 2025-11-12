"""
백테스팅 실행 스크립트

풍선이론 (거래량 돌파) 전략 테스트
"""
import sys
import os
import pandas as pd
import logging
from datetime import datetime
from backtesting import Backtest
import kis_auth as ka
from data_loader import load_stock_data
from strategies.balloon_theory_strategy import BalloonTheoryStrategy
from examples_llm_stock.volume_rank.volume_rank import volume_rank
from examples_llm_stock.market_cap.market_cap import market_cap

logging.getLogger('examples_llm_stock.search_stock_info.search_stock_info').setLevel(logging.WARNING)


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


def run_backtest_single(stock_code, stock_name, start_date, end_date, cash=10_000_000, commission=0.0015, save_chart=True):
    """단일 종목 백테스팅 실행"""
    try:
        df = load_stock_data(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            adjusted=True
        )

        if df.empty or len(df) < 250:  # 최소 250일 데이터 필요 (EMA 224일선 계산)
            return None

        from examples_llm_stock.search_stock_info.search_stock_info import search_stock_info
        stock_info = search_stock_info("300", stock_code)
        if not stock_info.empty and 'lstg_stqt' in stock_info.columns:
            lstg_stqt = int(stock_info['lstg_stqt'].iloc[0])
            df['MarketCap'] = lstg_stqt * df['Close']
        else:
            df['MarketCap'] = 0

        bt = Backtest(
            df,
            BalloonTheoryStrategy,
            cash=cash,
            commission=commission,
            exclusive_orders=True,
            trade_on_close=True,  # 종가 배팅: 신호 발생 시 당일 종가에 즉시 거래 (다음날 시가 X)
            finalize_trades=True  # 백테스팅 종료 시 미청산 포지션 자동 청산
        )

        stats = bt.run()

        equity_curve = stats['_equity_curve']['Equity']
        initial_equity = safe_float(equity_curve.iloc[0] if len(equity_curve) > 0 else 0)
        total_trades = int(stats.get('# Trades', 0))

        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "success": True,
            "initial_equity": initial_equity,
            "final_equity": safe_float(stats.get('Equity Final [$]', 0)),
            "return_pct": safe_float(stats.get('Return [%]', 0)),
            "total_trades": total_trades,
            "win_rate_pct": safe_float(stats.get('Win Rate [%]', 0)),
            "max_drawdown_pct": safe_float(stats.get('Max. Drawdown [%]', 0)),
            "sharpe_ratio": safe_float(stats.get('Sharpe Ratio', 0))
        }

        # 거래가 있는 종목만 차트 저장
        if save_chart and total_trades > 0:
            safe_name = stock_name.replace(' ', '_').replace('/', '_')
            chart_filename = f"charts/{stock_code}_{safe_name}_return{result['return_pct']:.1f}pct.html"
            os.makedirs("charts", exist_ok=True)
            bt.plot(filename=chart_filename, open_browser=False)
            result["chart_path"] = chart_filename

        return result
    except Exception as e:
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "success": False,
            "error": str(e)
        }


def get_stock_list_from_csv(csv_file=None):
    """CSV 파일에서 종목 리스트 가져오기"""
    if csv_file is None:
        # 최신 CSV 파일 찾기
        csv_files = [f for f in os.listdir('.') if f.startswith('buy_candidates_') and f.endswith('.csv')]
        if not csv_files:
            return None
        csv_file = max(csv_files)  # 가장 최신 파일
    
    if not os.path.exists(csv_file):
        return None
    
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    # 종목코드 컬럼 찾기
    for col in ['종목코드', 'code', 'stock_code', 'mksc_shrn_iscd']:
        if col in df.columns:
            return df[col].tolist()
    
    return None


def get_stock_list_from_api():
    """API로 거래량 상위 종목 리스트 가져오기 (스캐너와 동일한 조건)"""
    print("  거래량 상위 종목 조회 중 (여러 기준 병합)...")

    # 2-1. 평균거래량 기준 (30개)
    print("  - 평균거래량 기준...")
    stocks_avg_volume = volume_rank(
        fid_cond_mrkt_div_code="J",
        fid_cond_scr_div_code="20171",
        fid_input_iscd="0000",
        fid_div_cls_code="0",
        fid_blng_cls_code="0",  # 0: 평균거래량
        fid_trgt_cls_code="111111111",
        fid_trgt_exls_cls_code="0000000000",
        fid_input_price_1="1000",  # 1000원 이상
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
        fid_blng_cls_code="1",  # 1: 거래증가율
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
        fid_blng_cls_code="3",  # 3: 거래금액순
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
        fid_input_iscd="0001",  # 0001: 코스피
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
        fid_input_iscd="1001",  # 1001: 코스닥
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

    print(f"  ✓ 총 {len(all_stocks)}개 종목 로드 완료 (중복 제거 후)")

    # ETF/ETN 제외 키워드
    exclude_keywords = ['KODEX', 'TIGER', 'KINDEX', 'KOSEF', 'ARIRANG', 'KBSTAR',
                        'HANARO', 'TIMEFOLIO', 'SOL', 'TREX', 'ACE', '스팩',
                        '코스피', '코스닥', 'ETF', 'ETN', '레버리지', '인버스',
                        '곱버스', '2X', '3X', 'X2', 'X3']

    # 종목코드와 종목명을 딕셔너리로 반환 (ETF/ETN 제외)
    stock_dict = {}
    filtered_count = 0
    for _, row in all_stocks.iterrows():
        code = row['mksc_shrn_iscd']
        name = row.get('hts_kor_isnm', '').strip() if 'hts_kor_isnm' in row else ''

        # ETF/ETN 필터링
        if any(keyword in name.upper() for keyword in [k.upper() for k in exclude_keywords]):
            filtered_count += 1
            continue

        stock_dict[code] = name

    print(f"  ✓ ETF/ETN {filtered_count}개 제외, 최종 {len(stock_dict)}개 종목")

    return stock_dict


def main():
    """
    백테스팅 실행 (여러 종목 자동 처리)
    """
    print("=" * 80)
    print("풍선이론 (Balloon Theory) 전략 백테스팅 - 다중 종목")
    print("=" * 80)

    # 1. KIS API 인증
    print("\n[1/5] KIS API 인증 중...")
    ka.auth(svr="prod")
    print("✓ 인증 완료")

    # 2. 종목 리스트 가져오기 (항상 API로 가져오기)
    print("\n[2/5] 종목 리스트 수집 중...")

    # API로 종목 가져오기 (스캐너와 동일한 조건으로 150개)
    stock_dict = get_stock_list_from_api()

    if not stock_dict:
        print("✗ 종목 리스트를 가져올 수 없습니다.")
        return

    # 최대 150개로 제한 (너무 많으면 시간이 오래 걸림)
    if len(stock_dict) > 150:
        print(f"  (150개로 제한: {len(stock_dict)}개 중)")
        stock_dict = dict(list(stock_dict.items())[:150])

    # 3. 백테스팅 파라미터
    start_date = "20220101"
    end_date = "20231231"
    cash = 10_000_000
    commission = 0.0015

    # 4. 각 종목 백테스팅 실행
    print(f"\n[3/5] {len(stock_dict)}개 종목 백테스팅 실행 중...")
    print(f"  기간: {start_date} ~ {end_date}")
    print()

    results = []
    total_initial = 0
    total_final = 0
    total_trades = 0

    trade_count = 0  # 거래 발생 종목 카운터
    for i, (stock_code, stock_name) in enumerate(stock_dict.items(), 1):
        stock_code_str = str(stock_code).zfill(6)
        display_name = f"{stock_name[:8]}" if stock_name else stock_code_str

        result = run_backtest_single(stock_code_str, stock_name, start_date, end_date, cash, commission)

        if result and result.get("success"):
            results.append(result)
            total_initial += result["initial_equity"]
            total_final += result["final_equity"]
            total_trades += result["total_trades"]

            # 거래가 있는 종목만 로그 출력
            if result["total_trades"] > 0:
                trade_count += 1
                print(f"  [{trade_count}] {stock_code_str} ({display_name}) - 거래 {result['total_trades']}회, 수익률 {result['return_pct']:>8.2f}%, 승률 {result['win_rate_pct']:>6.1f}%")
                if "chart_path" in result:
                    print(f"      → 차트: {result['chart_path']}")

    # 5. 결과 요약
    print("\n" + "=" * 80)
    print("[4/5] 백테스팅 결과 요약")
    print("=" * 80)
    
    if not results:
        print("\n거래가 발생한 종목이 없습니다.")
        return
    
    successful_stocks = [r for r in results if r.get("total_trades", 0) > 0]

    print(f"\n전체 통계:")
    print(f"  테스트 종목 수:        {len(stock_dict):>15} 개")
    print(f"  성공한 백테스팅:       {len(results):>15} 개")
    print(f"  거래 발생 종목:        {len(successful_stocks):>15} 개")

    if successful_stocks:
        print(f"\n거래 발생 종목 상세 (전체 {len(successful_stocks)}개):")
        print(f"{'종목명':<12} {'코드':<8} {'거래':<6} {'수익률':<10} {'승률':<8} {'MDD':<10}")
        print("-" * 70)

        # 수익률 순으로 정렬
        successful_stocks.sort(key=lambda x: x.get("return_pct", 0), reverse=True)

        # 전체 거래 발생 종목 표시
        for r in successful_stocks:
            name = r.get('stock_name', '')[:10] or r['stock_code']
            print(f"{name:<12} {r['stock_code']:<8} {r['total_trades']:<6} {r['return_pct']:>9.2f}% {r['win_rate_pct']:>7.2f}% {r['max_drawdown_pct']:>9.2f}%")
    
    total_return = ((total_final - total_initial) / total_initial * 100) if total_initial > 0 else 0
    
    print(f"\n전체 포트폴리오:")
    print(f"  총 초기 자본:          {total_initial:>15,.0f} 원")
    print(f"  총 최종 자산:          {total_final:>15,.0f} 원")
    print(f"  총 수익률:            {total_return:>15.2f} %")
    print(f"  총 거래 횟수:         {total_trades:>15} 회")
    
    print("\n" + "=" * 80)
    print("[5/5] 완료")
    print("=" * 80)

    return results


if __name__ == "__main__":
    try:
        stats = main()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()