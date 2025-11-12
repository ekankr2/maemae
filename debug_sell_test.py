import pandas as pd
from strategies.kosdaq_pi_rain_strategy import check_kospi200_inv2x_sell_signal

# Given: 고이격도 상태 (이격도 > 105) + 전일 종가 < 3일선
dates = pd.date_range('2024-01-01', periods=30, freq='D')

# 먼저 낮은 가격으로 11일 유지 (11일선을 낮게 만듦), 그 후 급등
base_prices = [10000] * 11 + [10000 + i * 80 for i in range(1, 20)]

data = pd.DataFrame({
    'Open': base_prices,
    'High': [p + 50 for p in base_prices],
    'Low': [p - 50 for p in base_prices],
    'Close': base_prices,
    'Volume': [1000] * 30
}, index=dates)

# 마지막 3일은 추가 급등 후 급락 (이격도 > 105, 전일 종가 < 3일선)
data.loc[dates[-3], 'Close'] = 11900  # 추가 급등
data.loc[dates[-2], 'Close'] = 11500  # 전일: 급락 (3일선보다 낮게)
data.loc[dates[-1], 'Close'] = 11900  # 금일 (다시 회복)

print("=" * 60)
print("데이터 확인")
print("=" * 60)
print(f"전일 종가: {data.iloc[-2]['Close']}")
print(f"전전일 종가: {data.iloc[-3]['Close']}")
print(f"금일 종가: {data.iloc[-1]['Close']}")
print()

# 11일선 계산
sma_11 = data['Close'].rolling(window=11).mean()
prev_sma_11 = sma_11.iloc[-2]
prev_close = data.iloc[-2]['Close']

print("=" * 60)
print("11일선 이격도 확인")
print("=" * 60)
print(f"전일 11일선: {prev_sma_11}")
print(f"전일 종가: {prev_close}")
disparity_11 = (prev_close / prev_sma_11) * 100
print(f"11일 이격도: {disparity_11}")
print(f"이격도 > 105? {disparity_11 > 105}")
print()

# 3일선 계산
sma_3 = data['Close'].rolling(window=3).mean()
prev_sma_3 = sma_3.iloc[-2]

print("=" * 60)
print("3일선 확인")
print("=" * 60)
print(f"전일 3일선: {prev_sma_3}")
print(f"전일 종가: {prev_close}")
print(f"전일 종가 < 3일선? {prev_close < prev_sma_3}")
print()

# 실제 매도 신호 확인
result = check_kospi200_inv2x_sell_signal(data, current_idx=-1)
print("=" * 60)
print(f"매도 신호: {result}")
print("=" * 60)