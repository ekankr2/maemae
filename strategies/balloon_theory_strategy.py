import sys
sys.path.append('..')

from backtesting import Strategy
import pandas as pd


class BalloonTheoryStrategy(Strategy):
    min_price = 1500
    max_price = 300000
    min_gain_pct = 0.04
    volume_multiplier_min = 4.0
    min_volume = 1000000
    max_upper_tail_ratio_entry = 0.06
    max_upper_tail_ratio_exit = 0.08
    ema_short_period = 112
    min_market_cap = 300_000_000_000

    def init(self):
        self.ema_short = self.I(lambda x: pd.Series(x).ewm(span=self.ema_short_period, adjust=False).mean(), self.data.Close)
        self.entry_open_price = None
        self.entry_close_price = None
        self.entry_volume = None
        self.entry_day_count = 0

    def next(self):
        if len(self.data.Close) < 2:
            return

        close = self.data.Close[-1]
        open_price = self.data.Open[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        prev_close = self.data.Close[-2]
        prev_open = self.data.Open[-2]
        volume = self.data.Volume[-1]
        prev_volume = self.data.Volume[-2]

        if self.position:
            self.entry_day_count += 1
            self._check_sell_signal(close, open_price, high, volume)
            return

        self._check_buy_signal(close, open_price, high, low, prev_open, volume, prev_volume)

    def _check_buy_signal(self, close, open_price, high, low, prev_open, volume, prev_volume):
        if close <= self.min_price or close >= self.max_price:
            return
        if close <= open_price:
            return

        gain_pct = (close - open_price) / open_price if open_price > 0 else 0
        if gain_pct < self.min_gain_pct:
            return

        if prev_volume == 0:
            return
        volume_ratio = volume / prev_volume
        if volume_ratio < self.volume_multiplier_min:
            return
        if volume < self.min_volume:
            return

        # 현재가가 EMA 112일선 위에 있어야 함
        if len(self.ema_short) > 0:
            if close <= self.ema_short[-1]:
                return

        upper_tail_ratio = (high - close) / high if high > 0 else 0
        if upper_tail_ratio > self.max_upper_tail_ratio_entry:
            return

        # 시가총액 체크 - MarketCap이 없거나 0이거나 조건 미달이면 제외
        if not hasattr(self.data, 'MarketCap') or len(self.data.MarketCap) == 0:
            return
        if self.data.MarketCap[-1] <= 0 or self.data.MarketCap[-1] < self.min_market_cap:
            return

        self.buy()
        self.entry_open_price = open_price
        self.entry_close_price = close
        self.entry_volume = volume
        self.entry_day_count = 0

    def _check_sell_signal(self, close, open_price, high, volume):
        # Priority 1: 매수일 시가 이탈
        if self.entry_open_price is not None and close < self.entry_open_price:
            self.position.close()
            self.entry_open_price = None
            self.entry_close_price = None
            self.entry_volume = None
            self.entry_day_count = 0
            return

        # Priority 2: 매수일 거래량 초과
        if self.entry_volume is not None and volume > self.entry_volume:
            self.position.close()
            self.entry_open_price = None
            self.entry_close_price = None
            self.entry_volume = None
            self.entry_day_count = 0
            return

        # Priority 3: 전일 시가 이탈
        if len(self.data.Open) >= 2 and close < self.data.Open[-2]:
            self.position.close()
            self.entry_open_price = None
            self.entry_close_price = None
            self.entry_volume = None
            self.entry_day_count = 0
            return

        # Priority 4: 위꼬리가 너무 긴 양봉 (8% 이상)
        if close > open_price:
            upper_tail_ratio = (high - close) / high if high > 0 else 0
            if upper_tail_ratio > self.max_upper_tail_ratio_exit:
                self.position.close()
                self.entry_open_price = None
                self.entry_close_price = None
                self.entry_volume = None
                self.entry_day_count = 0
                return

        # Priority 5: 매수일 바로 다음날 inside bar 음봉
        if self.entry_day_count == 1 and self.entry_open_price is not None and self.entry_close_price is not None:
            # 음봉 체크
            is_bearish = close < open_price

            if is_bearish:
                # 매수일 몸통 범위
                entry_body_low = min(self.entry_open_price, self.entry_close_price)
                entry_body_high = max(self.entry_open_price, self.entry_close_price)

                # 오늘 몸통 범위
                today_body_low = min(open_price, close)
                today_body_high = max(open_price, close)

                # Inside bar 체크 (오늘 몸통이 매수일 몸통 안에 완전히 포함)
                is_inside_bar = (today_body_low >= entry_body_low and today_body_high <= entry_body_high)

                if is_inside_bar:
                    self.position.close()
                    self.entry_open_price = None
                    self.entry_close_price = None
                    self.entry_volume = None
                    self.entry_day_count = 0
                    return