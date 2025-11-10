"""
EMA 골든 크로스 / 데드 크로스 전략
"""
import sys
sys.path.append('..')

from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd
from indicators.moving_average import calculate_ema


class EMACrossStrategy(Strategy):
    """
    EMA 골든/데드 크로스 전략

    진입: 단기 EMA가 장기 EMA를 상향 돌파 (골든 크로스)
    청산: 단기 EMA가 장기 EMA를 하향 돌파 (데드 크로스)
    """

    # 전략 파라미터 (최적화 가능)
    fast_period = 5   # 단기 EMA 기간
    slow_period = 20  # 장기 EMA 기간

    def init(self):
        """
        전략 초기화: 지표 계산
        """
        # 종가 데이터
        close_prices = self.data.Close

        # EMA 계산 (backtesting.py의 I() 헬퍼 사용)
        # 각 시점마다 EMA를 계산하기 위해 pandas의 ewm 사용
        self.fast_ema = self.I(
            lambda x: pd.Series(x).ewm(span=self.fast_period, adjust=False).mean(),
            close_prices,
            name=f'EMA{self.fast_period}'
        )

        self.slow_ema = self.I(
            lambda x: pd.Series(x).ewm(span=self.slow_period, adjust=False).mean(),
            close_prices,
            name=f'EMA{self.slow_period}'
        )

    def next(self):
        """
        각 봉(bar)마다 실행되는 매매 로직
        """
        # 골든 크로스: 단기 EMA가 장기 EMA를 상향 돌파
        if crossover(self.fast_ema, self.slow_ema):
            # 포지션이 없으면 매수
            if not self.position:
                self.buy()

        # 데드 크로스: 단기 EMA가 장기 EMA를 하향 돌파
        elif crossover(self.slow_ema, self.fast_ema):
            # 포지션이 있으면 매도
            if self.position:
                self.position.close()