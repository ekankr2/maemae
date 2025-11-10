"""
pytest 공통 설정 및 fixture 정의
"""
import pytest
from datetime import datetime
from typing import List, Dict


# ============================================
# Test Data Fixtures
# ============================================

@pytest.fixture
def sample_price_data() -> List[float]:
    """샘플 가격 데이터 (10개)"""
    return [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0]


@pytest.fixture
def sample_ohlcv_data() -> List[Dict]:
    """샘플 OHLCV 데이터"""
    return [
        {"open": 100, "high": 105, "low": 99, "close": 103, "volume": 10000},
        {"open": 103, "high": 107, "low": 102, "close": 106, "volume": 12000},
        {"open": 106, "high": 110, "low": 105, "close": 108, "volume": 15000},
        {"open": 108, "high": 112, "low": 107, "close": 110, "volume": 11000},
        {"open": 110, "high": 113, "low": 109, "close": 111, "volume": 9000},
    ]


@pytest.fixture
def sample_stock_code() -> str:
    """샘플 종목코드 (삼성전자)"""
    return "005930"


# ============================================
# Mock Objects
# ============================================

@pytest.fixture
def mock_kis_api(mocker):
    """한국투자증권 API 모킹"""
    mock = mocker.Mock()
    mock.inquire_price.return_value = {
        "stck_prpr": "70000",
        "prdy_vrss": "1000",
        "prdy_ctrt": "1.45",
        "acml_vol": "1000000"
    }
    return mock


@pytest.fixture
def mock_order_response():
    """주문 응답 모킹 데이터"""
    return {
        "ODNO": "0000123456",
        "ORD_TMD": "153000",
        "ORD_QTY": "10",
        "ORD_UNPR": "70000"
    }


# ============================================
# Test Strategy Objects
# ============================================

@pytest.fixture
def simple_strategy_config():
    """간단한 전략 설정"""
    return {
        "strategy_id": "test_strategy_001",
        "name": "Simple MA Strategy",
        "indicators": [
            {"type": "MA", "period": 5},
            {"type": "MA", "period": 20}
        ],
        "entry_conditions": [
            {"type": "cross_over", "fast": "MA_5", "slow": "MA_20"}
        ],
        "exit_conditions": [
            {"type": "cross_under", "fast": "MA_5", "slow": "MA_20"}
        ],
        "risk_params": {
            "stop_loss_pct": 2.0,
            "take_profit_pct": 5.0,
            "max_position_size": 1000000
        }
    }


# ============================================
# Database Fixtures (if needed)
# ============================================

@pytest.fixture
def test_db():
    """테스트용 인메모리 DB"""
    # TODO: SQLite in-memory DB 설정
    pass


# ============================================
# Cleanup Fixtures
# ============================================

@pytest.fixture(autouse=True)
def reset_state():
    """각 테스트 후 상태 초기화"""
    yield
    # 테스트 후 정리 작업
    pass