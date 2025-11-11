"""
풍선이론 (Balloon Theory) 전략

거래량 급증 시 상승 모멘텀을 포착하는 전략

진입 조건:
- 당일 거래량이 전일 거래량 대비 400% 이상, 2000% 이하 증가
- 양봉이어야 함 (종가 > 시가)
- 종가 배팅 (3시 15분에 매수)

매수 제외 조건:
- 위꼬리가 너무 길 경우 (고가 대비 종가가 5% 이상 차이)
- 주가 2000원 이하
- 주가 30만원 이상
- EMA 20, 60일선 역배열
- 거래량 300만개 이하
- 22% 이상 상승
- EMA 20일선과 종가의 이격이 20% 이상일 경우
- ETF, ETN 등

청산 조건 (우선순위 순서):
- 매수일 시가 이탈 시
- 매수일 거래량을 넘는 거래량이 나올 시
- SMA 20일선 이탈 시
- 위꼬리가 너무 긴 양봉이 나올 경우 (양봉이면서 고가 대비 현재가가 7% 이상 차이)
- 조건 충족 시 장마감 전에 매도 (3시 10분 ~ 20분)
"""
import sys
sys.path.append('..')

from backtesting import Strategy
import pandas as pd


class BalloonTheoryStrategy(Strategy):
    """
    풍선이론 전략

    매수 조건:
    1. 당일 거래량이 전일 거래량 대비 400% 이상, 2000% 이하 증가
    2. 양봉이어야 함 (종가 > 시가)
    3. 거래량이 300만개 이상
    4. 위꼬리가 너무 길지 않음 (고가 대비 종가가 5% 이상 차이나지 않음)

    매수 제외 조건:
    1. 주가 2000원 이하
    2. 주가 30만원 이상
    3. EMA 20, 60일선 역배열
    4. 22% 이상 상승
    5. EMA 20일선과 종가의 이격이 20% 이상일 경우

    매도 조건 (우선순위 순서):
    1. 매수일 시가 이탈 시 청산
    2. 매수일 거래량을 넘는 거래량이 나올 시 청산
    3. SMA 20일선 이탈 시 청산
    4. 위꼬리가 너무 긴 양봉이 나올 경우 청산 (양봉이면서 고가 대비 현재가가 7% 이상 차이)
    """

    # 파라미터 설정
    min_price = 2000                # 최소 거래 가격 (2000원)
    max_price = 300000              # 최대 거래 가격 (30만원)
    volume_multiplier_min = 4.0     # 거래량 증가율 최소 (400%)
    volume_multiplier_max = 20.0    # 거래량 증가율 최대 (2000%)
    min_volume = 3000000            # 최소 거래량 (300만개)
    max_upper_tail_ratio_entry = 0.05   # 최대 위꼬리 비율 - 진입 (고가 대비 5%)
    max_upper_tail_ratio_exit = 0.07    # 최대 위꼬리 비율 - 청산 (고가 대비 7%)
    ema_short_period = 20           # EMA 단기 기간 (20일, 역배열 체크용)
    ema_period = 60                 # EMA 중기 기간 (60일, 역배열 체크용)
    sma_exit_period = 20            # SMA 청산 기간 (20일, 청산 조건용)
    price_limit_pct = 0.22          # 급등 제외 비율 (22%)
    max_ema_deviation_pct = 0.20    # EMA 20일선 최대 이격률 (20%)

    def init(self):
        """전략 초기화"""
        # EMA 20일선 계산 (역배열 체크용)
        self.ema_short = self.I(lambda x: pd.Series(x).ewm(span=self.ema_short_period, adjust=False).mean(), self.data.Close)

        # EMA 60일선 계산 (역배열 체크용)
        self.ema = self.I(lambda x: pd.Series(x).ewm(span=self.ema_period, adjust=False).mean(), self.data.Close)

        # SMA 20일선 계산 (청산 조건용)
        self.sma_exit = self.I(lambda x: pd.Series(x).rolling(window=self.sma_exit_period).mean(), self.data.Close)

        # 진입 시 정보 저장 (매도 기준용)
        self.entry_open_price = None  # 매수일 시가 (청산 조건 판단용)
        self.entry_volume = None      # 매수일 거래량 (청산 조건 판단용)

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
            self._check_sell_signal(close, open_price, high, volume)
            return

        # 포지션이 없으면 매수 조건 체크
        self._check_buy_signal(close, open_price, high, low, prev_open, volume, prev_volume)

    def _check_buy_signal(self, close, open_price, high, low, prev_open, volume, prev_volume):
        """
        매수 시그널 체크

        조건:
        1. 당일 거래량이 전일 거래량 대비 400% 이상, 2000% 이하 증가
        2. 양봉이어야 함 (종가 > 시가)
        3. 거래량이 300만개 이상
        4. 위꼬리가 너무 길지 않음 (고가 대비 종가가 5% 이상 차이나지 않음)

        매수 제외 조건:
        1. 주가 2000원 이하
        2. 주가 30만원 이상
        3. EMA 20, 60일선 역배열
        4. 22% 이상 상승
        5. EMA 20일선과 종가의 이격이 20% 이상일 경우
        """
        # 매수 제외 조건 - 주가 범위 (2000원 초과, 30만원 미만)
        if close <= self.min_price or close >= self.max_price:
            return

        # 양봉 확인 (종가 > 시가)
        if close <= open_price:
            return

        # 급등 제외 (22% 이상 상승)
        gain_pct = (close - open_price) / open_price if open_price > 0 else 0
        if gain_pct >= self.price_limit_pct:
            return

        # 전일 거래량이 0이면 계산 불가
        if prev_volume == 0:
            return

        # 거래량 증가율 확인 (400% 이상, 2000% 이하)
        volume_ratio = volume / prev_volume
        if volume_ratio < self.volume_multiplier_min or volume_ratio > self.volume_multiplier_max:
            return

        # 거래량 절대값 확인 (300만개 이상)
        if volume < self.min_volume:
            return

        # EMA 역배열 제외 (EMA 20 < EMA 60이면 매수 안함)
        if len(self.ema_short) > 0 and len(self.ema) > 0:
            if self.ema_short[-1] < self.ema[-1]:
                return

        # EMA 20일선 이격률 체크 (20% 이상 이격되면 매수 안함)
        # 이격률 = (종가 - EMA 20) / EMA 20
        if len(self.ema_short) > 0 and self.ema_short[-1] > 0:
            ema_deviation = (close - self.ema_short[-1]) / self.ema_short[-1]
            if ema_deviation >= self.max_ema_deviation_pct:
                return

        # 위꼬리 길이 체크 (고가 대비 종가가 5% 이상 차이나면 매수 안함)
        # 위꼬리 비율 = (고가 - 종가) / 고가
        upper_tail_ratio = (high - close) / high if high > 0 else 0
        if upper_tail_ratio > self.max_upper_tail_ratio_entry:
            return

        # 모든 조건 만족 시 매수
        self.buy()
        self.entry_open_price = open_price  # 매수일 시가 저장 (청산 조건 판단용)
        self.entry_volume = volume          # 매수일 거래량 저장 (청산 조건 판단용)

    def _check_sell_signal(self, close, open_price, high, volume):
        """
        매도 시그널 체크 (우선순위 순서)

        조건:
        1. 매수일 시가 이탈 시 청산 (현재 종가 < 매수일 시가)
        2. 매수일 거래량을 넘는 거래량이 나올 시 청산 (현재 거래량 > 매수일 거래량)
        3. SMA 20일선 이탈 시 청산 (현재 종가 < SMA 20일선)
        4. 위꼬리가 너무 긴 양봉이 나올 경우 청산 (양봉이면서 고가 대비 현재가가 7% 이상 차이)
        """
        # 우선순위 1: 매수일 시가 이탈 시 청산
        if self.entry_open_price is not None and close < self.entry_open_price:
            self.position.close()
            self.entry_open_price = None
            self.entry_volume = None
            return

        # 우선순위 2: 매수일 거래량을 넘는 거래량이 나올 시 청산
        if self.entry_volume is not None and volume > self.entry_volume:
            self.position.close()
            self.entry_open_price = None
            self.entry_volume = None
            return

        # 우선순위 3: SMA 20일선 이탈 시 청산
        if len(self.sma_exit) > 0 and close < self.sma_exit[-1]:
            self.position.close()
            self.entry_open_price = None
            self.entry_volume = None
            return

        # 우선순위 4: 위꼬리가 너무 긴 양봉이 나올 경우 청산 (양봉이면서 고가 대비 현재가가 7% 이상 차이)
        # 양봉일 때만 체크 (종가 > 시가)
        if close > open_price:
            upper_tail_ratio = (high - close) / high if high > 0 else 0
            if upper_tail_ratio > self.max_upper_tail_ratio_exit:
                self.position.close()
                self.entry_open_price = None
                self.entry_volume = None
                return