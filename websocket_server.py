"""
WebSocket 실시간 시세 서버
"""
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import kis_auth as ka
from domestic_stock.domestic_stock_functions_ws import (
    current_concluded_price,
    asking_price_krx
)

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
                asyncio.create_task(manager.send_message({
                    "type": "price",
                    "stock_code": stock_code,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "current_price": int(row.get('STCK_PRPR', 0)),
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)