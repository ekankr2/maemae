# 매매 - 자동매매 퀀트투자 시스템

국내주식(한국투자증권 API) 자동매매 개인 프로젝트

## 프로젝트 개요

한국투자증권 Open API를 활용한 자동매매 시스템. FastAPI 기반 REST API + WebSocket 실시간 시세를 제공하며, 퀀트 전략을 구현해서 자동 매매를 실행하는 것이 목표.

## 기술 스택

- **Language**: Python 3.13+
- **Framework**: FastAPI
- **Package Manager**: uv
- **API**: 한국투자증권 Open API
- **Real-time**: WebSocket

## 프로젝트 구조

```
maemae/
├── main.py                      # FastAPI 서버 (REST API + WebSocket)
├── websocket_server.py          # 실시간 시세 WebSocket 서버
├── settings.py                  # Pydantic 환경 변수 설정
├── kis_auth.py                  # 한투 API 인증 모듈
├── .env                         # API 설정 (앱키, 계좌정보) - gitignore
├── .env.example                 # 환경 변수 템플릿
│
├── domestic_stock/              # 국내주식 통합 API
│   ├── domestic_stock_functions.py      # 모든 REST API 함수
│   ├── domestic_stock_examples.py       # 사용 예제
│   ├── domestic_stock_functions_ws.py   # WebSocket API
│   └── domestic_stock_examples_ws.py    # WebSocket 예제
│
└── examples_llm_stock/          # 개별 API 테스트용 (157개 기능)
    ├── inquire_price/           # 현재가 조회
    ├── order_cash/              # 주문
    └── ...
```

## 설치 및 실행

### 1. uv 설치
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync
```

### 2. 환경 변수 설정
```bash
# .env.example을 복사해서 .env 파일 생성
cp .env.example .env

# .env 파일에 본인 정보 입력
# - 모의투자 앱키/시크릿
# - 계좌번호 (앞 8자리)
# - HTS ID
```

### 3. 서버 실행
```bash
# FastAPI 서버 실행
uv run uvicorn main:app --reload --port 8000

# 또는 WebSocket 서버 실행
uv run python websocket_server.py
```

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/` | API 상태 확인 |
| GET | `/docs` | API 문서 (Swagger) |
| GET | `/api/stock/price/{stock_code}` | 주식 현재가 조회 |
| GET | `/api/account/balance` | 계좌 잔고 조회 |
| POST | `/api/order/buy` | 매수 주문 |
| POST | `/api/order/sell` | 매도 주문 |
| WS | `/ws/price/{stock_code}` | 실시간 시세 (3초 폴링) |

## 주요 기능

### 1. kis_auth.py
- 접근 토큰 자동 발급/갱신
- 모의투자/실전투자 환경 전환
- REST/WebSocket 인증

### 2. domestic_stock_functions.py
국내주식 관련 모든 API 함수 포함:
- 시세 조회 (현재가, 호가, 체결가, 일봉 등)
- 주문 (매수, 매도, 취소, 정정)
- 잔고 조회
- 매수가능 금액 조회
- 실시간 시세 (WebSocket)

### 3. FastAPI 서버 (main.py)
- REST API로 현재가/잔고/주문 기능 제공
- WebSocket으로 실시간 시세 스트리밍
- Swagger UI 문서 자동 생성

## 개발 로드맵

- [x] 한투 API 연동
- [x] FastAPI REST API 구현
- [x] WebSocket 실시간 시세
- [ ] 매매 전략 엔진 (이동평균, RSI, 볼린저밴드 등)
- [ ] 백테스팅 시스템
- [ ] 리스크 관리 (손절/익절)
- [ ] 자동매매 실행 엔진
- [ ] 모니터링 대시보드

## Railway 배포

### 1. Railway 프로젝트 생성
```bash
# Railway CLI 설치 (선택사항)
npm i -g @railway/cli

# Git 저장소 연결 또는 Railway 대시보드에서 직접 배포
```

### 2. 환경 변수 설정
Railway 대시보드에서 다음 환경 변수 추가:

```bash
PAPER_APP=모의투자_앱키
PAPER_SEC=모의투자_앱키_시크릿
MY_PAPER_STOCK=모의투자_증권계좌_8자리
MY_HTSID=사용자_HTS_ID
MY_PROD=01

# 실전투자 (선택)
REAL_APP=실전투자_앱키
REAL_SEC=실전투자_앱키_시크릿
MY_REAL_STOCK=실전투자_증권계좌_8자리
```

### 3. 배포 파일
- `Procfile`: Railway 실행 명령어
- `railway.json`: 빌드/배포 설정
- `.env.example`: 환경 변수 템플릿

### 4. 배포 후 확인
```
https://your-app.railway.app/docs
```

## 메모

- 기본은 모의투자 환경 (`svr="vps"`)
- 실전투자는 `svr="prod"` 변경
- `.env` 파일은 .gitignore에 포함 (보안)
- 로컬/Railway 모두 `.env` (로컬) 또는 환경 변수 (Railway)로 통일