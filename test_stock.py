"""
한국투자증권 API 테스트 스크립트
"""
import logging
import kis_auth as ka
from domestic_stock.stock_api import *

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # 모의투자 인증
    logger.info("=== 한국투자증권 API 인증 시작 ===")
    ka.auth(svr="vps", product="01")  # vps: 모의투자, prod: 실전투자
    logger.info("인증 완료\n")

    # 1. 삼성전자 현재가 조회
    logger.info("=== 1. 삼성전자 현재가 조회 ===")
    price_info = inquire_price("005930")
    if price_info:
        print(f"종목: 삼성전자 (005930)")
        print(f"현재가: {price_info['현재가']:,}원")
        print(f"전일대비: {price_info['전일대비']:+,}원 ({price_info['등락률']:+.2f}%)")
        print(f"거래량: {price_info['거래량']:,}주")
        print(f"시가: {price_info['시가']:,}원")
        print(f"고가: {price_info['고가']:,}원")
        print(f"저가: {price_info['저가']:,}원\n")

    # 2. 보유 잔고 조회
    logger.info("=== 2. 보유 주식 잔고 조회 ===")
    balance = inquire_balance()
    if balance:
        if len(balance) == 0:
            print("보유 주식이 없습니다.\n")
        else:
            for stock in balance:
                print(f"{stock['종목명']} ({stock['종목코드']})")
                print(f"  보유수량: {stock['보유수량']:,}주")
                print(f"  매입평균가: {stock['매입평균가']:,}원")
                print(f"  현재가: {stock['현재가']:,}원")
                print(f"  평가손익: {stock['평가손익']:+,}원 ({stock['수익률']:+.2f}%)\n")

    # 3. 삼성전자 일봉 데이터 조회 (최근 30일)
    logger.info("=== 3. 삼성전자 일봉 데이터 조회 (최근 5일) ===")
    daily_prices = inquire_daily_price("005930", period="D")
    if daily_prices:
        for i, day in enumerate(daily_prices[:5]):
            print(f"{day['일자']}: 시가 {day['시가']:,} / 고가 {day['고가']:,} / "
                  f"저가 {day['저가']:,} / 종가 {day['종가']:,} / 거래량 {day['거래량']:,}")

    logger.info("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()