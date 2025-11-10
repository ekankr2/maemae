"""
볼린저 밴드 (Bollinger Bands) 계산

볼린저 밴드는 가격 변동성을 측정하는 지표입니다.
- 상단 밴드: MA + (2 * 표준편차)
- 중간 밴드: 이동평균
- 하단 밴드: MA - (2 * 표준편차)
"""
from typing import List, Tuple


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    num_std: float = 2.0
) -> Tuple[float, float, float]:
    """
    볼린저 밴드 계산

    Args:
        prices: 가격 리스트
        period: 이동평균 기간 (기본값: 20)
        num_std: 표준편차 배수 (기본값: 2.0)

    Returns:
        (상단밴드, 중간밴드, 하단밴드) 튜플

    Raises:
        ValueError: period가 양수가 아니거나 데이터가 부족할 때
    """
    # TODO: TDD로 구현
    raise NotImplementedError("Bollinger Bands calculation not implemented yet")