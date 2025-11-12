"""
포트폴리오 백테스트 엔진 테스트
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest_engine import PortfolioBacktest


@pytest.mark.unit
class TestPortfolioBacktest:
    """포트폴리오 백테스트 기본 기능 테스트"""

    def test_initialization(self):
        """백테스터 초기화"""
        # Given & When
        bt = PortfolioBacktest(
            initial_cash=10_000_000,
            commission=0.0015
        )

        # Then
        assert bt.initial_cash == 10_000_000
        assert bt.cash == 10_000_000
        assert bt.commission == 0.0015
        assert len(bt.positions) == 0
        assert len(bt.trades) == 0

    def test_load_data(self):
        """데이터 로드"""
        # Given
        bt = PortfolioBacktest()
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        data = pd.DataFrame({
            'Open': [100, 102, 101, 103, 104],
            'High': [102, 104, 103, 105, 106],
            'Low': [99, 101, 100, 102, 103],
            'Close': [101, 103, 102, 104, 105],
            'Volume': [1000, 1100, 1050, 1200, 1150]
        }, index=dates)

        # When
        bt.load_data('233740', data)

        # Then
        assert '233740' in bt.data
        assert len(bt.data['233740']) == 5
        assert '233740' in bt.symbols

    def test_load_data_missing_columns(self):
        """필수 컬럼 누락 시 에러"""
        # Given
        bt = PortfolioBacktest()
        data = pd.DataFrame({
            'Close': [100, 101, 102]
        })

        # When & Then
        with pytest.raises(ValueError, match="must contain columns"):
            bt.load_data('233740', data)


@pytest.mark.unit
class TestBuyAndSell:
    """매수/매도 기능 테스트"""

    def test_buy_success(self):
        """매수 성공"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0015)
        date = datetime(2024, 1, 1)

        # When: 10주를 10,000원에 매수
        success = bt.buy('233740', quantity=10, price=10_000, date=date)

        # Then
        assert success is True
        assert bt.cash == 1_000_000 - (10 * 10_000 * 1.0015)  # 수수료 포함
        assert '233740' in bt.positions
        assert bt.positions['233740'].quantity == 10
        assert bt.positions['233740'].entry_price == 10_000
        assert len(bt.trades) == 1
        assert bt.trades[0].action == 'buy'

    def test_buy_insufficient_cash(self):
        """잔고 부족 시 매수 실패"""
        # Given
        bt = PortfolioBacktest(initial_cash=50_000, commission=0.0015)
        date = datetime(2024, 1, 1)

        # When: 10주를 10,000원에 매수 시도 (필요: 100,150원)
        success = bt.buy('233740', quantity=10, price=10_000, date=date)

        # Then
        assert success is False
        assert bt.cash == 50_000  # 잔고 변화 없음
        assert '233740' not in bt.positions

    def test_buy_accumulate_position(self):
        """추가 매수 시 평균단가 계산"""
        # Given
        bt = PortfolioBacktest(initial_cash=2_000_000, commission=0.0015)
        date = datetime(2024, 1, 1)

        # When: 첫 매수 10주 @ 10,000원
        bt.buy('233740', quantity=10, price=10_000, date=date)
        # 추가 매수 10주 @ 12,000원
        bt.buy('233740', quantity=10, price=12_000, date=date)

        # Then: 평균단가 = (10*10000 + 10*12000) / 20 = 11,000
        assert bt.positions['233740'].quantity == 20
        assert bt.positions['233740'].entry_price == 11_000

    def test_sell_success(self):
        """매도 성공"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0015)
        date = datetime(2024, 1, 1)
        bt.buy('233740', quantity=10, price=10_000, date=date)
        initial_cash_after_buy = bt.cash

        # When: 5주를 12,000원에 매도
        success = bt.sell('233740', quantity=5, price=12_000, date=date)

        # Then
        assert success is True
        assert bt.positions['233740'].quantity == 5  # 5주 남음
        # 매도 대금 = 5 * 12,000 * (1 - 0.0015) = 59,910
        expected_cash = initial_cash_after_buy + (5 * 12_000 * (1 - 0.0015))
        assert bt.cash == pytest.approx(expected_cash)
        assert len(bt.trades) == 2  # 매수 1, 매도 1

    def test_sell_all_position(self):
        """전량 매도 시 포지션 삭제"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0015)
        date = datetime(2024, 1, 1)
        bt.buy('233740', quantity=10, price=10_000, date=date)

        # When: 10주 전량 매도
        bt.sell('233740', quantity=10, price=12_000, date=date)

        # Then
        assert '233740' not in bt.positions  # 포지션 삭제됨

    def test_sell_no_position(self):
        """포지션 없을 때 매도 실패"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0015)
        date = datetime(2024, 1, 1)

        # When
        success = bt.sell('233740', quantity=10, price=10_000, date=date)

        # Then
        assert success is False

    def test_sell_insufficient_quantity(self):
        """보유 수량보다 많이 매도 시도 시 실패"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0015)
        date = datetime(2024, 1, 1)
        bt.buy('233740', quantity=5, price=10_000, date=date)

        # When: 10주 매도 시도 (보유 5주)
        success = bt.sell('233740', quantity=10, price=10_000, date=date)

        # Then
        assert success is False
        assert bt.positions['233740'].quantity == 5  # 수량 변화 없음


@pytest.mark.unit
class TestBacktestRun:
    """백테스트 실행 테스트"""

    def test_simple_buy_and_hold(self):
        """단순 매수 후 보유 전략"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0015)

        # 5일 데이터 생성
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        data = pd.DataFrame({
            'Open': [100, 102, 101, 103, 104],
            'High': [102, 104, 103, 105, 106],
            'Low': [99, 101, 100, 102, 103],
            'Close': [101, 103, 102, 104, 105],
            'Volume': [1000, 1100, 1050, 1200, 1150]
        }, index=dates)
        bt.load_data('TEST', data)

        # When: 첫날 매수 전략
        def strategy(backtest, date, current_data):
            if date == dates[0] and 'TEST' in current_data:
                # 첫날 100원에 100주 매수
                backtest.buy('TEST', quantity=100, price=100, date=date)

        results = bt.run(strategy)

        # Then
        assert results['total_trades'] == 1  # 매수 1회
        assert len(bt.positions) == 1  # 포지션 보유 중
        # 최종 자산 = 남은 현금 + 포지션 가치
        # 포지션 가치 = 100주 * 105원 = 10,500
        position_value = 100 * 105
        expected_equity = bt.cash + position_value
        assert results['final_equity'] == pytest.approx(expected_equity)

    def test_calculate_returns(self):
        """수익률 계산"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0)  # 수수료 0으로 단순화

        dates = pd.date_range('2024-01-01', periods=3, freq='D')
        data = pd.DataFrame({
            'Open': [100, 110, 120],
            'High': [105, 115, 125],
            'Low': [95, 105, 115],
            'Close': [100, 110, 120],
            'Volume': [1000, 1000, 1000]
        }, index=dates)
        bt.load_data('TEST', data)

        # When: 첫날 매수, 마지막날 매도
        def strategy(backtest, date, current_data):
            if date == dates[0]:
                # 100원에 1000주 매수 = 100,000원
                backtest.buy('TEST', quantity=1000, price=100, date=date)
            elif date == dates[2]:
                # 120원에 1000주 매도 = 120,000원
                backtest.sell('TEST', quantity=1000, price=120, date=date)

        results = bt.run(strategy)

        # Then
        # 수익 = 120,000 - 100,000 = 20,000
        # 수익률 = 20,000 / 1,000,000 * 100 = 2%
        assert results['total_return'] == pytest.approx(2.0, abs=0.1)
        assert results['total_trades'] == 2

    def test_max_drawdown_calculation(self):
        """최대 낙폭(MDD) 계산"""
        # Given
        bt = PortfolioBacktest(initial_cash=1_000_000, commission=0.0)

        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        data = pd.DataFrame({
            'Open': [100, 120, 80, 90, 110],
            'High': [105, 125, 85, 95, 115],
            'Low': [95, 115, 75, 85, 105],
            'Close': [100, 120, 80, 90, 110],
            'Volume': [1000, 1000, 1000, 1000, 1000]
        }, index=dates)
        bt.load_data('TEST', data)

        # When: 첫날 전액 매수
        def strategy(backtest, date, current_data):
            if date == dates[0]:
                backtest.buy('TEST', quantity=10000, price=100, date=date)

        results = bt.run(strategy)

        # Then: 최고점 120 -> 최저점 80 = -33.33% MDD
        # 실제로는 초기자본 1,000,000 기준으로 계산되므로
        # Peak: 1,200,000 (120원일 때)
        # Valley: 800,000 (80원일 때)
        # MDD = (1,200,000 - 800,000) / 1,200,000 * 100 = 33.33%
        assert results['max_drawdown'] > 30  # 대략 33% MDD