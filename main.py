from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json
import asyncio
import kis_auth as ka
from domestic_stock.domestic_stock_functions import (
    inquire_price,
    inquire_balance,
    order_cash,
    inquire_psbl_order
)

app = FastAPI(title="매매 자동매매 API", version="1.0.0")

# 앱 시작시 인증 (모의투자)
@app.on_event("startup")
async def startup_event():
    ka.auth(svr="vps", product="01")  # vps: 모의투자, prod: 실전투자
    print("✅ 한국투자증권 API 인증 완료")


# API Models
class StockPriceRequest(BaseModel):
    stock_code: str  # 종목코드 (예: "005930")

class OrderRequest(BaseModel):
    stock_code: str
    quantity: int
    price: int
    order_type: str = "limit"  # limit(지정가) or market(시장가)


@app.get("/")
async def root():
    return {
        "message": "매매 자동매매 API",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/api/stock/price/{stock_code}")
async def get_stock_price(stock_code: str):
    """주식 현재가 조회"""
    try:
        result = inquire_price(
            env_dv="real",
            fid_cond_mrkt_div_code="J",
            fid_input_iscd=stock_code
        )

        if result.empty:
            raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")

        data = result.iloc[0]
        return {
            "stock_code": stock_code,
            "current_price": int(data.get('stck_prpr', 0)),
            "change": int(data.get('prdy_vrss', 0)),
            "change_rate": float(data.get('prdy_ctrt', 0)),
            "volume": int(data.get('acml_vol', 0)),
            "high": int(data.get('stck_hgpr', 0)),
            "low": int(data.get('stck_lwpr', 0)),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/balance")
async def get_balance():
    """계좌 잔고 조회"""
    try:
        result = inquire_balance()

        if result.empty:
            return {"holdings": [], "total_value": 0}

        holdings = []
        for _, row in result.iterrows():
            holdings.append({
                "stock_code": row.get('pdno'),
                "stock_name": row.get('prdt_name'),
                "quantity": int(row.get('hldg_qty', 0)),
                "avg_price": int(row.get('pchs_avg_pric', 0)),
                "current_price": int(row.get('prpr', 0)),
                "profit_loss": int(row.get('evlu_pfls_amt', 0)),
                "profit_rate": float(row.get('evlu_pfls_rt', 0))
            })

        return {"holdings": holdings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/order/buy")
async def buy_stock(order: OrderRequest):
    """매수 주문"""
    try:
        # 매수 가능 금액 확인
        psbl = inquire_psbl_order(
            fid_cond_mrkt_div_code="J",
            fid_input_iscd=order.stock_code,
            ord_dv="buy"
        )

        result = order_cash(
            fid_cond_mrkt_div_code="J",
            fid_input_iscd=order.stock_code,
            fid_ord_qty=str(order.quantity),
            fid_ord_unpr=str(order.price),
            buy_sell_dv="buy",
            ord_dv=order.order_type
        )

        if result.empty:
            raise HTTPException(status_code=400, detail="주문 실패")

        data = result.iloc[0]
        return {
            "order_no": data.get('ODNO'),
            "order_time": data.get('ORD_TMD'),
            "message": "매수 주문 완료"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/order/sell")
async def sell_stock(order: OrderRequest):
    """매도 주문"""
    try:
        result = order_cash(
            fid_cond_mrkt_div_code="J",
            fid_input_iscd=order.stock_code,
            fid_ord_qty=str(order.quantity),
            fid_ord_unpr=str(order.price),
            buy_sell_dv="sell",
            ord_dv=order.order_type
        )

        if result.empty:
            raise HTTPException(status_code=400, detail="주문 실패")

        data = result.iloc[0]
        return {
            "order_no": data.get('ODNO'),
            "order_time": data.get('ORD_TMD'),
            "message": "매도 주문 완료"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket 연결 관리
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

manager = ConnectionManager()


@app.websocket("/ws/price/{stock_code}")
async def websocket_price(websocket: WebSocket, stock_code: str):
    """실시간 시세 WebSocket (간단한 폴링 방식)"""
    await manager.connect(websocket)

    try:
        while True:
            # 3초마다 현재가 조회해서 전송
            result = inquire_price(
                env_dv="real",
                fid_cond_mrkt_div_code="J",
                fid_input_iscd=stock_code
            )

            if not result.empty:
                data = result.iloc[0]
                await manager.send_message({
                    "stock_code": stock_code,
                    "current_price": int(data.get('stck_prpr', 0)),
                    "change": int(data.get('prdy_vrss', 0)),
                    "change_rate": float(data.get('prdy_ctrt', 0)),
                    "volume": int(data.get('acml_vol', 0)),
                }, websocket)

            await asyncio.sleep(3)  # 3초마다 업데이트

    except WebSocketDisconnect:
        manager.disconnect(websocket)
