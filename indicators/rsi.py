"""
RSI (Relative Strength Index) 계산

RSI는 과매수/과매도 상태를 판단하는 모멘텀 지표입니다.
- 0~100 사이의 값
- 70 이상: 과매수 (Overbought)
- 30 이하: 과매도 (Oversold)
"""
from typing import List


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    RSI (Relative Strength Index) 계산

    Args:
        prices: 가격 리스트
        period: RSI 기간 (기본값: 14)

    Returns:
        RSI 값 (0~100)

    Raises:
        ValueError: period가 양수가 아니거나 데이터가 부족할 때
    """
    # TODO: TDD로 구현
    raise NotImplementedError("RSI calculation not implemented yet")