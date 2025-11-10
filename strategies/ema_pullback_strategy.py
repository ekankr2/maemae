"""
이평 때리기 (EMA Pullback) 전략

큰 하락 후 바닥에서 상승 초입을 잡아내는 전략
- EMA 60, 112, 224 사용
- 이평선 돌파 후 눌림목에서 다시 터치하면 매수
- 상위 이평선 도달 시 매도
"""
import sys
sys.path.append('..')

from backtesting import Strategy
import pandas as pd


class EMAPullbackStrategy(Strategy):
    """
    이평 때리기 전략

    매수 조건:
    1. 주가가 EMA를 상향 돌파한 이력이 있음
    2. 눌림목이 와서 해당 EMA 근처로 접근 (1% 이내)
    3. 다시 반등 시그널 (종가 > 시가)

    매도 조건:
    - EMA60 이탈 시 매도
    """

    # EMA 기간 설정
    ema_short = 60    # 단기 이평선
    ema_mid = 112     # 중기 이평선
    ema_long = 224    # 장기 이평선

    # 이평선 터치 판단 기준 (%)
    touch_threshold = 1.0  # 1% 이내면 터치로 판단

    def init(self):
        """전략 초기화: EMA 계산"""
        close = self.data.Close

        # EMA 계산
        self.ema60 = self.I(
            lambda x: pd.Series(x).ewm(span=self.ema_short, adjust=False).mean(),
            close,
            name=f'EMA{self.ema_short}'
        )

        self.ema112 = self.I(
            lambda x: pd.Series(x).ewm(span=self.ema_mid, adjust=False).mean(),
            close,
            name=f'EMA{self.ema_mid}'
        )

        self.ema224 = self.I(
            lambda x: pd.Series(x).ewm(span=self.ema_long, adjust=False).mean(),
            close,
            name=f'EMA{self.ema_long}'
        )

        # 매수한 EMA 레벨 추적 (60, 112, 224 중 어디서 샀는지)
        self.buy_ema_level = None

    def next(self):
        """매 봉마다 실행되는 매매 로직"""
        close = self.data.Close[-1]
        prev_close = self.data.Close[-2] if len(self.data.Close) > 1 else close
        open_price = self.data.Open[-1]

        # 현재 포지션이 있으면 매도 조건 체크
        if self.position:
            self._check_sell_signal(close)
            return

        # 포지션이 없으면 매수 조건 체크
        self._check_buy_signal(close, prev_close, open_price)

    def _is_near_ema(self, price, ema_value):
        """주가가 EMA 근처인지 확인 (threshold % 이내)"""
        if ema_value == 0:
            return False
        diff_pct = abs((price - ema_value) / ema_value) * 100
        return diff_pct <= self.touch_threshold

    def _is_price_above_ema(self, price, ema_value):
        """주가가 EMA 위에 있는지 확인"""
        return price > ema_value

    def _check_buy_signal(self, close, prev_close, open_price):
        """
        매수 시그널 체크

        조건:
        1. 현재가가 EMA60 위에 있음 (상승장 필터)
        2. 주가가 EMA 근처로 접근 (눌림목)
        3. 반등 시그널 (종가 > 시가)
        """
        # 상승장 필터: 주가가 EMA60 아래면 매수 안 함
        if close < self.ema60[-1]:
            return

        # 반등 확인: 양봉
        is_bullish = close > open_price

        if not is_bullish:
            return

        # EMA60 근처에서 매수 기회 체크
        if (self._is_price_above_ema(prev_close, self.ema60[-2]) and
            self._is_near_ema(close, self.ema60[-1]) and
            self.ema60[-1] > self.ema60[-5]):  # EMA60이 상승 추세

            self.buy()
            self.buy_ema_level = 60
            return

        # EMA112 근처에서 매수 기회 체크
        if (self._is_price_above_ema(prev_close, self.ema112[-2]) and
            self._is_near_ema(close, self.ema112[-1]) and
            self.ema112[-1] > self.ema112[-5]):  # EMA112가 상승 추세

            self.buy()
            self.buy_ema_level = 112
            return

        # EMA224 근처에서 매수 기회 체크
        if (self._is_price_above_ema(prev_close, self.ema224[-2]) and
            self._is_near_ema(close, self.ema224[-1]) and
            self.ema224[-1] > self.ema224[-5]):  # EMA224가 상승 추세

            self.buy()
            self.buy_ema_level = 224
            return

    def _check_sell_signal(self, close):
        """
        매도 시그널 체크

        조건: EMA60 아래로 이탈하면 전량 매도 (추세 전환)
        """
        # EMA60 이탈 시 매도
        if close < self.ema60[-1]:
            self.position.close()
            self.buy_ema_level = None