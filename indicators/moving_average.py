"""
기술적 지표 계산 모듈
"""
from typing import List


def calculate_moving_average(prices: List[float], period: int) -> float:
    """
    단순 이동평균(Simple Moving Average) 계산

    Args:
        prices: 가격 리스트
        period: 이동평균 기간

    Returns:
        이동평균 값

    Raises:
        ValueError: period가 양수가 아니거나 데이터가 부족할 때
    """
    # 검증: period는 양수여야 함
    if period <= 0:
        raise ValueError("Period must be positive")

    # 검증: 충분한 데이터가 있어야 함
    if len(prices) < period:
        raise ValueError(f"Not enough data: need {period} prices, got {len(prices)}")

    # 마지막 period개의 평균 계산
    recent_prices = prices[-period:]
    return sum(recent_prices) / period


def calculate_ema(prices: List[float], period: int) -> float:
    """
    지수 이동평균(Exponential Moving Average) 계산

    Args:
        prices: 가격 리스트
        period: 이동평균 기간

    Returns:
        EMA 값 (최근 가격에 더 높은 가중치 적용)

    Raises:
        ValueError: period가 양수가 아니거나 데이터가 부족할 때
    """
    # 검증: period는 양수여야 함
    if period <= 0:
        raise ValueError("Period must be positive")

    # 검증: 충분한 데이터가 있어야 함
    if len(prices) < period:
        raise ValueError(f"Not enough data: need {period} prices, got {len(prices)}")

    # 1. 첫 EMA는 첫 period개의 SMA로 시작
    ema = sum(prices[:period]) / period

    # 2. EMA 승수 계산: 2/(기간+1)
    multiplier = 2.0 / (period + 1)

    # 3. 나머지 데이터에 대해 EMA 계산
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    return ema