"""
WebSocket 실시간 시세 서버 + 자동매매 엔진
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import pandas as pd
import kis_auth as ka
from domestic_stock.domestic_stock_functions_ws import (
    current_concluded_price,
    asking_price_krx
)
from data_loader import load_stock_data
from examples_llm_stock.order_cash.order_cash import order_cash

app = FastAPI(title="매매 실시간 시세 WebSocket", version="1.0.0")

# 연결된 클라이언트 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


# ============================================================================
# 자동매매 엔진
# ============================================================================

class RealTimeEMA:
    """실시간 EMA 계산"""

    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.ema60 = None
        self.ema112 = None
        self.ema224 = None
        self.prices = []

    def initialize(self):
        """과거 데이터로 EMA 초기화"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        df = load_stock_data(self.stock_code, start_date, end_date, adjusted=True)

        if len(df) < 224:
            raise ValueError(f"{self.stock_code}: 데이터 부족")

        self.prices = df['Close'].values.tolist()

        # EMA 계산
        self.ema60 = self._calculate_ema(self.prices, 60)
        self.ema112 = self._calculate_ema(self.prices, 112)
        self.ema224 = self._calculate_ema(self.prices, 224)

        print(f"  {self.stock_code} EMA 초기화: EMA60={self.ema60:,.0f}, EMA112={self.ema112:,.0f}, EMA224={self.ema224:,.0f}")

    def _calculate_ema(self, prices, period):
        """EMA 계산"""
        ema = sum(prices[:period]) / period
        multiplier = 2.0 / (period + 1)
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def update(self, new_price: float):
        """실시간 가격으로 EMA 업데이트"""
        self.prices.append(new_price)
        if len(self.prices) > 300:
            self.prices.pop(0)

        multiplier60 = 2.0 / 61
        multiplier112 = 2.0 / 113
        multiplier224 = 2.0 / 225

        self.ema60 = (new_price - self.ema60) * multiplier60 + self.ema60
        self.ema112 = (new_price - self.ema112) * multiplier112 + self.ema112
        self.ema224 = (new_price - self.ema224) * multiplier224 + self.ema224

    def get_distance(self, price: float, ema: float) -> float:
        """이격률 계산"""
        if ema == 0:
            return 999.0
        return ((price - ema) / ema) * 100

    def is_near_ema(self, price: float, ema: float, threshold: float = 0.5) -> bool:
        """EMA 터치 감지 (±threshold% 이내)"""
        distance = abs(self.get_distance(price, ema))
        return distance <= threshold


class AutoTrader:
    """자동매매 엔진"""

    def __init__(self, mode: str = "demo"):
        self.mode = mode  # "demo" or "real"
        self.watch_list = {}  # 감시 종목: {code: RealTimeEMA}
        self.positions = {}  # 보유 포지션: {code: {...}}

        # 계좌 정보
        self.cano = os.getenv("KIS_ACCOUNT_NO", "")
        self.acnt_prdt_cd = os.getenv("KIS_ACCOUNT_PRODUCT_CD", "01")

        print(f"\n자동매매 엔진 시작 (모드: {mode})")

    def load_watch_list(self, csv_file: str):
        """스캐너 결과에서 감시 종목 로드"""
        if not os.path.exists(csv_file):
            print(f"⚠️  {csv_file} 파일 없음")
            return

        df = pd.read_csv(csv_file, encoding='utf-8-sig')

        for _, row in df.iterrows():
            code = row['종목코드']
            name = row['종목명']

            print(f"\n감시 종목 추가: {name} ({code})")

            ema_tracker = RealTimeEMA(code)
            ema_tracker.initialize()

            self.watch_list[code] = ema_tracker

        print(f"\n✓ 총 {len(self.watch_list)}개 종목 감시")

    def load_positions(self, json_file: str = "positions.json"):
        """보유 포지션 로드"""
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                self.positions = json.load(f)
            print(f"✓ 보유 포지션 {len(self.positions)}개")

    def save_positions(self, json_file: str = "positions.json"):
        """보유 포지션 저장"""
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.positions, f, ensure_ascii=False, indent=2)

    def check_buy_signal(self, code: str, price: float) -> bool:
        """매수 시그널 확인"""
        if code not in self.watch_list:
            return False

        if code in self.positions:  # 이미 보유 중
            return False

        ema = self.watch_list[code]

        # EMA 터치 감지
        if ema.is_near_ema(price, ema.ema60, threshold=0.5):
            print(f"🎯 {code}: EMA60 터치! ({price:,.0f}원)")
            return True
        if ema.is_near_ema(price, ema.ema112, threshold=0.5):
            print(f"🎯 {code}: EMA112 터치! ({price:,.0f}원)")
            return True
        if ema.is_near_ema(price, ema.ema224, threshold=0.5):
            print(f"🎯 {code}: EMA224 터치! ({price:,.0f}원)")
            return True

        return False

    def check_sell_signal(self, code: str, price: float) -> bool:
        """청산 시그널 확인 (EMA60 이탈)"""
        if code not in self.positions:
            return False

        if code not in self.watch_list:
            return False

        ema = self.watch_list[code]

        # EMA60 이탈
        if price < ema.ema60:
            distance = ema.get_distance(price, ema.ema60)
            print(f"⚠️  {code}: EMA60 이탈! ({price:,.0f}원, {distance:.2f}%)")
            return True

        return False

    def execute_buy(self, code: str, price: float, quantity: int = 10):
        """매수 주문"""
        print(f"\n💰 매수 주문: {code} {quantity}주 @ {price:,.0f}원")

        try:
            # 주문 실행 (모의투자)
            result = order_cash(
                env_dv=self.mode,
                ord_dv="buy",
                cano=self.cano,
                acnt_prdt_cd=self.acnt_prdt_cd,
                pdno=code,
                ord_dvsn="01",  # 시장가
                ord_qty=str(quantity),
                ord_unpr="0",
                excg_id_dvsn_cd="01"
            )

            # 포지션 기록
            self.positions[code] = {
                "buy_price": price,
                "quantity": quantity,
                "buy_time": datetime.now().isoformat()
            }
            self.save_positions()

            print(f"✓ 매수 완료")
            return True

        except Exception as e:
            print(f"❌ 매수 실패: {e}")
            return False

    def execute_sell(self, code: str, price: float):
        """청산 주문"""
        position = self.positions[code]
        quantity = position['quantity']

        print(f"\n💸 청산 주문: {code} {quantity}주 @ {price:,.0f}원")

        try:
            result = order_cash(
                env_dv=self.mode,
                ord_dv="sell",
                cano=self.cano,
                acnt_prdt_cd=self.acnt_prdt_cd,
                pdno=code,
                ord_dvsn="01",
                ord_qty=str(quantity),
                ord_unpr="0",
                excg_id_dvsn_cd="01",
                sll_type="01"
            )

            # 손익 계산
            buy_price = position['buy_price']
            profit = (price - buy_price) * quantity
            profit_rate = ((price - buy_price) / buy_price) * 100

            print(f"✓ 청산 완료: {profit:,.0f}원 ({profit_rate:+.2f}%)")

            # 포지션 삭제
            del self.positions[code]
            self.save_positions()

            return True

        except Exception as e:
            print(f"❌ 청산 실패: {e}")
            return False

    def on_price_update(self, code: str, price: float):
        """실시간 시세 업데이트 콜백"""
        # EMA 업데이트
        if code in self.watch_list:
            self.watch_list[code].update(price)

        # 매수 시그널 확인
        if self.check_buy_signal(code, price):
            self.execute_buy(code, price, quantity=10)

        # 청산 시그널 확인
        if self.check_sell_signal(code, price):
            self.execute_sell(code, price)


# 전역 자동매매 엔진 인스턴스
auto_trader = AutoTrader(mode="demo")


# 홈페이지 (테스트용)
@app.get("/")
async def get():
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>실시간 시세</title>
        </head>
        <body>
            <h1>실시간 시세 WebSocket 테스트</h1>
            <form action="" onsubmit="sendMessage(event)">
                <input type="text" id="stockCode" autocomplete="off" placeholder="종목코드 (예: 005930)"/>
                <button>구독</button>
            </form>
            <ul id='messages'>
            </ul>
            <script>
                var ws = new WebSocket("ws://localhost:8001/ws/realtime");
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var data = JSON.parse(event.data)
                    var content = document.createTextNode(
                        data.time + ' - ' + data.stock_code + ': ' +
                        '현재가 ' + data.current_price + '원 (' + data.change_rate + '%)'
                    )
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                function sendMessage(event) {
                    var input = document.getElementById("stockCode")
                    ws.send(JSON.stringify({action: "subscribe", stock_code: input.value}))
                    input.value = ''
                    event.preventDefault()
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(html)


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """실시간 시세 WebSocket 엔드포인트"""
    await manager.connect(websocket)

    # 한투 WebSocket 인증
    ka.auth(svr="vps", product="01")
    ka.auth_ws(svr="vps", product="01")

    subscribed_stocks = set()

    try:
        while True:
            # 클라이언트로부터 메시지 받기
            data = await websocket.receive_text()
            message = json.loads(data)

            action = message.get("action")
            stock_code = message.get("stock_code")

            if action == "subscribe" and stock_code:
                # 종목 구독
                subscribed_stocks.add(stock_code)
                await manager.send_message({
                    "type": "info",
                    "message": f"{stock_code} 구독 시작"
                }, websocket)

                # 실시간 시세 시작 (예시)
                asyncio.create_task(
                    stream_stock_price(websocket, stock_code)
                )

            elif action == "unsubscribe" and stock_code:
                # 구독 해제
                subscribed_stocks.discard(stock_code)
                await manager.send_message({
                    "type": "info",
                    "message": f"{stock_code} 구독 해제"
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"클라이언트 연결 종료")


async def stream_stock_price(websocket: WebSocket, stock_code: str):
    """실시간 시세 스트림 (데모용 - 실제로는 한투 WebSocket 연동)"""

    # 한투 WebSocket 실시간 시세 연동
    kws = ka.KISWebSocket(api_url="/tryitout")

    # 실시간 체결가 구독
    def on_message(ws, tr_id, df, data_map):
        if not df.empty:
            try:
                row = df.iloc[0]
                current_price = int(row.get('STCK_PRPR', 0))

                # 자동매매 로직 실행
                auto_trader.on_price_update(stock_code, current_price)

                # WebSocket 클라이언트에 전송
                asyncio.create_task(manager.send_message({
                    "type": "price",
                    "stock_code": stock_code,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "current_price": current_price,
                    "change": int(row.get('PRDY_VRSS', 0)),
                    "change_rate": float(row.get('PRDY_CTRT', 0)),
                    "volume": int(row.get('ACML_VOL', 0))
                }, websocket))
            except Exception as e:
                print(f"Error processing message: {e}")

    # 구독 시작
    kws.subscribe(request=current_concluded_price, data=[stock_code])

    try:
        kws.start(on_result=on_message, result_all_data=False)
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 자동매매 초기화"""
    print("\n" + "=" * 60)
    print("자동매매 시스템 시작")
    print("=" * 60)

    # KIS API 인증
    ka.auth(svr="vps", product="01")
    print("✓ KIS API 인증 완료")

    # 오늘 스캔 결과 로드
    today = datetime.now().strftime("%Y%m%d")
    csv_file = f"buy_candidates_{today}.csv"

    auto_trader.load_watch_list(csv_file)
    auto_trader.load_positions()

    print("\n✓ 자동매매 준비 완료")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)