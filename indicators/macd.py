"""
MACD (Moving Average Convergence Divergence) 계산

MACD는 추세와 모멘텀을 동시에 판단하는 지표입니다.
- MACD Line: 12일 EMA - 26일 EMA
- Signal Line: MACD의 9일 EMA
- Histogram: MACD - Signal
"""
from typing import List, Tuple


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[float, float, float]:
    """
    MACD 계산

    Args:
        prices: 가격 리스트
        fast_period: 빠른 EMA 기간 (기본값: 12)
        slow_period: 느린 EMA 기간 (기본값: 26)
        signal_period: 시그널 EMA 기간 (기본값: 9)

    Returns:
        (MACD, Signal, Histogram) 튜플

    Raises:
        ValueError: 잘못된 파라미터 또는 데이터 부족
    """
    # TODO: TDD로 구현
    raise NotImplementedError("MACD calculation not implemented yet")