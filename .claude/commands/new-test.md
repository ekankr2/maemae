---
description: "Create a new test file from template"
---

I'll help you create a new test file.

**Test File Naming Convention:**
- Unit tests: `tests/test_<module_name>.py`
- Integration tests: `tests/integration/test_<feature>.py`
- Strategy tests: `tests/strategy/test_<strategy_name>.py`

**Test Structure (Given-When-Then):**
```python
@pytest.mark.unit
def test_something():
    # Given: 테스트 준비 (데이터, 상태 설정)

    # When: 테스트 실행 (함수 호출)

    # Then: 결과 검증 (assertion)

```

**Available Markers:**
- `@pytest.mark.unit` - 빠른 단위 테스트
- `@pytest.mark.integration` - API 호출 등 통합 테스트
- `@pytest.mark.slow` - 느린 테스트 (백테스팅 등)
- `@pytest.mark.strategy` - 전략 관련 테스트
- `@pytest.mark.asyncio` - 비동기 테스트

**Example:**
```python
import pytest

@pytest.mark.unit
def test_calculate_moving_average(sample_price_data):
    # Given
    prices = sample_price_data
    period = 5

    # When
    ma = calculate_moving_average(prices, period)

    # Then
    expected = sum(prices[-period:]) / period
    assert ma == pytest.approx(expected)
```

What test file would you like to create?