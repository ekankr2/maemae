import sys
sys.path.append('..')

from backtesting import Strategy
import pandas as pd


class BalloonTheoryStrategy(Strategy):
    min_price = 1500
    max_price = 300000
    min_gain_pct = 0.04
    volume_multiplier_min = 5.0
    min_volume = 3000000
    max_upper_tail_ratio_entry = 0.06
    max_upper_tail_ratio_exit = 0.06
    ema_short_period = 20
    ema_period = 60
    ema_long_period = 112
    min_ema_long_deviation_pct = 0.15
    sma_exit_period = 25
    price_limit_pct = 0.22
    min_market_cap = 120_000_000_000

    def init(self):
        self.ema_short = self.I(lambda x: pd.Series(x).ewm(span=self.ema_short_period, adjust=False).mean(), self.data.Close)
        self.ema = self.I(lambda x: pd.Series(x).ewm(span=self.ema_period, adjust=False).mean(), self.data.Close)
        self.ema_long = self.I(lambda x: pd.Series(x).ewm(span=self.ema_long_period, adjust=False).mean(), self.data.Close)
        self.sma_exit = self.I(lambda x: pd.Series(x).rolling(window=self.sma_exit_period).mean(), self.data.Close)
        self.entry_open_price = None
        self.entry_volume = None
        self.entry_close = None
        self.entry_bar = None

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
        if gain_pct >= self.price_limit_pct:
            return

        if prev_volume == 0:
            return
        volume_ratio = volume / prev_volume
        if volume_ratio < self.volume_multiplier_min:
            return
        if volume < self.min_volume:
            return

        if len(self.ema_short) > 0 and len(self.ema) > 0:
            if self.ema_short[-1] < self.ema[-1]:
                return

        if len(self.ema_long) > 0:
            ema_long_deviation = (open_price - self.ema_long[-1]) / self.ema_long[-1] if self.ema_long[-1] > 0 else 0
            if ema_long_deviation >= self.min_ema_long_deviation_pct:
                return

        upper_tail_ratio = (high - close) / high if high > 0 else 0
        if upper_tail_ratio > self.max_upper_tail_ratio_entry:
            return

        if hasattr(self.data, 'MarketCap') and len(self.data.MarketCap) > 0:
            if self.data.MarketCap[-1] < self.min_market_cap:
                return

        self.buy()
        self.entry_open_price = open_price
        self.entry_volume = volume
        self.entry_close = close
        self.entry_bar = len(self.data)

    def _check_sell_signal(self, close, open_price, high, volume):
        if self.entry_open_price is not None and close < self.entry_open_price:
            self.position.close()
            self.entry_open_price = None
            self.entry_volume = None
            self.entry_close = None
            self.entry_bar = None
            return

        if self.entry_volume is not None and volume > self.entry_volume:
            self.position.close()
            self.entry_open_price = None
            self.entry_volume = None
            self.entry_close = None
            self.entry_bar = None
            return

        if self.entry_bar is not None and len(self.data) == self.entry_bar + 1:
            if close < open_price:
                self.position.close()
                self.entry_open_price = None
                self.entry_volume = None
                self.entry_close = None
                self.entry_bar = None
                return

        if self.entry_bar is not None and len(self.data) == self.entry_bar + 1:
            if self.entry_close is not None and close < self.entry_close:
                self.position.close()
                self.entry_open_price = None
                self.entry_volume = None
                self.entry_close = None
                self.entry_bar = None
                return

        if len(self.sma_exit) > 0 and close < self.sma_exit[-1]:
            self.position.close()
            self.entry_open_price = None
            self.entry_volume = None
            self.entry_close = None
            self.entry_bar = None
            return

        if close > open_price:
            upper_tail_ratio = (high - close) / high if high > 0 else 0
            if upper_tail_ratio > self.max_upper_tail_ratio_exit:
                self.position.close()
                self.entry_open_price = None
                self.entry_volume = None
                self.entry_close = None
                self.entry_bar = None
                return