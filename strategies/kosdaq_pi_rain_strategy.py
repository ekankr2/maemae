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


class KosdaqPiRainStrategy(Strategy):
    """
    코스닥피 레인 포트폴리오 전략

    4개 ETF를 동시에 관리하며, 각 ETF는 독립적인 매수/매도 조건을 가짐
    """

    # 공통 설정
    commission = 0.0015  # 슬리피지 0.15%

    # ETF 코드
    KOSDAQ150_LEV = "233740"      # 코스닥150레버리지
    KOSDAQ150_INV = "251340"      # 코스닥150선물인버스
    KOSPI200_LEV = "122630"       # 레버리지
    KOSPI200_INV = "252670"       # 200선물인버스2X

    def init(self):
        """전략 초기화 - 지표 계산"""
        # TODO: 각 ETF별 필요한 지표들 계산
        # - 이동평균선들 (SMA/EMA)
        # - RSI
        # - 이격도
        # - 모멘텀 스코어
        pass

    def next(self):
        """매 봉마다 실행되는 전략 로직"""
        # TODO:
        # 1. 각 ETF별 매수/매도 신호 확인
        # 2. 모멘텀 스코어 계산
        # 3. 비중 조절 및 리밸런싱
        pass

    # ============================================================
    # 코스닥150레버리지 (233740) - 변동성 돌파
    # ============================================================

    def _check_kosdaq150_lev_buy(self):
        """
        코스닥150레버리지 매수 신호 확인

        조건:
        - 기본 필터: (시가 > 전일 저가) OR (전일 종가 > 10일 이동평균)
        - K값: 60일선 위 = 0.3, 60일선 아래 = 0.4
        - 목표가 = 금일 시가 + (전일 고가 - 전일 저가) × K
        - 장중 목표가 상향 돌파시 매수
        """
        # TODO: 구현
        pass

    def _check_kosdaq150_lev_sell(self):
        """
        코스닥150레버리지 매도 신호 확인

        조건:
        - K값: 60일선 위 = 0.4, 60일선 아래 = 0.3
        - 목표가 = 금일 시가 - (전일 고가 - 전일 저가) × K
        - 장중 목표가 하향 돌파시 매도
        """
        # TODO: 구현
        pass

    # ============================================================
    # 코스닥150선물인버스 (251340) - 변동성 돌파
    # ============================================================

    def _check_kosdaq150_inv_buy(self):
        """
        코스닥150선물인버스 매수 신호 확인

        조건:
        - 기본 필터: 전일 종가 > 20일 이동평균
        - K값 = 0.4
        - 목표가 = 금일 시가 + (전일 고가 - 전일 저가) × 0.4
        - 장중 목표가 상향 돌파시 매수
        """
        # TODO: 구현
        pass

    def _check_kosdaq150_inv_sell(self):
        """
        코스닥150선물인버스 매도 신호 확인

        조건:
        - K값 = 0.4
        - 목표가 = 금일 시가 - (전일 고가 - 전일 저가) × 0.4
        - 장중 목표가 하향 돌파시 매도
        """
        # TODO: 구현
        pass

    # ============================================================
    # 레버리지 (122630) - 이격도 + RSI
    # ============================================================

    def _check_kospi200_lev_buy(self):
        """
        레버리지 매수 신호 확인

        조건:
        - 전전일 저가 < 전일 저가
        - 20일 이동평균선 이격도 < 98 OR > 106
        - 전일 종가 기준 RSI < 80
        - 조건 만족시 장 시작 후 매수
        """
        # TODO: 구현
        pass

    def _check_kospi200_lev_sell(self):
        """
        레버리지 매도 신호 확인 (홀딩 조건)

        조건:
        - (전전일 저가 < 전일 저가 OR 전일 거래량 < 최근 3일 평균)
          AND (20일 이격도 < 98 OR > 106) → 홀딩
        - 위 조건 불만족시 매도
        """
        # TODO: 구현
        pass

    # ============================================================
    # 200선물인버스2X (252670) - 다중 조건
    # ============================================================

    def _check_kospi200_inv_buy(self):
        """
        200선물인버스2X 매수 신호 확인

        조건:
        - 전일 종가 > (3일선, 6일선, 19일선, 60일선)
        - 60일선 증가 중 (전전일 60일선 < 전일 60일선)
        - 정배열: 3일선 > 6일선 > 19일선
        - 전일 종가 기준 RSI < 70
        - 전전일 RSI < 전일 RSI
        - 전전일 거래량 < 전일 거래량
        - 전전일 저가 < 전일 저가
        - 조건 만족시 장 시작 후 매수
        """
        # TODO: 구현
        pass

    def _check_kospi200_inv_sell(self):
        """
        200선물인버스2X 매도 신호 확인

        조건:
        - IF 11일 이동평균선 이격도 > 105: 전일 종가 < 3일선 → 매도
        - IF 11일 이동평균선 이격도 ≤ 105:
          전일 종가 < 6일선 AND 전일 종가 < 19일선 → 매도
        """
        # TODO: 구현
        pass

    # ============================================================
    # 모멘텀 스코어 & 비중 조절
    # ============================================================

    def _calculate_momentum_score(self, prices):
        """
        모멘텀 스코어 계산

        Returns:
            (score1, score2) tuple
            - score1: 100일 평균 모멘텀 (10일마다) - 장기추세
            - score2: 20일간 등락률의 이동평균선 - 단기추세
        """
        # TODO: 구현
        pass

    def _adjust_weights(self):
        """
        코스닥 ETF 비중 조절

        레버리지와 인버스의 모멘텀 스코어를 비교하여:
        - 레버리지 우세: 레버리지 × 1.3, 인버스 × 0.7
        - 인버스 우세: 레버리지 × 0.7, 인버스 × 1.3
        """
        # TODO: 구현
        pass