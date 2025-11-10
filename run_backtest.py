"""
백테스팅 실행 스크립트

삼성전자 1년치 데이터로 이평 때리기 전략 테스트
"""
from backtesting import Backtest
import kis_auth as ka
from data_loader import load_stock_data
from strategies.ema_pullback_strategy import EMAPullbackStrategy


def main():
    """
    백테스팅 실행
    """
    print("=" * 60)
    print("이평 때리기 (EMA Pullback) 전략 백테스팅")
    print("=" * 60)

    # 1. KIS API 인증 (모의투자 서버)
    print("\n[1/4] KIS API 인증 중...")
    ka.auth(svr="vps")  # vps: 모의투자
    print("✓ 인증 완료")

    # 2. 과거 데이터 로드
    print("\n[2/4] 삼성전자 일봉 데이터 로딩 중...")
    stock_code = "005930"  # 삼성전자
    start_date = "20230101"
    end_date = "20231231"

    df = load_stock_data(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        adjusted=True,  # 수정주가 사용
        mode="vps"
    )
    print(f"✓ 데이터 로드 완료: {len(df)}개 봉")
    print(f"  기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"\n데이터 샘플:\n{df.head()}")

    # 3. 백테스팅 설정
    print("\n[3/4] 백테스팅 설정 중...")
    bt = Backtest(
        df,
        EMAPullbackStrategy,
        cash=10_000_000,  # 초기 자본금 1천만원
        commission=0.0015,  # 수수료 0.15%
        exclusive_orders=True  # 동시에 여러 주문 불가
    )
    print("✓ 백테스팅 설정 완료")

    # 4. 백테스팅 실행
    print("\n[4/4] 백테스팅 실행 중...")
    stats = bt.run()
    print("✓ 백테스팅 완료")

    # 5. 결과 출력
    print("\n" + "=" * 60)
    print("백테스팅 결과")
    print("=" * 60)
    print(f"\n전략: 이평 때리기 EMA({EMAPullbackStrategy.ema_short}, {EMAPullbackStrategy.ema_mid}, {EMAPullbackStrategy.ema_long})")
    print(f"\n주요 성과 지표:")
    print(f"  초기 자본금:        {stats['_equity_curve']['Equity'][0]:>15,.0f} 원")
    print(f"  최종 자산:          {stats['Equity Final [$]']:>15,.0f} 원")
    print(f"  총 수익률:          {stats['Return [%]']:>15.2f} %")
    print(f"  연환산 수익률:      {stats.get('Return (Ann.) [%]', 0):>15.2f} %")
    print(f"\n거래 정보:")
    print(f"  총 거래 횟수:       {stats['# Trades']:>15} 회")
    print(f"  승률:               {stats['Win Rate [%]']:>15.2f} %")
    print(f"\n리스크 지표:")
    print(f"  최대 낙폭 (MDD):    {stats['Max. Drawdown [%]']:>15.2f} %")
    print(f"  샤프 비율:          {stats.get('Sharpe Ratio', 0):>15.2f}")

    # 6. 차트 생성 (선택)
    print("\n백테스팅 차트를 생성하시겠습니까? (브라우저에서 열립니다)")
    user_input = input("y/n: ").strip().lower()
    if user_input == 'y':
        bt.plot()

    return stats


if __name__ == "__main__":
    try:
        stats = main()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()