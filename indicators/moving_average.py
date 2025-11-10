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