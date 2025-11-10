"""
풍선이론 (Balloon Theory) 전략

거래량 급증 시 상승 모멘텀을 포착하는 전략
- EMA60 위에 있는 종목만 선택 (상승 추세 확인)
- 당일 거래량이 전일 거래량 대비 400% 이상 증가 시 매수
- 주가 1,000원 이상만 거래
- 양봉이어야 함 (종가 > 시가)
- 종가 기준 EMA60 이탈 또는 전일 시가 이탈 시 손절
"""
import sys
sys.path.append('..')

from backtesting import Strategy
import pandas as pd


class BalloonTheoryStrategy(Strategy):
    """
    풍선이론 전략

    매수 조건:
    1. 종가가 EMA60 위에 있음 (상승 추세)
    2. 주가가 1,000원 이상
    3. 당일 거래량이 전일 거래량 대비 400% 이상 증가
    4. 양봉이어야 함 (종가 > 시가)

    매도 조건:
    1. 종가가 EMA60 아래로 이탈
    2. 종가가 전일 일봉 시가 아래로 이탈
    """

    # 파라미터 설정
    ema_period = 60           # EMA 기간
    min_price = 1000          # 최소 거래 가격
    volume_multiplier = 4.0   # 거래량 증가율 (400%)

    def init(self):
        """전략 초기화: EMA 계산"""
        close = self.data.Close

        # EMA60 계산
        self.ema60 = self.I(
            lambda x: pd.Series(x).ewm(span=self.ema_period, adjust=False).mean(),
            close,
            name=f'EMA{self.ema_period}'
        )

        # 진입 시 시가 저장 (손절 기준용)
        self.entry_prev_open = None

    def next(self):
        """매 봉마다 실행되는 매매 로직"""
        # 최소 2일치 데이터 필요
        if len(self.data.Close) < 2:
            return

        close = self.data.Close[-1]
        open_price = self.data.Open[-1]
        prev_close = self.data.Close[-2]
        prev_open = self.data.Open[-2]
        volume = self.data.Volume[-1]
        prev_volume = self.data.Volume[-2]

        # 현재 포지션이 있으면 매도 조건 체크
        if self.position:
            self._check_sell_signal(close, prev_open)
            return

        # 포지션이 없으면 매수 조건 체크
        self._check_buy_signal(close, open_price, prev_open, volume, prev_volume)

    def _check_buy_signal(self, close, open_price, prev_open, volume, prev_volume):
        """
        매수 시그널 체크

        조건:
        1. 종가가 EMA60 위에 있음
        2. 주가가 1,000원 이상
        3. 당일 거래량이 전일 거래량 대비 400% 이상 증가
        4. 양봉이어야 함 (종가 > 시가)
        """
        # EMA60 위에 있는지 확인
        if close <= self.ema60[-1]:
            return

        # 최소 가격 조건
        if close < self.min_price:
            return

        # 양봉 확인 (종가 > 시가)
        if close <= open_price:
            return

        # 전일 거래량이 0이면 계산 불가
        if prev_volume == 0:
            return

        # 거래량 증가율 확인
        volume_ratio = volume / prev_volume
        if volume_ratio < self.volume_multiplier:
            return

        # 모든 조건 만족 시 매수
        self.buy()
        self.entry_prev_open = prev_open  # 손절 기준 저장

    def _check_sell_signal(self, close, prev_open):
        """
        매도 시그널 체크

        조건:
        1. 종가가 EMA60 아래로 이탈
        2. 종가가 전일 시가 아래로 이탈
        """
        # EMA60 이탈 시 매도
        if close < self.ema60[-1]:
            self.position.close()
            self.entry_prev_open = None
            return

        # 전일 시가 이탈 시 매도 (손절)
        if self.entry_prev_open is not None and close < self.entry_prev_open:
            self.position.close()
            self.entry_prev_open = None
            return