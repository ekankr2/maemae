"""
포트폴리오 백테스트 엔진

여러 종목을 동시에 관리하며 비중 조절이 가능한 백테스터
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: float
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0

    @property
    def value(self) -> float:
        """현재 포지션 가치"""
        return self.quantity * self.current_price

    @property
    def profit_loss(self) -> float:
        """손익"""
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def profit_loss_pct(self) -> float:
        """손익률 (%)"""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price * 100


@dataclass
class Trade:
    """거래 기록"""
    date: datetime
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: float
    price: float
    commission: float
    total_cost: float


@dataclass
class PortfolioState:
    """포트폴리오 상태"""
    date: datetime
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    equity: float = 0.0  # 총 자산 (현금 + 포지션 가치)

    def update_equity(self):
        """총 자산 업데이트"""
        position_value = sum(pos.value for pos in self.positions.values())
        self.equity = self.cash + position_value


class PortfolioBacktest:
    """
    포트폴리오 백테스터

    여러 ETF를 동시에 관리하며, 비중 조절과 리밸런싱을 지원합니다.
    """

    def __init__(
        self,
        initial_cash: float = 10_000_000,
        commission: float = 0.0015,
        symbols: Optional[List[str]] = None
    ):
        """
        Args:
            initial_cash: 초기 자본금
            commission: 거래 수수료 (비율, 0.0015 = 0.15%)
            symbols: 거래할 종목 리스트
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.symbols = symbols or []

        # 상태 초기화
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[PortfolioState] = []

        # 데이터
        self.data: Dict[str, pd.DataFrame] = {}

    def load_data(self, symbol: str, data: pd.DataFrame):
        """
        종목 데이터 로드

        Args:
            symbol: 종목 코드
            data: OHLCV 데이터프레임 (Open, High, Low, Close, Volume 컬럼 필요)
        """
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")

        self.data[symbol] = data.copy()

        if symbol not in self.symbols:
            self.symbols.append(symbol)

    def buy(self, symbol: str, quantity: float, price: float, date: datetime) -> bool:
        """
        매수 실행

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격
            date: 거래 일시

        Returns:
            성공 여부
        """
        total_cost = quantity * price
        commission_fee = total_cost * self.commission
        total_with_commission = total_cost + commission_fee

        # 잔고 확인
        if self.cash < total_with_commission:
            return False

        # 잔고 차감
        self.cash -= total_with_commission

        # 포지션 추가 또는 업데이트
        if symbol in self.positions:
            # 기존 포지션이 있으면 평균단가 계산
            old_pos = self.positions[symbol]
            new_quantity = old_pos.quantity + quantity
            new_entry_price = (
                (old_pos.entry_price * old_pos.quantity + price * quantity)
                / new_quantity
            )
            old_pos.quantity = new_quantity
            old_pos.entry_price = new_entry_price
            old_pos.current_price = price
        else:
            # 새 포지션 생성
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                entry_date=date,
                current_price=price
            )

        # 거래 기록
        self.trades.append(Trade(
            date=date,
            symbol=symbol,
            action='buy',
            quantity=quantity,
            price=price,
            commission=commission_fee,
            total_cost=total_with_commission
        ))

        return True

    def sell(self, symbol: str, quantity: float, price: float, date: datetime) -> bool:
        """
        매도 실행

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격
            date: 거래 일시

        Returns:
            성공 여부
        """
        # 포지션 확인
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        if position.quantity < quantity:
            return False

        # 매도 대금 계산
        total_revenue = quantity * price
        commission_fee = total_revenue * self.commission
        total_with_commission = total_revenue - commission_fee

        # 잔고 증가
        self.cash += total_with_commission

        # 포지션 업데이트
        position.quantity -= quantity
        position.current_price = price

        # 포지션이 0이 되면 삭제
        if position.quantity == 0:
            del self.positions[symbol]

        # 거래 기록
        self.trades.append(Trade(
            date=date,
            symbol=symbol,
            action='sell',
            quantity=quantity,
            price=price,
            commission=commission_fee,
            total_cost=total_with_commission
        ))

        return True

    def update_positions(self, date: datetime, prices: Dict[str, float]):
        """
        포지션 현재가 업데이트

        Args:
            date: 날짜
            prices: {symbol: current_price} 딕셔너리
        """
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.current_price = prices[symbol]

        # 포트폴리오 상태 기록
        state = PortfolioState(
            date=date,
            cash=self.cash,
            positions=self.positions.copy()
        )
        state.update_equity()
        self.equity_curve.append(state)

    def run(self, strategy_func) -> Dict:
        """
        백테스트 실행

        Args:
            strategy_func: 전략 함수 (매 봉마다 호출)
                          signature: strategy_func(backtest, date, data)

        Returns:
            백테스트 결과 딕셔너리
        """
        if not self.data:
            raise ValueError("No data loaded. Use load_data() first.")

        # 모든 데이터의 날짜 인덱스 통합
        all_dates = set()
        for df in self.data.values():
            all_dates.update(df.index)
        dates = sorted(all_dates)

        # 각 날짜마다 전략 실행
        for date in dates:
            # 현재 날짜의 데이터 수집
            current_data = {}
            current_prices = {}
            for symbol, df in self.data.items():
                if date in df.index:
                    current_data[symbol] = df.loc[date]
                    current_prices[symbol] = df.loc[date, 'Close']

            # 전략 함수 호출
            strategy_func(self, date, current_data)

            # 포지션 업데이트
            self.update_positions(date, current_prices)

        # 결과 계산
        return self._calculate_results()

    def _calculate_results(self) -> Dict:
        """백테스트 결과 계산"""
        if not self.equity_curve:
            return {
                'initial_equity': self.initial_cash,
                'final_equity': self.cash,
                'total_return': 0.0,
                'total_trades': 0,
                'equity_curve': []
            }

        final_state = self.equity_curve[-1]
        total_return = (final_state.equity - self.initial_cash) / self.initial_cash * 100

        # 최대 낙폭 (MDD) 계산
        equity_values = [state.equity for state in self.equity_curve]
        peak = equity_values[0]
        max_drawdown = 0.0

        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return {
            'initial_equity': self.initial_cash,
            'final_equity': final_state.equity,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'total_trades': len(self.trades),
            'equity_curve': self.equity_curve,
            'trades': self.trades
        }

    def get_position(self, symbol: str) -> Optional[Position]:
        """현재 포지션 조회"""
        return self.positions.get(symbol)

    def get_position_value(self, symbol: str) -> float:
        """포지션 가치 조회"""
        pos = self.get_position(symbol)
        return pos.value if pos else 0.0

    def get_total_equity(self) -> float:
        """총 자산 조회"""
        position_value = sum(pos.value for pos in self.positions.values())
        return self.cash + position_value