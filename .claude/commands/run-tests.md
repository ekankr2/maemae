---
description: "Run tests with pytest"
---

Running tests with pytest:

```bash
# 모든 테스트 실행
uv run pytest

# Unit 테스트만 실행 (빠른 테스트)
uv run pytest -m unit

# Integration 테스트 제외
uv run pytest -m "not integration"

# Slow 테스트 제외
uv run pytest -m "not slow"

# 특정 파일만 테스트
uv run pytest tests/test_indicators.py

# 특정 테스트만 실행
uv run pytest tests/test_indicators.py::test_calculate_ma

# Coverage 포함
uv run pytest --cov=. --cov-report=html

# Verbose 모드
uv run pytest -v

# 실패한 테스트만 재실행
uv run pytest --lf
```

Which tests would you like to run?