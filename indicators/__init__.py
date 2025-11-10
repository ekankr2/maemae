"""
기술적 지표 계산 패키지

자동매매에 사용되는 다양한 기술적 지표들을 제공합니다.
모든 지표는 TDD로 작성되어 정확성이 검증되었습니다.
"""

from .moving_average import calculate_moving_average

__all__ = [
    'calculate_moving_average',
]

__version__ = '0.1.0'