"""
풍선이론 (Balloon Theory) 전략

거래량 급증 시 상승 모멘텀을 포착하는 전략
- 당일 거래량이 전일 거래량 대비 400% 이상, 1200% 이하 증가 시 매수
- 4% 이상 상승
- EMA 60일선 위
- 양봉이어야 함 (종가 > 시가)
- 주가 1000원 이하 제외
- 주가 30만원 이상 제외
- 거래량 80만개 이상
- 상한가 제외
- 위꼬리가 너무 길 경우 매수하지 않음 (고가 대비 종가가 10% 이상 차이)
- 종가 배팅 (3시 15분에 매수)
- 3 영업일 안에 청산
- 매수일 거래량의 60% 이상의 거래량이 나오면 3 영업일을 연장
- 장 마감 전에 매도 (종가 기준)
"""
import sys
sys.path.append('..')

from backtesting import Strategy
import pandas as pd


class BalloonTheoryStrategy(Strategy):
    """
    풍선이론 전략

    매수 조건:
    1. 당일 거래량이 전일 거래량 대비 400% 이상, 1200% 이하 증가
    2. 4% 이상 상승
    3. EMA 60일선 위
    4. 양봉이어야 함 (종가 > 시가)
    5. 거래량이 80만개 이상
    6. 위꼬리가 너무 길지 않음 (고가 대비 종가가 10% 이상 차이나지 않음)

    매수 제외 조건:
    1. 주가 1000원 이하
    2. 주가 30만원 이상
    3. 상한가

    매도 조건:
    1. 기본 3 영업일 후 청산
    2. 매수일 거래량의 60% 이상 거래량이 나오면 그 시점에서 3 영업일 연장 (무제한 반복)
    """

    # 파라미터 설정
    min_price = 1000                # 최소 거래 가격
    max_price = 300000              # 최대 거래 가격 (30만원)
    min_gain_pct = 0.04             # 최소 상승률 (4%)
    volume_multiplier_min = 4.0     # 거래량 증가율 최소 (400%)
    volume_multiplier_max = 12.0    # 거래량 증가율 최대 (1200%)
    min_volume = 800000             # 최소 거래량 (80만개)
    max_upper_tail_ratio = 0.10     # 최대 위꼬리 비율 (고가 대비 10%)
    ema_period = 60                 # EMA 기간 (60일)
    price_limit_pct = 0.30          # 상한가 비율 (30%)
    base_hold_days = 3              # 기본 보유 기간 (3 영업일)
    volume_extension_ratio = 0.6    # 거래량 연장 조건 (60%)

    def init(self):
        """전략 초기화"""
        # EMA 60일선 계산
        self.ema = self.I(lambda x: pd.Series(x).ewm(span=self.ema_period, adjust=False).mean(), self.data.Close)

        # 진입 시 정보 저장 (매도 기준용)
        self.entry_volume = None      # 매수일 거래량 (연장 조건 판단용)
        self.entry_day_count = None   # 매수 후 경과 영업일 수
        self.hold_days_limit = None   # 청산 기한 (기본 3일, 거래량 유지 시 계속 연장)

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
            self._check_sell_signal(volume)
            return

        # 포지션이 없으면 매수 조건 체크
        self._check_buy_signal(close, open_price, high, low, prev_open, volume, prev_volume)

    def _check_buy_signal(self, close, open_price, high, low, prev_open, volume, prev_volume):
        """
        매수 시그널 체크

        조건:
        1. 당일 거래량이 전일 거래량 대비 400% 이상, 1200% 이하 증가
        2. 4% 이상 상승
        3. EMA 60일선 위
        4. 양봉이어야 함 (종가 > 시가)
        5. 거래량이 80만개 이상
        6. 위꼬리가 너무 길지 않음 (고가 대비 종가가 10% 이상 차이나지 않음)

        매수 제외 조건:
        1. 주가 1000원 이하
        2. 주가 30만원 이상
        3. 상한가
        """
        # 매수 제외 조건 - 주가 범위 (1000원 초과, 30만원 미만)
        if close <= self.min_price or close >= self.max_price:
            return

        # 양봉 확인 (종가 > 시가)
        if close <= open_price:
            return

        # 4% 이상 상승 확인
        gain_pct = (close - open_price) / open_price if open_price > 0 else 0
        if gain_pct < self.min_gain_pct:
            return

        # 상한가 제외 (30% 이상 상승)
        if gain_pct >= self.price_limit_pct:
            return

        # 전일 거래량이 0이면 계산 불가
        if prev_volume == 0:
            return

        # 거래량 증가율 확인 (400% 이상, 1200% 이하)
        volume_ratio = volume / prev_volume
        if volume_ratio < self.volume_multiplier_min or volume_ratio > self.volume_multiplier_max:
            return

        # 거래량 절대값 확인 (80만개 이상)
        if volume < self.min_volume:
            return

        # EMA 60일선 위에 있는지 확인
        if len(self.ema) > 0 and close <= self.ema[-1]:
            return

        # 위꼬리 길이 체크 (고가 대비 종가가 10% 이상 차이나면 매수 안함)
        # 위꼬리 비율 = (고가 - 종가) / 고가
        upper_tail_ratio = (high - close) / high if high > 0 else 0
        if upper_tail_ratio > self.max_upper_tail_ratio:
            return

        # 모든 조건 만족 시 매수
        self.buy()
        self.entry_volume = volume                  # 매수일 거래량 저장 (연장 조건 판단용)
        self.entry_day_count = 0                    # 경과 일수 초기화 (매수일은 0일)
        self.hold_days_limit = self.base_hold_days  # 청산 기한 (기본 3일)

    def _check_sell_signal(self, volume):
        """
        매도 시그널 체크

        조건:
        1. 기본 3 영업일 후 청산
        2. 매수일 거래량의 60% 이상 거래량이 나오면 그 시점에서 3 영업일 연장 (무제한 반복)
        """
        # 경과 일수 증가 (매수일은 0일, 다음 날부터 1일, 2일, 3일...)
        self.entry_day_count += 1

        # 거래량이 매수일 거래량의 60% 이상이면 현재 시점에서 +3일 연장
        if (self.entry_volume is not None and
            volume >= self.entry_volume * self.volume_extension_ratio):
            self.hold_days_limit = self.entry_day_count + self.base_hold_days

        # 청산 기한 도달 시 매도
        if self.entry_day_count >= self.hold_days_limit:
            self.position.close()
            self.entry_volume = None
            self.entry_day_count = None
            self.hold_days_limit = None
            return