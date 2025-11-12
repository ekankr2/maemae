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
    # 입력 검증
    if period <= 0:
        raise ValueError("Period must be positive")

    # RSI 계산을 위해서는 period + 1개의 데이터가 필요
    # (첫 번째 값은 변화량 계산에만 사용되므로)
    if len(prices) < period + 1:
        raise ValueError("Not enough data")

    # 가격 변화량 계산
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]

    # 최근 period개의 변화량만 사용
    recent_changes = changes[-period:]

    # 상승폭과 하락폭 분리
    gains = [change if change > 0 else 0 for change in recent_changes]
    losses = [-change if change < 0 else 0 for change in recent_changes]

    # 평균 계산
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # 특별 케이스: 모든 하락폭이 0 (계속 상승)
    if avg_loss == 0:
        return 100.0

    # 특별 케이스: 모든 상승폭이 0 (계속 하락)
    if avg_gain == 0:
        return 0.0

    # RS와 RSI 계산
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi