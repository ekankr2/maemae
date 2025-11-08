# 한국투자증권 자동매매 퀀트투자 앱

## 시작하기

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. kis_devlp.yaml 설정
1. 한국투자증권 Open API 포털에서 앱키/앱시크릿 발급
   - 포털: https://apiportal.koreainvestment.com/
2. 예시 파일 복사 후 본인 정보 입력
   ```bash
   cp kis_devlp.yaml.example kis_devlp.yaml
   ```
3. `kis_devlp.yaml` 파일에 본인 정보 입력
   - 모의투자 앱키/시크릿
   - 실전투자 앱키/시크릿 (실전 사용시)
   - HTS ID
   - 계좌번호
4. **주의**: `kis_devlp.yaml` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다

### 3. 테스트 실행
```bash
python test_stock.py
```

## 주요 기능

### kis_auth.py - 인증 모듈
- 접근 토큰 자동 발급/갱신
- 모의투자/실전투자 환경 전환
- API 호출 공통 함수

### domestic_stock/stock_api.py - 국내주식 API
- `inquire_price()`: 주식 현재가 조회
- `inquire_balance()`: 보유 잔고 조회
- `order_cash()`: 주식 주문 (매수/매도)
- `inquire_daily_price()`: 일/주/월봉 시세 조회

## 사용 예시

```python
import kis_auth as ka
from domestic_stock.stock_api import *

# 모의투자 인증
ka.auth(svr="vps", product="01")

# 삼성전자 현재가 조회
price = inquire_price("005930")
print(price)

# 잔고 조회
balance = inquire_balance()
print(balance)

# 매수 주문 (10주, 70000원 지정가)
result = order_cash("005930", 10, 70000, buy_sell="buy", order_type="limit")
print(result)
```

## 다음 단계
- [ ] 웹소켓 실시간 시세 구현
- [ ] 퀀트 전략 백테스팅 엔진
- [ ] FastAPI 웹 인터페이스
- [ ] 리스크 관리 시스템