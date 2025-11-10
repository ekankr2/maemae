"""
완전 자동매매 시스템

기능:
1. daily_scanner.py에서 찾은 매수 후보 감시
2. 실시간 시세로 EMA 터치 감지 → 자동 매수
3. 보유 종목 감시 → EMA60 이탈 시 자동 청산
"""
import sys
sys.path.extend(['.'])

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import kis_auth as ka
from data_loader import load_stock_data
from examples_llm_stock.order_cash.order_cash import order_cash
from domestic_stock.domestic_stock_functions_ws import current_concluded_price


class RealTimeEMA:
    """실시간 EMA 계산 및 관리"""

    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.ema60 = None
        self.ema112 = None
        self.ema224 = None
        self.prices = []

    def initialize(self):
        """과거 데이터로 EMA 초기화"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        df = load_stock_data(self.stock_code, start_date, end_date, adjusted=True)

        if len(df) < 224:
            raise ValueError(f"{self.stock_code}: 데이터 부족 (최소 224일 필요)")

        self.prices = df['Close'].values.tolist()

        # 초기 EMA 계산
        self.ema60 = self._calculate_ema(self.prices, 60)
        self.ema112 = self._calculate_ema(self.prices, 112)
        self.ema224 = self._calculate_ema(self.prices, 224)

        print(f"{self.stock_code} EMA 초기화 완료:")
        print(f"  EMA60={self.ema60:,.0f}, EMA112={self.ema112:,.0f}, EMA224={self.ema224:,.0f}")

    def _calculate_ema(self, prices, period):
        """EMA 계산 (daily_scanner.py와 동일)"""
        ema = sum(prices[:period]) / period
        multiplier = 2.0 / (period + 1)

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def update(self, new_price: float):
        """실시간 가격으로 EMA 업데이트"""
        # 가격 히스토리 업데이트 (최근 300개만 유지)
        self.prices.append(new_price)
        if len(self.prices) > 300:
            self.prices.pop(0)

        # EMA 증분 업데이트
        multiplier60 = 2.0 / (60 + 1)
        multiplier112 = 2.0 / (112 + 1)
        multiplier224 = 2.0 / (224 + 1)

        self.ema60 = (new_price - self.ema60) * multiplier60 + self.ema60
        self.ema112 = (new_price - self.ema112) * multiplier112 + self.ema112
        self.ema224 = (new_price - self.ema224) * multiplier224 + self.ema224

    def get_distance(self, price: float, ema: float) -> float:
        """이격률 계산"""
        if ema == 0:
            return 999.0
        return ((price - ema) / ema) * 100

    def is_near_ema(self, price: float, ema: float, threshold: float = 0.5) -> bool:
        """EMA 근처 터치 감지 (±threshold% 이내)"""
        distance = abs(self.get_distance(price, ema))
        return distance <= threshold


class AutoTrader:
    """자동매매 엔진"""

    def __init__(self, mode: str = "demo"):
        """
        Args:
            mode: "demo" (모의투자) or "real" (실전투자)
        """
        self.mode = mode
        self.watch_list: Dict[str, RealTimeEMA] = {}  # 감시 종목
        self.positions: Dict[str, dict] = {}  # 보유 포지션

        # 계좌 정보 (환경변수에서 로드)
        self.cano = os.getenv("KIS_ACCOUNT_NO")
        self.acnt_prdt_cd = os.getenv("KIS_ACCOUNT_PRODUCT_CD")

        if not self.cano or not self.acnt_prdt_cd:
            raise ValueError("환경변수에 계좌정보 설정 필요: KIS_ACCOUNT_NO, KIS_ACCOUNT_PRODUCT_CD")

        print(f"자동매매 엔진 시작 (모드: {mode})")
        print(f"계좌: {self.cano}-{self.acnt_prdt_cd}")

    def load_watch_list(self, csv_file: str):
        """스캐너 결과(CSV)에서 감시 종목 로드"""
        import pandas as pd

        if not os.path.exists(csv_file):
            print(f"⚠️  {csv_file} 파일이 없습니다. daily_scanner.py를 먼저 실행하세요.")
            return

        df = pd.read_csv(csv_file, encoding='utf-8-sig')

        for _, row in df.iterrows():
            code = row['종목코드']
            name = row['종목명']

            print(f"\n감시 종목 추가: {name} ({code})")

            ema_tracker = RealTimeEMA(code)
            ema_tracker.initialize()

            self.watch_list[code] = ema_tracker

        print(f"\n✓ 총 {len(self.watch_list)}개 종목 감시 시작")

    def load_positions(self, json_file: str = "positions.json"):
        """보유 포지션 로드"""
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                self.positions = json.load(f)
            print(f"✓ 보유 포지션 {len(self.positions)}개 로드")

    def save_positions(self, json_file: str = "positions.json"):
        """보유 포지션 저장"""
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.positions, f, ensure_ascii=False, indent=2)

    def buy_signal(self, code: str, current_price: float) -> bool:
        """매수 시그널 감지"""
        ema_tracker = self.watch_list[code]

        # 이미 보유 중이면 추가 매수 안함
        if code in self.positions:
            return False

        # EMA 터치 감지 (±0.5% 이내)
        if ema_tracker.is_near_ema(current_price, ema_tracker.ema60, threshold=0.5):
            print(f"🎯 {code}: EMA60 터치! (현재가={current_price:,.0f}, EMA60={ema_tracker.ema60:,.0f})")
            return True

        if ema_tracker.is_near_ema(current_price, ema_tracker.ema112, threshold=0.5):
            print(f"🎯 {code}: EMA112 터치! (현재가={current_price:,.0f}, EMA112={ema_tracker.ema112:,.0f})")
            return True

        if ema_tracker.is_near_ema(current_price, ema_tracker.ema224, threshold=0.5):
            print(f"🎯 {code}: EMA224 터치! (현재가={current_price:,.0f}, EMA224={ema_tracker.ema224:,.0f})")
            return True

        return False

    def sell_signal(self, code: str, current_price: float) -> bool:
        """청산 시그널 감지 (EMA60 이탈)"""
        if code not in self.positions:
            return False

        ema_tracker = self.watch_list.get(code)
        if not ema_tracker:
            return False

        # EMA60 밑으로 이탈하면 청산
        if current_price < ema_tracker.ema60:
            distance = ema_tracker.get_distance(current_price, ema_tracker.ema60)
            print(f"⚠️  {code}: EMA60 이탈! (현재가={current_price:,.0f}, EMA60={ema_tracker.ema60:,.0f}, 이격률={distance:.2f}%)")
            return True

        return False

    def execute_buy(self, code: str, price: float, quantity: int = 10):
        """매수 주문 실행"""
        print(f"\n💰 매수 주문: {code} {quantity}주 @ {price:,.0f}원")

        try:
            result = order_cash(
                env_dv=self.mode,  # "demo" or "real"
                ord_dv="buy",
                cano=self.cano,
                acnt_prdt_cd=self.acnt_prdt_cd,
                pdno=code,
                ord_dvsn="01",  # 시장가
                ord_qty=str(quantity),
                ord_unpr="0",  # 시장가는 0
                excg_id_dvsn_cd="01"
            )

            # 포지션 기록
            self.positions[code] = {
                "buy_price": price,
                "quantity": quantity,
                "buy_time": datetime.now().isoformat()
            }
            self.save_positions()

            print(f"✓ 매수 완료: {code} {quantity}주")

            # 감시 목록에서 제거 (포지션 목록으로 이동)
            if code in self.watch_list:
                ema_tracker = self.watch_list.pop(code)
                # 청산 감시를 위해 포지션에 EMA 정보 유지
                self.watch_list[code] = ema_tracker

            return True

        except Exception as e:
            print(f"❌ 매수 실패: {e}")
            return False

    def execute_sell(self, code: str, price: float):
        """청산 주문 실행"""
        position = self.positions[code]
        quantity = position['quantity']

        print(f"\n💸 청산 주문: {code} {quantity}주 @ {price:,.0f}원")

        try:
            result = order_cash(
                env_dv=self.mode,
                ord_dv="sell",
                cano=self.cano,
                acnt_prdt_cd=self.acnt_prdt_cd,
                pdno=code,
                ord_dvsn="01",  # 시장가
                ord_qty=str(quantity),
                ord_unpr="0",
                excg_id_dvsn_cd="01",
                sll_type="01"  # 일반 매도
            )

            # 손익 계산
            buy_price = position['buy_price']
            profit = (price - buy_price) * quantity
            profit_rate = ((price - buy_price) / buy_price) * 100

            print(f"✓ 청산 완료: {code}")
            print(f"  매수가: {buy_price:,.0f}원 → 청산가: {price:,.0f}원")
            print(f"  손익: {profit:,.0f}원 ({profit_rate:+.2f}%)")

            # 포지션 제거
            del self.positions[code]
            self.save_positions()

            return True

        except Exception as e:
            print(f"❌ 청산 실패: {e}")
            return False

    async def monitor_realtime(self):
        """실시간 시세 감시 (WebSocket)"""
        print("\n실시간 시세 감시 시작...")

        # 감시 종목 + 보유 종목
        all_codes = set(self.watch_list.keys()) | set(self.positions.keys())

        for code in all_codes:
            print(f"  구독: {code}")

            # WebSocket 콜백 등록
            async def on_price_update(data):
                stock_code = data['stock_code']
                current_price = float(data['current_price'])

                # EMA 업데이트
                if stock_code in self.watch_list:
                    self.watch_list[stock_code].update(current_price)

                # 매수 시그널 확인
                if self.buy_signal(stock_code, current_price):
                    self.execute_buy(stock_code, current_price, quantity=10)

                # 청산 시그널 확인
                if self.sell_signal(stock_code, current_price):
                    self.execute_sell(stock_code, current_price)

            # WebSocket 구독
            await current_concluded_price(
                stock_code=code,
                callback=on_price_update
            )

    async def run(self):
        """자동매매 실행"""
        print("\n" + "=" * 60)
        print("자동매매 시스템 가동")
        print("=" * 60)

        # 1. 오늘 스캔 결과 로드
        today = datetime.now().strftime("%Y%m%d")
        csv_file = f"buy_candidates_{today}.csv"
        self.load_watch_list(csv_file)

        # 2. 기존 포지션 로드
        self.load_positions()

        # 3. 실시간 감시 시작
        await self.monitor_realtime()


async def main():
    """메인 함수"""
    # KIS API 인증
    print("KIS API 인증 중...")
    ka.auth(svr="vps")  # vps: 모의투자
    print("✓ 인증 완료")

    # 자동매매 엔진 시작
    trader = AutoTrader(mode="demo")  # 모의투자
    await trader.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n자동매매 종료")