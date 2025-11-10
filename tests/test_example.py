"""
테스트 템플릿 예시

이 파일은 테스트 작성 가이드입니다.
실제 테스트는 기능별로 분리된 파일에 작성하세요.
"""
import pytest


# ============================================
# Unit Test 예시
# ============================================

@pytest.mark.unit
class TestIndicators:
    """기술적 지표 계산 테스트"""

    def test_calculate_simple_moving_average(self, sample_price_data):
        """이동평균 계산 테스트"""
        # Given: 가격 데이터
        prices = sample_price_data
        period = 5

        # When: 이동평균 계산
        # ma = calculate_moving_average(prices, period)

        # Then: 예상값과 일치
        # expected = sum(prices[-period:]) / period
        # assert ma == pytest.approx(expected)

        # TODO: 실제 함수 구현 후 주석 해제
        pass

    def test_calculate_rsi(self, sample_price_data):
        """RSI 계산 테스트"""
        # Given
        prices = sample_price_data
        period = 14

        # When
        # rsi = calculate_rsi(prices, period)

        # Then
        # assert 0 <= rsi <= 100

        pass


# ============================================
# Integration Test 예시
# ============================================

@pytest.mark.integration
class TestOrderExecution:
    """주문 실행 통합 테스트"""

    def test_buy_order_success(self, mock_kis_api, sample_stock_code):
        """매수 주문 성공 테스트"""
        # Given: 주문 정보
        stock_code = sample_stock_code
        quantity = 10
        price = 70000

        # When: 매수 주문 실행
        # result = execute_buy_order(stock_code, quantity, price)

        # Then: 주문 성공
        # assert result["status"] == "success"
        # assert result["order_no"] is not None

        pass

    def test_sell_order_with_insufficient_quantity(self):
        """보유 수량 부족 시 매도 주문 실패 테스트"""
        # Given: 보유하지 않은 종목
        stock_code = "005930"
        quantity = 100

        # When & Then: 예외 발생
        # with pytest.raises(InsufficientQuantityError):
        #     execute_sell_order(stock_code, quantity, price=70000)

        pass


# ============================================
# Strategy Test 예시
# ============================================

@pytest.mark.strategy
class TestStrategy:
    """매매 전략 테스트"""

    def test_strategy_generates_buy_signal(self, simple_strategy_config, sample_ohlcv_data):
        """매수 신호 생성 테스트"""
        # Given: 전략과 데이터
        strategy = simple_strategy_config
        data = sample_ohlcv_data

        # When: 신호 생성
        # signal = strategy.generate_signal(data)

        # Then: 매수 신호
        # assert signal == "BUY"

        pass

    def test_strategy_no_signal_when_no_crossover(self):
        """크로스오버 없을 때 신호 없음 테스트"""
        # Given
        # When
        # Then
        pass


# ============================================
# Async Test 예시 (FastAPI 엔드포인트)
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestAPI:
    """FastAPI 엔드포인트 테스트"""

    async def test_get_stock_price(self):
        """현재가 조회 API 테스트"""
        # Given
        stock_code = "005930"

        # When
        # response = await client.get(f"/api/stock/price/{stock_code}")

        # Then
        # assert response.status_code == 200
        # assert response.json()["stock_code"] == stock_code

        pass


# ============================================
# Parametrized Test 예시
# ============================================

@pytest.mark.unit
@pytest.mark.parametrize("prices,period,expected", [
    ([100, 102, 104, 106, 108], 3, 106.0),
    ([100, 100, 100, 100, 100], 5, 100.0),
    ([100, 110, 90, 105, 95], 3, 96.67),
])
def test_moving_average_with_various_inputs(prices, period, expected):
    """다양한 입력에 대한 이동평균 계산 테스트"""
    # When
    # result = calculate_moving_average(prices, period)

    # Then
    # assert result == pytest.approx(expected, rel=0.01)

    pass


# ============================================
# Exception Test 예시
# ============================================

@pytest.mark.unit
def test_invalid_period_raises_error():
    """잘못된 기간 입력 시 에러 발생 테스트"""
    # Given
    prices = [100, 102, 104]
    period = -1  # 잘못된 값

    # When & Then
    # with pytest.raises(ValueError, match="Period must be positive"):
    #     calculate_moving_average(prices, period)

    pass


# ============================================
# Slow Test 예시
# ============================================

@pytest.mark.slow
def test_backtest_one_year():
    """1년치 백테스팅 테스트 (느림)"""
    # Given: 1년치 데이터
    # When: 백테스팅 실행
    # Then: 성과 지표 확인
    pass