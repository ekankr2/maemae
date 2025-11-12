"""
코스닥피 레인 전략 테스트
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest_engine import PortfolioBacktest


@pytest.mark.unit
class TestKosdaq150LeverageBuyCondition:
    """코스닥150레버리지 매수 조건 테스트"""

    def test_buy_when_basic_filter_passes_and_breakout_target(self):
        """
        기본 필터 통과하고 목표가 돌파 시 매수

        조건:
        - 기본 필터: 시가 > 전일 저가
        - 현재가가 60일선 위 → K = 0.3
        - 목표가 = 시가 + (전일 고가 - 전일 저가) × 0.3
        - 고가가 목표가를 돌파하면 매수
        """
        # Given: 3일 데이터
        dates = pd.date_range('2024-01-01', periods=3, freq='D')

        # 60일선 계산을 위한 충분한 데이터 (62일)
        full_dates = pd.date_range('2023-11-01', periods=62, freq='D')
        prices = list(range(9000, 9000 + 62 * 10, 10))  # 9000부터 10씩 증가

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 62
        }, index=full_dates)

        # 마지막 3일만 테스트
        # Day -2: Close = 9610
        # Day -1 (전일): Open=9600, High=9650, Low=9550, Close=9620
        # Day 0 (금일): Open=9630, 60일선 근처 (현재가 > 60일선)

        # 금일 시가 = 9630
        # 전일 고가 - 전일 저가 = 9650 - 9550 = 100
        # K = 0.3 (60일선 위)
        # 목표가 = 9630 + 100 * 0.3 = 9660
        # 금일 고가가 9680이면 목표가 돌파 → 매수

        data.loc[full_dates[-1], 'Open'] = 9630
        data.loc[full_dates[-1], 'High'] = 9680  # 목표가 9660 돌파
        data.loc[full_dates[-1], 'Low'] = 9600
        data.loc[full_dates[-1], 'Close'] = 9670

        # 기본 필터 만족: 시가(9630) > 전일 저가(9550) ✓

        # When: 백테스트 실행
        from strategies.kosdaq_pi_rain_strategy import check_kosdaq150_lev_buy_signal

        result = check_kosdaq150_lev_buy_signal(data, current_idx=-1)

        # Then: 매수 신호 발생
        assert result is True

    def test_no_buy_when_basic_filter_fails(self):
        """
        기본 필터 실패 시 매수 안함

        조건:
        - 시가 <= 전일 저가 AND 전일 종가 <= 10일 이동평균
        """
        # Given: 12일 데이터 (10일 이평선 계산용)
        dates = pd.date_range('2024-01-01', periods=12, freq='D')
        prices = [10000] * 10 + [9900, 9850]  # 횡보 후 하락

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 12
        }, index=dates)

        # 마지막 날: 시가(9850) <= 전일 저가(9850) → 기본 필터 실패

        # When
        from strategies.kosdaq_pi_rain_strategy import check_kosdaq150_lev_buy_signal

        result = check_kosdaq150_lev_buy_signal(data, current_idx=-1)

        # Then: 매수 신호 없음
        assert result is False

    def test_no_buy_when_price_not_breakout_target(self):
        """
        목표가를 돌파하지 못하면 매수 안함

        조건:
        - 기본 필터는 통과
        - 하지만 고가가 목표가를 돌파하지 못함
        """
        # Given
        dates = pd.date_range('2023-11-01', periods=62, freq='D')
        prices = list(range(9000, 9000 + 62 * 10, 10))

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 62
        }, index=dates)

        # 목표가 = 9630 + 100 * 0.3 = 9660
        # 금일 고가 = 9650 < 9660 → 목표가 미돌파
        data.loc[dates[-1], 'Open'] = 9630
        data.loc[dates[-1], 'High'] = 9650  # 목표가 미돌파
        data.loc[dates[-1], 'Low'] = 9600
        data.loc[dates[-1], 'Close'] = 9640

        # When
        from strategies.kosdaq_pi_rain_strategy import check_kosdaq150_lev_buy_signal

        result = check_kosdaq150_lev_buy_signal(data, current_idx=-1)

        # Then: 매수 안함
        assert result is False

    def test_k_value_changes_based_on_ema60(self):
        """
        60일선 위치에 따라 K값이 바뀜

        - 현재가 > 60일선 → K = 0.3
        - 현재가 <= 60일선 → K = 0.4
        """
        # Given: 60일선 아래에 있는 경우
        dates = pd.date_range('2023-11-01', periods=62, freq='D')
        # 하락 추세로 60일선 아래
        prices = list(range(10000, 10000 - 62 * 10, -10))

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 62
        }, index=dates)

        # 금일 종가가 60일선 아래 → K = 0.4
        # 목표가 = 시가 + (전일 범위) × 0.4
        # 더 높은 K값으로 목표가가 더 높아짐

        # When: K값 계산
        from strategies.kosdaq_pi_rain_strategy import calculate_k_value_for_buy

        k_value = calculate_k_value_for_buy(data, current_idx=-1)

        # Then: K = 0.4
        assert k_value == 0.4


@pytest.mark.unit
class TestKosdaq150LeverageSellCondition:
    """코스닥150레버리지 매도 조건 테스트"""

    def test_sell_when_price_breaks_down_target(self):
        """
        목표가 하향 돌파 시 매도

        조건:
        - 현재가가 60일선 위 → K = 0.4 (매수와 반대)
        - 목표가 = 시가 - (전일 고가 - 전일 저가) × 0.4
        - 저가가 목표가 이하로 떨어지면 매도
        """
        # Given: 62일 데이터 (60일선 계산용)
        dates = pd.date_range('2023-11-01', periods=62, freq='D')
        prices = list(range(9000, 9000 + 62 * 10, 10))  # 상승 추세

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 62
        }, index=dates)

        # 마지막 날 설정
        # 금일 시가 = 9630
        # 전일 고가 - 전일 저가 = 9650 - 9550 = 100
        # K = 0.4 (60일선 위, 매도는 매수와 반대)
        # 목표가 = 9630 - 100 * 0.4 = 9590
        # 금일 저가가 9580이면 목표가 하향 돌파 → 매도

        data.loc[dates[-1], 'Open'] = 9630
        data.loc[dates[-1], 'High'] = 9650
        data.loc[dates[-1], 'Low'] = 9580  # 목표가 9590 하향 돌파
        data.loc[dates[-1], 'Close'] = 9600

        # When
        from strategies.kosdaq_pi_rain_strategy import check_kosdaq150_lev_sell_signal

        result = check_kosdaq150_lev_sell_signal(data, current_idx=-1)

        # Then: 매도 신호 발생
        assert result is True

    def test_no_sell_when_price_not_break_down_target(self):
        """
        목표가를 하향 돌파하지 않으면 매도 안함
        """
        # Given
        dates = pd.date_range('2023-11-01', periods=62, freq='D')
        prices = list(range(9000, 9000 + 62 * 10, 10))

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 62
        }, index=dates)

        # 목표가 = 9630 - 100 * 0.4 = 9590
        # 금일 저가 = 9600 > 9590 → 목표가 미돌파
        data.loc[dates[-1], 'Open'] = 9630
        data.loc[dates[-1], 'High'] = 9650
        data.loc[dates[-1], 'Low'] = 9600  # 목표가 미돌파
        data.loc[dates[-1], 'Close'] = 9620

        # When
        from strategies.kosdaq_pi_rain_strategy import check_kosdaq150_lev_sell_signal

        result = check_kosdaq150_lev_sell_signal(data, current_idx=-1)

        # Then: 매도 안함
        assert result is False

    def test_k_value_for_sell_is_opposite_to_buy(self):
        """
        매도 K값은 매수와 반대

        - 현재가 > 60일선 → K = 0.4 (매수는 0.3)
        - 현재가 <= 60일선 → K = 0.3 (매수는 0.4)
        """
        # Given: 60일선 위에 있는 경우
        dates = pd.date_range('2023-11-01', periods=62, freq='D')
        prices = list(range(9000, 9000 + 62 * 10, 10))  # 상승 추세

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 62
        }, index=dates)

        # 현재가가 60일선 위 → 매도 K = 0.4

        # When: 매도용 K값 계산
        from strategies.kosdaq_pi_rain_strategy import calculate_k_value_for_sell

        k_value = calculate_k_value_for_sell(data, current_idx=-1)

        # Then: K = 0.4 (매수는 0.3)
        assert k_value == 0.4

    def test_k_value_for_sell_below_ema60(self):
        """
        60일선 아래에서 매도 K값은 0.3
        """
        # Given: 60일선 아래 (하락 추세)
        dates = pd.date_range('2023-11-01', periods=62, freq='D')
        prices = list(range(10000, 10000 - 62 * 10, -10))  # 하락 추세

        data = pd.DataFrame({
            'Open': prices,
            'High': [p + 50 for p in prices],
            'Low': [p - 50 for p in prices],
            'Close': [p + 20 for p in prices],
            'Volume': [1000] * 62
        }, index=dates)

        # 현재가가 60일선 아래 → 매도 K = 0.3

        # When
        from strategies.kosdaq_pi_rain_strategy import calculate_k_value_for_sell

        k_value = calculate_k_value_for_sell(data, current_idx=-1)

        # Then: K = 0.3 (매수는 0.4)
        assert k_value == 0.3