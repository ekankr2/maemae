"""
기술적 지표 계산 테스트
"""
import pytest
from indicators.moving_average import calculate_moving_average, calculate_ema


@pytest.mark.unit
class TestMovingAverage:
    """이동평균 계산 테스트"""

    def test_calculate_5day_moving_average(self):
        """5일 이동평균 계산"""
        # Given: 최근 5일의 종가
        prices = [100, 102, 101, 103, 104]
        period = 5

        # When: 5일 이동평균 계산
        result = calculate_moving_average(prices, period)

        # Then: (100+102+101+103+104)/5 = 102
        expected = 102.0
        assert result == pytest.approx(expected)

    def test_calculate_ma_with_more_data_than_period(self):
        """데이터가 기간보다 많을 때 최근 데이터만 사용"""
        # Given: 10일 데이터, 5일 이동평균
        prices = [90, 91, 92, 93, 94, 100, 102, 101, 103, 104]
        period = 5

        # When
        result = calculate_moving_average(prices, period)

        # Then: 마지막 5개만 사용 (100,102,101,103,104)
        expected = 102.0
        assert result == pytest.approx(expected)

    def test_calculate_ma_with_invalid_period(self):
        """잘못된 기간 입력 시 에러 발생"""
        # Given
        prices = [100, 102, 104]
        period = 0  # 잘못된 값

        # When & Then
        with pytest.raises(ValueError, match="Period must be positive"):
            calculate_moving_average(prices, period)

    def test_calculate_ma_when_not_enough_data(self):
        """데이터가 기간보다 적을 때 에러 발생"""
        # Given
        prices = [100, 102]
        period = 5

        # When & Then
        with pytest.raises(ValueError, match="Not enough data"):
            calculate_moving_average(prices, period)


@pytest.mark.unit
class TestExponentialMovingAverage:
    """지수 이동평균 계산 테스트"""

    def test_calculate_5day_ema(self):
        """5일 EMA 계산"""
        # Given: 10일의 종가 데이터
        prices = [100, 102, 101, 103, 104, 105, 103, 106, 108, 107]
        period = 5

        # When: 5일 EMA 계산
        result = calculate_ema(prices, period)

        # Then: EMA는 최근 값에 더 높은 가중치
        # 수동 계산:
        # 1. 첫 EMA는 처음 5개의 SMA: (100+102+101+103+104)/5 = 102
        # 2. multiplier = 2/(5+1) = 0.333...
        # 3. EMA[5] = (105-102)*0.333 + 102 = 103.0
        # 4. EMA[6] = (103-103.0)*0.333 + 103.0 = 103.0
        # 5. EMA[7] = (106-103.0)*0.333 + 103.0 = 104.0
        # 6. EMA[8] = (108-104.0)*0.333 + 104.0 = 105.333
        # 7. EMA[9] = (107-105.333)*0.333 + 105.333 = 105.889
        expected = 105.889
        assert result == pytest.approx(expected, rel=0.01)