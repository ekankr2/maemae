"""
풍선이론 (Balloon Theory) 전략

거래량 급증 시 상승 모멘텀을 포착하는 전략
- 당일 거래량이 전일 거래량 대비 400% 이상 증가 시 매수
- 5% 이상 상승
- 종가 기준 EMA 60일선 위
- 양봉이어야 함 (종가 > 시가)
- 주가 1000원 이상만 거래
- 거래량 100만개 이상
- 꼬리가 너무 길 경우 매수하지 않음 (봉 꼬리가 현재가 대비 10% 이상)
- 종가 배팅 (3시 15분에 매수)
- 거래량 재증가 시 매도 (당일 거래량 > 매수일 거래량)
- 전일 시가 이탈 시 매도 (종가 < 전일 시가)
- 고정 손절 -7%
"""
import sys
sys.path.append('..')

from backtesting import Strategy
import pandas as pd


class BalloonTheoryStrategy(Strategy):
    """
    풍선이론 전략

    매수 조건:
    1. 당일 거래량이 전일 거래량 대비 400% 이상 증가
    2. 5% 이상 상승
    3. 종가 기준 EMA 60일선 위
    4. 양봉이어야 함 (종가 > 시가)
    5. 주가가 1000원 이상
    6. 거래량이 100만개 이상
    7. 꼬리가 너무 길지 않음 (하단 꼬리가 종가 대비 10% 미만)

    매도 조건:
    1. 거래량 재증가: 당일 거래량 > 매수일 거래량
    2. 전일 시가 이탈: 종가 < 매수일 전일 시가
    3. 고정 손절: 매수가 대비 -7% 이상 손실
    """

    # 파라미터 설정
    min_price = 1000           # 최소 거래 가격
    min_gain_pct = 0.05        # 최소 상승률 (5%)
    volume_multiplier = 4.0    # 거래량 증가율 (400%)
    min_volume = 1000000       # 최소 거래량 (100만개)
    max_tail_ratio = 0.10      # 최대 꼬리 비율 (10%)
    ema_period = 60            # EMA 기간 (60일)
    stop_loss_pct = 0.07       # 고정 손절 비율 (7%)

    def init(self):
        """전략 초기화"""
        # EMA 60일선 계산
        self.ema60 = self.I(lambda x: pd.Series(x).ewm(span=self.ema_period, adjust=False).mean(), self.data.Close)

        # 진입 시 정보 저장 (매도 기준용)
        self.entry_price = None      # 매수 가격 (고정 손절 기준)
        self.entry_prev_open = None  # 매수일 전일 시가 (전일 시가 이탈 청산 기준)
        self.entry_volume = None     # 매수일 거래량 (거래량 재증가 청산 기준)

    def next(self):
        """매 봉마다 실행되는 매매 로직"""
        # 최소 2일치 데이터 필요
        if len(self.data.Close) < 2:
            return

        close = self.data.Close[-1]
        open_price = self.data.Open[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        prev_open = self.data.Open[-2]
        volume = self.data.Volume[-1]
        prev_volume = self.data.Volume[-2]

        # 현재 포지션이 있으면 매도 조건 체크
        if self.position:
            self._check_sell_signal(close, volume, prev_volume)
            return

        # 포지션이 없으면 매수 조건 체크
        self._check_buy_signal(close, open_price, high, low, prev_open, volume, prev_volume)

    def _check_buy_signal(self, close, open_price, high, low, prev_open, volume, prev_volume):
        """
        매수 시그널 체크

        조건:
        1. 당일 거래량이 전일 거래량 대비 400% 이상 증가
        2. 5% 이상 상승
        3. 종가 기준 EMA 60일선 위
        4. 양봉이어야 함 (종가 > 시가)
        5. 주가가 1000원 이상
        6. 거래량이 100만개 이상
        7. 꼬리가 너무 길지 않음 (하단 꼬리가 종가 대비 10% 미만)
        """
        # 최소 가격 조건 (1000원 이상)
        if close < self.min_price:
            return

        # 양봉 확인 (종가 > 시가)
        if close <= open_price:
            return

        # 5% 이상 상승 확인
        gain_pct = (close - open_price) / open_price if open_price > 0 else 0
        if gain_pct < self.min_gain_pct:
            return

        # 전일 거래량이 0이면 계산 불가
        if prev_volume == 0:
            return

        # 거래량 증가율 확인 (400% 이상)
        volume_ratio = volume / prev_volume
        if volume_ratio < self.volume_multiplier:
            return

        # 거래량 절대값 확인 (100만개 이상)
        if volume < self.min_volume:
            return

        # EMA 60일선 위에 있는지 확인
        if len(self.ema60) > 0 and close <= self.ema60[-1]:
            return

        # 꼬리 길이 체크 (하단 꼬리가 종가 대비 10% 이상이면 매수 안함)
        # 하단 꼬리 = 종가 - 저가
        lower_tail = close - low
        tail_ratio = lower_tail / close if close > 0 else 0
        if tail_ratio > self.max_tail_ratio:
            return

        # 모든 조건 만족 시 매수
        self.buy()
        self.entry_price = close          # 매수 가격 저장 (고정 손절 기준)
        self.entry_prev_open = prev_open  # 매수일 전일 시가 저장 (전일 시가 이탈 청산 기준)
        self.entry_volume = volume        # 매수일 거래량 저장 (거래량 재증가 청산 기준)

    def _check_sell_signal(self, close, volume, prev_volume):
        """
        매도 시그널 체크

        조건:
        1. 거래량 재증가: 당일 거래량 > 매수일 거래량
        2. 전일 시가 이탈: 종가 < 매수일 전일 시가
        3. 고정 손절: 매수가 대비 -7% 이상 손실
        """
        # 1. 고정 손절 체크 (-7%)
        if self.entry_price is not None:
            loss_pct = (close - self.entry_price) / self.entry_price
            if loss_pct <= -self.stop_loss_pct:
                self.position.close()
                self.entry_price = None
                self.entry_prev_open = None
                self.entry_volume = None
                return

        # 2. 거래량 재증가 체크 (당일 거래량 > 매수일 거래량)
        if self.entry_volume is not None and volume > self.entry_volume:
            self.position.close()
            self.entry_price = None
            self.entry_prev_open = None
            self.entry_volume = None
            return

        # 3. 전일 시가 이탈 체크 (종가 < 매수일 전일 시가)
        if self.entry_prev_open is not None and close < self.entry_prev_open:
            self.position.close()
            self.entry_price = None
            self.entry_prev_open = None
            self.entry_volume = None
            return