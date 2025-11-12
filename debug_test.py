import pandas as pd
from strategies.kosdaq_pi_rain_strategy import check_kospi200_inv2x_buy_signal
from indicators.rsi import calculate_rsi

# Test data - 변동성 있는 상승 추세
dates = pd.date_range('2024-01-01', periods=80, freq='D')

base_prices = []
price = 10000
for i in range(80):
    # 전반적으로 상승하되, 3일마다 1일 하락
    if i % 3 == 2:
        price -= 10  # 소폭 하락
    else:
        price += 15  # 상승
    base_prices.append(price)

data = pd.DataFrame({
    'Open': base_prices,
    'High': [p + 30 for p in base_prices],
    'Low': [p - 30 for p in base_prices],
    'Close': [p + 10 for p in base_prices],
    'Volume': [1000] * 80
}, index=dates)

# 전전일, 전일 설정
data.loc[dates[-3], 'Volume'] = 800
data.loc[dates[-2], 'Volume'] = 1200
data.loc[dates[-3], 'Low'] = base_prices[-3] - 50
data.loc[dates[-2], 'Low'] = base_prices[-2] - 30  # 더 높음

# Debug each condition
current_idx = -1
prev = data.iloc[current_idx - 1]
prev_prev = data.iloc[current_idx - 2]

print("=" * 60)
print("조건 1: 전일 종가 > (3일선, 6일선, 19일선, 60일선)")
sma_3 = data['Close'].rolling(window=3).mean()
sma_6 = data['Close'].rolling(window=6).mean()
sma_19 = data['Close'].rolling(window=19).mean()
sma_60 = data['Close'].rolling(window=60).mean()

prev_sma_3 = sma_3.iloc[current_idx - 1]
prev_sma_6 = sma_6.iloc[current_idx - 1]
prev_sma_19 = sma_19.iloc[current_idx - 1]
prev_sma_60 = sma_60.iloc[current_idx - 1]
prev_close = prev['Close']

print(f"전일 종가: {prev_close}")
print(f"전일 3일선: {prev_sma_3}")
print(f"전일 6일선: {prev_sma_6}")
print(f"전일 19일선: {prev_sma_19}")
print(f"전일 60일선: {prev_sma_60}")
print(f"Result: {prev_close > prev_sma_3 and prev_close > prev_sma_6 and prev_close > prev_sma_19 and prev_close > prev_sma_60}")

print("\n" + "=" * 60)
print("조건 2: 60일선 증가 중")
prev_prev_sma_60 = sma_60.iloc[current_idx - 2]
print(f"전전일 60일선: {prev_prev_sma_60}")
print(f"전일 60일선: {prev_sma_60}")
print(f"Result: {prev_prev_sma_60 < prev_sma_60}")

print("\n" + "=" * 60)
print("조건 3: 정배열 (3일선 > 6일선 > 19일선)")
print(f"전일 3일선: {prev_sma_3}")
print(f"전일 6일선: {prev_sma_6}")
print(f"전일 19일선: {prev_sma_19}")
print(f"Result: {prev_sma_3 > prev_sma_6 and prev_sma_6 > prev_sma_19}")

print("\n" + "=" * 60)
print("조건 4: 전일 종가 기준 RSI < 70")
close_prices_prev = data['Close'].iloc[:current_idx].tolist()
prev_rsi = calculate_rsi(close_prices_prev, period=14)
print(f"전일 RSI: {prev_rsi}")
print(f"Result: {prev_rsi < 70}")

print("\n" + "=" * 60)
print("조건 5: 전전일 RSI < 전일 RSI")
close_prices_prev_prev = data['Close'].iloc[:current_idx - 1].tolist()
prev_prev_rsi = calculate_rsi(close_prices_prev_prev, period=14)
print(f"전전일 RSI: {prev_prev_rsi}")
print(f"전일 RSI: {prev_rsi}")
print(f"Result: {prev_prev_rsi < prev_rsi}")

print("\n" + "=" * 60)
print("조건 6: 전전일 거래량 < 전일 거래량")
print(f"전전일 거래량: {prev_prev['Volume']}")
print(f"전일 거래량: {prev['Volume']}")
print(f"Result: {prev_prev['Volume'] < prev['Volume']}")

print("\n" + "=" * 60)
print("조건 7: 전전일 저가 < 전일 저가")
print(f"전전일 저가: {prev_prev['Low']}")
print(f"전일 저가: {prev['Low']}")
print(f"Result: {prev_prev['Low'] < prev['Low']}")

print("\n" + "=" * 60)
print("최종 매수 신호:")
result = check_kospi200_inv2x_buy_signal(data, current_idx=-1)
print(f"Result: {result}")