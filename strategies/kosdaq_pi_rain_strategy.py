"""
코스닥피 레인 전략 (Kosdaq-Pi Rain Strategy)

4개 ETF 변동성 돌파 전략:
- KODEX 코스닥150레버리지 (233740)
- KODEX 코스닥150선물인버스 (251340)
- KODEX 레버리지 (122630)
- KODEX 200선물인버스2X (252670)

각 ETF는 1/4 비중으로 시작하며, 모멘텀 스코어에 따라 코스닥 ETF 비중 조절 (1.3배/0.7배)
슬리피지: 0.15% (수수료 + 세금)
"""

from backtesting import Strategy
import pandas as pd
import numpy as np


# ============================================================
# 코스닥150레버리지 (233740) - 변동성 돌파 전략
# ============================================================

def calculate_k_value_for_buy(data: pd.DataFrame, current_idx: int = -1) -> float:
    """
    매수용 K값 계산

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        K값 (0.3 또는 0.4)
        - 현재가가 60일선 위: 0.3
        - 현재가가 60일선 아래: 0.4
    """
    if len(data) < 60:
        raise ValueError("Not enough data to calculate 60-day EMA")

    # 60일 EMA 계산
    ema_60 = data['Close'].ewm(span=60, adjust=False).mean()

    current_close = data.iloc[current_idx]['Close']
    current_ema_60 = ema_60.iloc[current_idx]

    # 현재가가 60일선 위면 0.3, 아니면 0.4
    if current_close > current_ema_60:
        return 0.3
    else:
        return 0.4


def check_kosdaq150_lev_buy_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    코스닥150레버리지 매수 신호 확인

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        매수 신호 여부 (True/False)

    조건:
        1. 기본 필터: (시가 > 전일 저가) OR (전일 종가 > 10일 이동평균)
        2. K값 결정: 현재가 기준 60일선 위 = 0.3, 60일선 아래 = 0.4
        3. 목표가 = 금일 시가 + (전일 고가 - 전일 저가) × K
        4. 장중 목표가 상향 돌파시 매수
    """
    if len(data) < 11:  # 최소 11일 필요 (10일 이평 + 전일 + 금일)
        return False

    if len(data) < 60:  # 60일 EMA 계산 불가
        return False

    # 현재 데이터
    current = data.iloc[current_idx]
    prev = data.iloc[current_idx - 1]

    # 1. 기본 필터 확인
    # 조건 A: 시가 > 전일 저가
    filter_a = current['Open'] > prev['Low']

    # 조건 B: 전일 종가 > 10일 이동평균
    ma_10 = data['Close'].rolling(window=10).mean()
    prev_ma_10 = ma_10.iloc[current_idx - 1]
    filter_b = prev['Close'] > prev_ma_10

    # 기본 필터: A OR B
    if not (filter_a or filter_b):
        return False

    # 2. K값 계산
    k_value = calculate_k_value_for_buy(data, current_idx)

    # 3. 목표가 계산
    prev_range = prev['High'] - prev['Low']
    target_price = current['Open'] + (prev_range * k_value)

    # 4. 목표가 돌파 확인 (장중 고가가 목표가 이상)
    if current['High'] >= target_price:
        return True

    return False


def calculate_k_value_for_sell(data: pd.DataFrame, current_idx: int = -1) -> float:
    """
    매도용 K값 계산 (매수와 반대)

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        K값 (0.3 또는 0.4)
        - 현재가가 60일선 위: 0.4 (매수는 0.3)
        - 현재가가 60일선 아래: 0.3 (매수는 0.4)
    """
    if len(data) < 60:
        raise ValueError("Not enough data to calculate 60-day EMA")

    # 60일 EMA 계산
    ema_60 = data['Close'].ewm(span=60, adjust=False).mean()

    current_close = data.iloc[current_idx]['Close']
    current_ema_60 = ema_60.iloc[current_idx]

    # 현재가가 60일선 위면 0.4, 아니면 0.3 (매수와 반대)
    if current_close > current_ema_60:
        return 0.4
    else:
        return 0.3


def check_kosdaq150_lev_sell_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    코스닥150레버리지 매도 신호 확인

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        매도 신호 여부 (True/False)

    조건:
        1. K값 결정: 현재가 기준 60일선 위 = 0.4, 60일선 아래 = 0.3 (매수와 반대)
        2. 목표가 = 금일 시가 - (전일 고가 - 전일 저가) × K
        3. 장중 목표가 하향 돌파시 매도
    """
    if len(data) < 2:  # 최소 2일 필요 (전일 + 금일)
        return False

    if len(data) < 60:  # 60일 EMA 계산 불가
        return False

    # 현재 데이터
    current = data.iloc[current_idx]
    prev = data.iloc[current_idx - 1]

    # 1. K값 계산 (매수와 반대)
    k_value = calculate_k_value_for_sell(data, current_idx)

    # 2. 목표가 계산
    prev_range = prev['High'] - prev['Low']
    target_price = current['Open'] - (prev_range * k_value)

    # 3. 목표가 하향 돌파 확인 (장중 저가가 목표가 이하)
    if current['Low'] <= target_price:
        return True

    return False


# ============================================================
# 코스닥150선물인버스 (251340) - 변동성 돌파 전략
# ============================================================

def check_kosdaq150_inv_buy_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    코스닥150선물인버스 매수 신호 확인

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        매수 신호 여부 (True/False)

    조건:
        1. 기본 필터: 전일 종가 > 20일 이동평균
        2. K값 = 0.4 (고정)
        3. 목표가 = 금일 시가 + (전일 고가 - 전일 저가) × 0.4
        4. 장중 목표가 상향 돌파시 매수
    """
    if len(data) < 21:  # 최소 21일 필요 (20일 이평 + 금일)
        return False

    # 현재 데이터
    current = data.iloc[current_idx]
    prev = data.iloc[current_idx - 1]

    # 1. 기본 필터 확인: 전일 종가 > 20일 이동평균
    ma_20 = data['Close'].rolling(window=20).mean()
    prev_ma_20 = ma_20.iloc[current_idx - 1]

    if prev['Close'] <= prev_ma_20:
        return False

    # 2. K값 = 0.4 (고정)
    k_value = 0.4

    # 3. 목표가 계산
    prev_range = prev['High'] - prev['Low']
    target_price = current['Open'] + (prev_range * k_value)

    # 4. 목표가 돌파 확인 (장중 고가가 목표가 이상)
    if current['High'] >= target_price:
        return True

    return False


def check_kosdaq150_inv_sell_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    코스닥150선물인버스 매도 신호 확인

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        매도 신호 여부 (True/False)

    조건:
        1. K값 = 0.4 (고정)
        2. 목표가 = 금일 시가 - (전일 고가 - 전일 저가) × 0.4
        3. 장중 목표가 하향 돌파시 매도
    """
    if len(data) < 2:  # 최소 2일 필요 (전일 + 금일)
        return False

    # 현재 데이터
    current = data.iloc[current_idx]
    prev = data.iloc[current_idx - 1]

    # 1. K값 = 0.4 (고정)
    k_value = 0.4

    # 2. 목표가 계산
    prev_range = prev['High'] - prev['Low']
    target_price = current['Open'] - (prev_range * k_value)

    # 3. 목표가 하향 돌파 확인 (장중 저가가 목표가 이하)
    if current['Low'] <= target_price:
        return True

    return False


# ============================================================
# 레버리지 (122630) - 이격도 + RSI 전략
# ============================================================

def check_kospi200_lev_buy_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    KODEX 레버리지 (122630) 매수 신호 확인

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        매수 신호 여부 (True/False)

    조건:
        1. 전전일 저가 < 전일 저가
        2. 20일 이동평균선 이격도 < 98 OR > 106
        3. 전일 종가 기준 RSI < 80
        4. 조건 만족시 장 시작 후 매수
    """
    # RSI 계산을 위해 최소 15일 + 20일 이평선 + 전전일 + 전일 = 최소 22일 필요
    if len(data) < 22:
        return False

    # 현재 데이터
    current = data.iloc[current_idx]
    prev = data.iloc[current_idx - 1]
    prev_prev = data.iloc[current_idx - 2]

    # 1. 전전일 저가 < 전일 저가
    if prev_prev['Low'] >= prev['Low']:
        return False

    # 2. 20일 이동평균선 이격도 계산
    ma_20 = data['Close'].rolling(window=20).mean()
    prev_ma_20 = ma_20.iloc[current_idx - 1]
    prev_close = prev['Close']

    # 이격도 = (현재가 / 이동평균) * 100
    disparity = (prev_close / prev_ma_20) * 100

    # 이격도가 98 미만 또는 106 초과가 아니면 매수 안함
    if not (disparity < 98 or disparity > 106):
        return False

    # 3. 전일 종가 기준 RSI < 80
    # RSI 계산을 위해 전일까지의 종가 데이터 사용
    from indicators.rsi import calculate_rsi

    # 전일까지의 종가 데이터 (current_idx - 1까지)
    close_prices = data['Close'].iloc[:current_idx].tolist()

    # RSI 계산 (14일 기준)
    try:
        rsi = calculate_rsi(close_prices, period=14)
    except ValueError:
        # RSI 계산 실패 시 매수 안함
        return False

    if rsi >= 80:
        return False

    # 모든 조건 만족 → 매수
    return True


def check_kospi200_lev_sell_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    KODEX 레버리지 (122630) 매도 신호 확인

    홀딩 조건:
        1. (전전일 저가 < 전일 저가 OR 전일 거래량 < 최근 3일 평균 거래량)
        2. AND (20일 이격도 < 98 OR > 106)

    Returns:
        True: 매도
        False: 홀딩 (매도 안함)
    """
    # 최소 데이터 확인: 20일 이평 + 전전일 + 전일 + 최근 3일 평균 계산용
    if len(data) < 22:
        return True  # 데이터 부족 시 매도 (안전 장치)

    current = data.iloc[current_idx]
    prev = data.iloc[current_idx - 1]
    prev_prev = data.iloc[current_idx - 2]

    # 조건 1-A: 전전일 저가 < 전일 저가
    lows_increasing = prev_prev['Low'] < prev['Low']

    # 조건 1-B: 전일 거래량 < 최근 3일 평균 거래량
    # 최근 3일 (idx -4, -3, -2)
    recent_3_volumes = data['Volume'].iloc[current_idx - 4:current_idx - 1].mean()
    prev_volume = prev['Volume']
    volume_decreasing = prev_volume < recent_3_volumes

    # 조건 1: 저가 상승 OR 거래량 감소
    condition_1 = lows_increasing or volume_decreasing

    # 조건 2: 20일 이격도 극단값
    ma_20 = data['Close'].rolling(window=20).mean()
    prev_ma_20 = ma_20.iloc[current_idx - 1]
    prev_close = prev['Close']
    disparity = (prev_close / prev_ma_20) * 100

    condition_2 = (disparity < 98) or (disparity > 106)

    # 홀딩 조건: 조건1 AND 조건2
    should_hold = condition_1 and condition_2

    # 홀딩하면 False (매도 안함), 아니면 True (매도)
    return not should_hold


# =============================================================================
# KODEX 200선물인버스2X (252670) 전략 함수
# =============================================================================

def check_kospi200_inv2x_buy_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    KODEX 200선물인버스2X (252670) 매수 신호 확인

    매수 조건 (7개 조건 모두 만족):
        1. 전일 종가 > (3일선, 6일선, 19일선, 60일선)
        2. 60일선 증가 중 (전전일 60일선 < 전일 60일선)
        3. 정배열: 3일선 > 6일선 > 19일선
        4. 전일 종가 기준 RSI < 70
        5. 전전일 RSI < 전일 RSI
        6. 전전일 거래량 < 전일 거래량
        7. 전전일 저가 < 전일 저가

    Args:
        data: OHLCV 데이터
        current_idx: 현재 인덱스 (기본값: -1, 마지막 데이터)

    Returns:
        True: 매수 신호 발생
        False: 매수 안함
    """
    # 최소 데이터 확인: 60일선 + RSI 14일 + 전전일 + 전일
    if len(data) < 77:  # 60 + 14 + 3 (margin)
        return False

    prev = data.iloc[current_idx - 1]  # 전일
    prev_prev = data.iloc[current_idx - 2]  # 전전일

    # 조건 1: 전일 종가 > (3일선, 6일선, 19일선, 60일선)
    sma_3 = data['Close'].rolling(window=3).mean()
    sma_6 = data['Close'].rolling(window=6).mean()
    sma_19 = data['Close'].rolling(window=19).mean()
    sma_60 = data['Close'].rolling(window=60).mean()

    prev_sma_3 = sma_3.iloc[current_idx - 1]
    prev_sma_6 = sma_6.iloc[current_idx - 1]
    prev_sma_19 = sma_19.iloc[current_idx - 1]
    prev_sma_60 = sma_60.iloc[current_idx - 1]

    prev_close = prev['Close']

    if not (prev_close > prev_sma_3 and
            prev_close > prev_sma_6 and
            prev_close > prev_sma_19 and
            prev_close > prev_sma_60):
        return False

    # 조건 2: 60일선 증가 중 (전전일 60일선 < 전일 60일선)
    prev_prev_sma_60 = sma_60.iloc[current_idx - 2]
    if prev_prev_sma_60 >= prev_sma_60:
        return False

    # 조건 3: 정배열: 3일선 > 6일선 > 19일선
    if not (prev_sma_3 > prev_sma_6 and prev_sma_6 > prev_sma_19):
        return False

    # 조건 4: 전일 종가 기준 RSI < 70
    from indicators.rsi import calculate_rsi

    close_prices_prev = data['Close'].iloc[:current_idx].tolist()
    try:
        prev_rsi = calculate_rsi(close_prices_prev, period=14)
    except ValueError:
        return False

    if prev_rsi >= 70:
        return False

    # 조건 5: 전전일 RSI < 전일 RSI
    close_prices_prev_prev = data['Close'].iloc[:current_idx - 1].tolist()
    try:
        prev_prev_rsi = calculate_rsi(close_prices_prev_prev, period=14)
    except ValueError:
        return False

    if prev_prev_rsi >= prev_rsi:
        return False

    # 조건 6: 전전일 거래량 < 전일 거래량
    if prev_prev['Volume'] >= prev['Volume']:
        return False

    # 조건 7: 전전일 저가 < 전일 저가
    if prev_prev['Low'] >= prev['Low']:
        return False

    # 모든 조건 만족
    return True


def check_kospi200_inv2x_sell_signal(data: pd.DataFrame, current_idx: int = -1) -> bool:
    """
    KODEX 200선물인버스2X (252670) 매도 신호 확인

    매도 조건:
        - IF 11일 이동평균선 이격도 > 105: 전일 종가 < 3일선 → 매도
        - IF 11일 이동평균선 이격도 ≤ 105: 전일 종가 < 6일선 AND 전일 종가 < 19일선 → 매도

    Args:
        data: OHLCV 데이터
        current_idx: 현재 인덱스 (기본값: -1, 마지막 데이터)

    Returns:
        True: 매도 신호 발생
        False: 매도 안함
    """
    # 최소 데이터 확인: 19일선 필요
    if len(data) < 20:
        return False

    prev = data.iloc[current_idx - 1]  # 전일
    prev_close = prev['Close']

    # 11일 이동평균선 계산
    sma_11 = data['Close'].rolling(window=11).mean()
    prev_sma_11 = sma_11.iloc[current_idx - 1]

    # 11일 이동평균선 이격도 = (전일 종가 / 11일선) * 100
    disparity_11 = (prev_close / prev_sma_11) * 100

    # 조건 1: 11일 이격도 > 105인 경우
    if disparity_11 > 105:
        # 3일선 계산
        sma_3 = data['Close'].rolling(window=3).mean()
        prev_sma_3 = sma_3.iloc[current_idx - 1]

        # 전일 종가 < 3일선 → 매도
        if prev_close < prev_sma_3:
            return True
        else:
            return False

    # 조건 2: 11일 이격도 ≤ 105인 경우
    else:
        # 6일선, 19일선 계산
        sma_6 = data['Close'].rolling(window=6).mean()
        sma_19 = data['Close'].rolling(window=19).mean()

        prev_sma_6 = sma_6.iloc[current_idx - 1]
        prev_sma_19 = sma_19.iloc[current_idx - 1]

        # 전일 종가 < 6일선 AND 전일 종가 < 19일선 → 매도
        if prev_close < prev_sma_6 and prev_close < prev_sma_19:
            return True
        else:
            return False


class Kosdaq150LevStrategy(Strategy):
    """
    코스닥150레버리지 (233740) 전략

    변동성 돌파 전략 with 동적 K값
    """

    commission = 0.0015  # 슬리피지 0.15%

    def init(self):
        """전략 초기화"""
        pass

    def next(self):
        """매 봉마다 실행되는 전략 로직"""
        # 데이터를 DataFrame으로 변환
        data = pd.DataFrame({
            'Open': self.data.Open,
            'High': self.data.High,
            'Low': self.data.Low,
            'Close': self.data.Close,
            'Volume': self.data.Volume
        })

        current_idx = len(data) - 1

        # 포지션이 없으면 매수 신호 확인
        if not self.position:
            if check_kosdaq150_lev_buy_signal(data, current_idx):
                self.buy()
        # 포지션이 있으면 매도 신호 확인
        else:
            if check_kosdaq150_lev_sell_signal(data, current_idx):
                self.position.close()


class Kosdaq150InvStrategy(Strategy):
    """
    코스닥150선물인버스 (251340) 전략

    변동성 돌파 전략 with K=0.4 고정
    """

    commission = 0.0015  # 슬리피지 0.15%

    def init(self):
        """전략 초기화"""
        pass

    def next(self):
        """매 봉마다 실행되는 전략 로직"""
        data = pd.DataFrame({
            'Open': self.data.Open,
            'High': self.data.High,
            'Low': self.data.Low,
            'Close': self.data.Close,
            'Volume': self.data.Volume
        })

        current_idx = len(data) - 1

        if not self.position:
            if check_kosdaq150_inv_buy_signal(data, current_idx):
                self.buy()
        else:
            if check_kosdaq150_inv_sell_signal(data, current_idx):
                self.position.close()


class Kospi200LevStrategy(Strategy):
    """
    KODEX 레버리지 (122630) 전략

    이격도 + RSI 전략
    """

    commission = 0.0015  # 슬리피지 0.15%

    def init(self):
        """전략 초기화"""
        pass

    def next(self):
        """매 봉마다 실행되는 전략 로직"""
        data = pd.DataFrame({
            'Open': self.data.Open,
            'High': self.data.High,
            'Low': self.data.Low,
            'Close': self.data.Close,
            'Volume': self.data.Volume
        })

        current_idx = len(data) - 1

        if not self.position:
            if check_kospi200_lev_buy_signal(data, current_idx):
                self.buy()
        else:
            if check_kospi200_lev_sell_signal(data, current_idx):
                self.position.close()


class Kospi200Inv2xStrategy(Strategy):
    """
    KODEX 200선물인버스2X (252670) 전략

    다중 조건 전략 (7개 조건)
    """

    commission = 0.0015  # 슬리피지 0.15%

    def init(self):
        """전략 초기화"""
        pass

    def next(self):
        """매 봉마다 실행되는 전략 로직"""
        data = pd.DataFrame({
            'Open': self.data.Open,
            'High': self.data.High,
            'Low': self.data.Low,
            'Close': self.data.Close,
            'Volume': self.data.Volume
        })

        current_idx = len(data) - 1

        if not self.position:
            if check_kospi200_inv2x_buy_signal(data, current_idx):
                self.buy()
        else:
            if check_kospi200_inv2x_sell_signal(data, current_idx):
                self.position.close()


# ============================================================
# 모멘텀 스코어 계산 함수 (전략 외부 - 테스트 가능)
# ============================================================

def calculate_momentum_score1(data: pd.DataFrame, current_idx: int = -1) -> float:
    """
    모멘텀 스코어1 계산 (장기추세)

    100일 평균 모멘텀 (10일마다 측정):
    - 10일 전 대비 현재 등락률
    - 20일 전 대비 현재 등락률
    - 30일 전 대비 현재 등락률
    - ...
    - 100일 전 대비 현재 등락률
    → 이 10개의 등락률 평균

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        모멘텀 스코어1 (장기추세 등락률 평균, %)

    Raises:
        ValueError: 데이터 부족 시
    """
    if len(data) < 101:  # current_idx까지 포함하여 최소 101일 필요
        raise ValueError("Not enough data to calculate momentum score1 (need at least 101 days)")

    current_close = data.iloc[current_idx]['Close']

    # 10일마다 등락률 계산 (10일, 20일, 30일, ..., 100일)
    momentum_values = []
    for days_ago in range(10, 101, 10):  # 10, 20, 30, ..., 100
        past_close = data.iloc[current_idx - days_ago]['Close']
        # 등락률 = (현재 - 과거) / 과거 × 100
        momentum = ((current_close - past_close) / past_close) * 100
        momentum_values.append(momentum)

    # 평균 등락률 반환
    return np.mean(momentum_values)


def calculate_momentum_score2(data: pd.DataFrame, current_idx: int = -1) -> float:
    """
    모멘텀 스코어2 계산 (단기추세)

    20일간 등락률의 이동평균선:
    - 각 날짜의 등락률 = (당일 종가 - 전일 종가) / 전일 종가 × 100
    - 최근 20일간의 등락률들의 평균

    Args:
        data: OHLCV 데이터프레임
        current_idx: 현재 인덱스 (기본값: -1, 마지막)

    Returns:
        모멘텀 스코어2 (단기추세 등락률 평균, %)

    Raises:
        ValueError: 데이터 부족 시
    """
    if len(data) < 21:  # 20일 + 1일 (등락률 계산을 위해 전일 필요)
        raise ValueError("Not enough data to calculate momentum score2 (need at least 21 days)")

    # 등락률 계산: (종가[i] - 종가[i-1]) / 종가[i-1] × 100
    # current_idx가 -1이면 전체 데이터를 사용, 아니면 :current_idx+1까지 사용
    if current_idx == -1:
        close_prices = data['Close']
    else:
        close_prices = data['Close'].iloc[:current_idx+1]

    daily_returns = close_prices.pct_change() * 100  # pct_change()는 자동으로 (현재-전일)/전일 계산

    # NaN 제거 (첫 번째 값)
    daily_returns = daily_returns.dropna()

    # 최근 20일간의 등락률 평균
    recent_20_returns = daily_returns.iloc[-20:]
    return recent_20_returns.mean()


def calculate_weight_adjustment(
    leverage_score1: float,
    leverage_score2: float,
    inverse_score1: float,
    inverse_score2: float
) -> tuple[float, float]:
    """
    코스닥 ETF 비중 조절 계산

    규칙:
    - IF 레버리지의 스코어1, 스코어2 모두 > 인버스: 레버리지 × 1.3, 인버스 × 0.7
    - ELSE: 레버리지 × 0.7, 인버스 × 1.3

    Args:
        leverage_score1: 레버리지 모멘텀 스코어1 (장기추세)
        leverage_score2: 레버리지 모멘텀 스코어2 (단기추세)
        inverse_score1: 인버스 모멘텀 스코어1 (장기추세)
        inverse_score2: 인버스 모멘텀 스코어2 (단기추세)

    Returns:
        (leverage_weight, inverse_weight) 튜플
    """
    # 레버리지의 두 스코어가 모두 인버스보다 높으면 레버리지 우세
    if leverage_score1 > inverse_score1 and leverage_score2 > inverse_score2:
        return (1.3, 0.7)
    else:
        # 그 외의 경우 인버스 우세
        return (0.7, 1.3)