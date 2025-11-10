# Product Requirements Document

## Overview
- **Product/Feature Name**: 매매 - 자동매매 퀀트투자 시스템
- **Version**: 1.0
- **Date**: 2025-11-10
- **Author**: ekan

## Problem Statement
수동 매매는 감정적 판단, 시간 제약, 일관성 부족 문제가 있습니다. 퀀트 전략을 자동화하여 24/7 시장을 모니터링하고, 데이터 기반 의사결정으로 일관된 매매를 실행하는 시스템이 필요합니다.

## Goals & Objectives
- **Primary Goal**: 한국투자증권 API를 활용한 완전 자동화된 매매 시스템 구축
- **Success Metrics**:
  - 매매 전략 자동 실행 성공률 > 99%
  - 백테스팅 결과와 실전 매매 오차율 < 5%
  - 시스템 가동률 > 99.9% (장 운영 시간 기준)
  - API 응답 시간 < 1초

## Target Users
- **개인 투자자 (본인)**: 퀀트 전략을 자동으로 실행하고 싶은 개발자/투자자
- **향후 확장**: 다른 개인 투자자에게 전략 공유/백테스팅 플랫폼 제공

## User Stories
1. As a 투자자, I want to 매매 전략을 코드로 정의 so that 감정 개입 없이 일관되게 실행할 수 있다.
2. As a 투자자, I want to 전략을 백테스팅 so that 실전 투자 전에 성과를 검증할 수 있다.
3. As a 투자자, I want to 리스크 관리 규칙을 설정 so that 큰 손실을 방지할 수 있다.
4. As a 투자자, I want to 실시간으로 포트폴리오를 모니터링 so that 현재 상태를 언제든지 확인할 수 있다.
5. As a 투자자, I want to 여러 전략을 동시에 운영 so that 분산 투자 효과를 얻을 수 있다.

## Requirements

### Functional Requirements

1. **매매 전략 엔진**
   - Description: 기술적 지표를 계산하고 매매 신호를 생성
   - Acceptance Criteria:
     - 이동평균(MA), RSI, 볼린저밴드, MACD 등 주요 지표 계산
     - 전략 조합 가능 (AND/OR 조건)
     - 커스텀 지표 추가 가능
     - 전략은 TBD (향후 결정)

2. **백테스팅 시스템**
   - Description: 과거 데이터로 전략 성과 검증
   - Acceptance Criteria:
     - 지정 기간의 과거 데이터 로드
     - 매매 시뮬레이션 실행
     - 성과 지표 계산 (수익률, MDD, 샤프지수 등)
     - 매매 내역 상세 로그

3. **자동 주문 실행**
   - Description: 매매 신호 발생 시 자동으로 주문 실행
   - Acceptance Criteria:
     - 매수/매도 신호에 따른 자동 주문
     - 분할 매매 지원 (N회 나눠서 매수/매도)
     - 주문 실패 시 재시도 로직
     - 주문 체결 확인 및 로깅

4. **리스크 관리**
   - Description: 손실 제한 및 포지션 크기 관리
   - Acceptance Criteria:
     - 손절선 설정 및 자동 실행
     - 익절선 설정 및 자동 실행
     - 최대 손실 한도 (일/주/월)
     - 종목당 투자 비중 제한
     - 총 투자 금액 제한

5. **포트폴리오 모니터링**
   - Description: 실시간 계좌 상태 및 수익률 추적
   - Acceptance Criteria:
     - 현재 보유 종목 및 수익률 표시
     - 일일/주간/월간 수익률 계산
     - 총 자산 추이 차트
     - 종목별 손익 상세

6. **알림 시스템**
   - Description: 주요 이벤트 발생 시 알림
   - Acceptance Criteria:
     - 매매 체결 알림
     - 손절/익절 실행 알림
     - 시스템 에러 알림
     - 일일 리포트 (선택적)

### Non-Functional Requirements
- **Performance**:
  - API 호출 응답 < 1초
  - 실시간 시세 업데이트 < 3초
  - 백테스팅 1년 데이터 < 10초
- **Security**:
  - API 키/시크릿 환경 변수 관리
  - 실전/모의투자 명확한 구분
  - 주문 실행 전 이중 확인 (실전투자)
- **Scalability**:
  - 동시에 최소 10개 종목 모니터링 가능
  - 여러 전략 동시 실행 가능
- **Reliability**:
  - 시스템 장애 시 자동 복구
  - 모든 주문/거래 로그 기록
  - 예외 처리 및 에러 로깅

## Current Implementation Status

### ✅ 완료된 기능
- 한국투자증권 API 인증 (`kis_auth.py`)
- REST API 서버 (FastAPI)
  - 현재가 조회 (`GET /api/stock/price/{code}`)
  - 계좌 잔고 조회 (`GET /api/account/balance`)
  - 매수/매도 주문 (`POST /api/order/buy`, `/api/order/sell`)
- WebSocket 실시간 시세 (`/ws/price/{code}`)
- 국내주식 API 통합 모듈 (`domestic_stock/`)

### 🚧 구현 필요 (이 PRD의 범위)
- 매매 전략 엔진
- 백테스팅 시스템
- 리스크 관리 시스템
- 자동매매 실행 엔진
- 모니터링 대시보드
- 알림 시스템

## Technical Architecture

### System Flow
```
1. 실시간 시세 수신 (WebSocket)
2. 전략 엔진에서 지표 계산
3. 매매 신호 생성
4. 리스크 관리 검증
5. 주문 실행
6. 체결 확인 및 로깅
7. 포트폴리오 업데이트
```

### Data Models

**Strategy (전략)**
```python
{
  strategy_id: str
  name: str
  indicators: List[Indicator]  # 사용할 지표들
  entry_conditions: List[Condition]  # 진입 조건
  exit_conditions: List[Condition]   # 청산 조건
  risk_params: RiskParams            # 리스크 파라미터
  is_active: bool
}
```

**Trade (거래)**
```python
{
  trade_id: str
  strategy_id: str
  stock_code: str
  order_type: "buy" | "sell"
  quantity: int
  price: int
  executed_at: datetime
  status: "pending" | "executed" | "failed"
}
```

**Position (포지션)**
```python
{
  stock_code: str
  quantity: int
  avg_price: int
  current_price: int
  profit_loss: float
  profit_rate: float
}
```

## API/Interface Specifications

### New Endpoints (추가 필요)

**Strategy Management**
- `POST /api/strategy` - 전략 생성
- `GET /api/strategy/{id}` - 전략 조회
- `PUT /api/strategy/{id}` - 전략 수정
- `DELETE /api/strategy/{id}` - 전략 삭제
- `POST /api/strategy/{id}/start` - 전략 시작
- `POST /api/strategy/{id}/stop` - 전략 중지

**Backtesting**
- `POST /api/backtest` - 백테스트 실행
- `GET /api/backtest/{id}` - 백테스트 결과 조회

**Monitoring**
- `GET /api/portfolio` - 포트폴리오 현황
- `GET /api/trades` - 거래 내역
- `GET /api/performance` - 성과 분석

## Out of Scope (v1.0에서 제외)
- 해외 주식 거래
- 선물/옵션 거래
- 다중 계좌 관리
- 소셜 트레이딩 (다른 사람 전략 따라하기)
- 모바일 앱
- 머신러닝 기반 전략 (추후 고려)

## Dependencies
- **External Services**:
  - 한국투자증권 Open API (필수)
  - Railway (배포, 선택)
- **Third-party Libraries**:
  - FastAPI (이미 사용중)
  - pandas (데이터 처리)
  - numpy (지표 계산)
  - TA-Lib 또는 pandas-ta (기술적 지표)
  - SQLite/PostgreSQL (거래 내역 저장)

## Technical Considerations
- **Architecture**:
  - 모노리틱 FastAPI 애플리케이션
  - 비동기 처리 (asyncio)
  - WebSocket + REST API 혼합
- **Technology Stack**:
  - Python 3.13+
  - FastAPI
  - pandas, numpy
  - SQLite (로컬) / PostgreSQL (프로덕션)
- **Constraints**:
  - 한투 API rate limit 고려 (1초당 20건)
  - 장 운영 시간 (09:00~15:30)만 거래 가능
- **Assumptions**:
  - 모의투자에서 충분히 테스트 후 실전 투자
  - 초기에는 단일 계좌만 지원

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API 장애 | 매매 불가 | 재시도 로직, 알림 시스템 |
| 잘못된 주문 실행 | 금전적 손실 | 모의투자 테스팅, 이중 확인 로직 |
| 전략 버그 | 예상치 못한 손실 | 백테스팅, 손절선 필수 설정 |
| 네트워크 지연 | 늦은 체결 | WebSocket 유지, 타임아웃 설정 |
| 데이터 손실 | 거래 기록 유실 | DB 백업, 로그 저장 |

## Strategy Development Plan
전략은 아직 결정되지 않았습니다. 다음 단계에서 결정할 사항:

1. **Phase 1: 간단한 전략으로 시작**
   - 이동평균 크로스오버
   - RSI 과매수/과매도

2. **Phase 2: 복합 전략**
   - 여러 지표 조합
   - 변동성 돌파

3. **Phase 3: 고급 전략**
   - 페어 트레이딩
   - 모멘텀 전략

## Timeline & Milestones
- **Phase 1** (2주): 전략 엔진 + 기술적 지표 계산
- **Phase 2** (2주): 백테스팅 시스템
- **Phase 3** (1주): 리스크 관리 시스템
- **Phase 4** (1주): 자동매매 실행 엔진
- **Phase 5** (1주): 모니터링 + 알림
- **Launch** (1주): 모의투자 운영 및 테스트

## Test Plan Reference
See `plan.md` for detailed test cases and TDD implementation plan.

---

## Notes
- 실전 투자 전 최소 1개월 모의투자 운영 필수
- 전략은 백테스팅 + 모의투자 검증 후 실전 적용
- 손절선은 모든 전략에 필수적으로 설정

## Changelog
| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0     | 2025-11-10 | Initial draft | ekan |