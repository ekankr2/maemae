"""
EMA (Exponential Moving Average) 계산

EMA는 최근 가격에 더 높은 가중치를 부여하는 이동평균입니다.
SMA보다 가격 변화에 더 빠르게 반응합니다.
"""
from typing import List


def calculate_ema(prices: List[float], period: int) -> float:
    """
    EMA (Exponential Moving Average) 계산

    Args:
        prices: 가격 리스트
        period: EMA 기간

    Returns:
        EMA 값

    Raises:
        ValueError: period가 양수가 아니거나 데이터가 부족할 때
    """
    # TODO: TDD로 구현
    raise NotImplementedError("EMA calculation not implemented yet")