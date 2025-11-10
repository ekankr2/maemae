# Technical Indicators Package

자동매매를 위한 기술적 지표 계산 패키지입니다.
모든 지표는 TDD로 작성되어 정확성이 검증되었습니다.

## 구현된 지표

### ✅ Moving Average (이동평균)
```python
from indicators import calculate_moving_average

prices = [100, 102, 101, 103, 104]
ma5 = calculate_moving_average(prices, period=5)
# 결과: 102.0
```

## 구현 예정

### 🚧 RSI (Relative Strength Index)
- 과매수/과매도 판단
- 기본 기간: 14일
- 범위: 0~100

### 🚧 Bollinger Bands (볼린저 밴드)
- 변동성 측정
- 상단/중간/하단 밴드 반환
- 기본 기간: 20일, 2σ

### 🚧 MACD (Moving Average Convergence Divergence)
- 추세 및 모멘텀 판단
- MACD Line, Signal Line, Histogram 반환
- 기본값: 12, 26, 9

### 🚧 EMA (Exponential Moving Average)
- 지수 이동평균
- 최근 가격에 높은 가중치
- MACD 계산에 필요

## 개발 방법

모든 지표는 TDD로 개발합니다:

1. **Red**: 테스트 먼저 작성
   ```bash
   # tests/test_indicators.py에 테스트 추가
   ```

2. **Green**: 테스트 통과하는 최소 코드
   ```bash
   # indicators/rsi.py에 구현
   ```

3. **Refactor**: 코드 개선
   ```bash
   uv run pytest tests/test_indicators.py
   ```

## 테스트 실행

```bash
# 모든 지표 테스트
uv run pytest tests/test_indicators.py -v

# 특정 지표만
uv run pytest tests/test_indicators.py::TestMovingAverage -v

# Unit 테스트만 (빠르게)
uv run pytest -m unit
```

## 사용 예시

```python
from indicators import (
    calculate_moving_average,
    # calculate_rsi,  # TODO
    # calculate_bollinger_bands,  # TODO
)

# 가격 데이터
prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]

# 5일 이동평균
ma5 = calculate_moving_average(prices, period=5)

# 20일 이동평균
ma20 = calculate_moving_average(prices, period=20)

# 매매 신호 (예시)
if ma5 > ma20:
    print("골든 크로스 - 매수 신호")
```

## 기여 가이드

새로운 지표 추가 시:

1. `indicators/<indicator_name>.py` 파일 생성
2. `tests/test_indicators.py`에 테스트 추가
3. TDD 사이클 (Red → Green → Refactor)
4. `indicators/__init__.py`에 export 추가