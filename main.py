from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import math
import os
import pandas as pd
import kis_auth as ka
from backtesting import Backtest
from domestic_stock.domestic_stock_functions import (
    inquire_price,
    inquire_balance,
    order_cash,
    inquire_psbl_order
)
from data_loader import load_stock_data
from strategies.balloon_theory_strategy import BalloonTheoryStrategy

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

class BacktestRequest(BaseModel):
    """백테스팅 요청 모델"""
    stock_code: str = "005930"  # 삼성전자
    start_date: str = "20220101"
    end_date: str = "20231231"
    cash: int = 10_000_000  # 초기 자본금
    commission: float = 0.0015  # 수수료 0.15%
    svr: str = "prod"  # prod: 실전투자, vps: 모의투자

class BacktestCsvRequest(BaseModel):
    """CSV 파일 기반 백테스팅 요청 모델"""
    csv_file: str  # CSV 파일 경로 (예: "buy_candidates_20251110.csv")
    start_date: str = "20220101"
    end_date: str = "20231231"
    cash: int = 10_000_000  # 초기 자본금
    commission: float = 0.0015  # 수수료 0.15%
    svr: str = "prod"  # prod: 실전투자, vps: 모의투자

class BacktestMultiRequest(BaseModel):
    """여러 종목 백테스팅 요청 모델"""
    stock_codes: list[str]  # 종목코드 리스트 (예: ["005930", "000660"])
    start_date: str = "20220101"
    end_date: str = "20231231"
    cash: int = 10_000_000  # 초기 자본금
    commission: float = 0.0015  # 수수료 0.15%
    svr: str = "prod"  # prod: 실전투자, vps: 모의투자


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


def safe_float(value, default=0.0):
    """NaN 값을 안전하게 처리하는 헬퍼 함수"""
    if value is None:
        return default
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return default
        return val
    except (ValueError, TypeError):
        return default


def run_backtest(
    stock_code: str,
    start_date: str,
    end_date: str,
    cash: int = 10_000_000,
    commission: float = 0.0015,
    svr: str = "prod"
) -> dict:
    """
    백테스팅 실행 함수
    
    Returns:
        dict: 백테스팅 결과 통계
    """
    # 1. KIS API 인증
    ka.auth(svr=svr)
    
    # 2. 과거 데이터 로드
    df = load_stock_data(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        adjusted=True  # 수정주가 사용
    )
    
    if df.empty:
        raise ValueError(f"데이터를 불러올 수 없습니다: {stock_code}")
    
    # 3. 백테스팅 설정
    bt = Backtest(
        df,
        BalloonTheoryStrategy,
        cash=cash,
        commission=commission,
        exclusive_orders=True  # 동시에 여러 주문 불가
    )
    
    # 4. 백테스팅 실행
    stats = bt.run()
    
    # 5. 결과를 딕셔너리로 변환 (NaN 값 처리)
    equity_curve = stats['_equity_curve']['Equity']
    initial_equity = safe_float(equity_curve.iloc[0] if len(equity_curve) > 0 else 0)
    
    result = {
        "stock_code": stock_code,
        "start_date": start_date,
        "end_date": end_date,
        "period": f"{df.index[0]} ~ {df.index[-1]}",
        "data_count": len(df),
        "strategy": "풍선이론 (Volume Breakout)",
        "strategy_params": {
            "ema_period": BalloonTheoryStrategy.ema_period,
            "volume_multiplier": BalloonTheoryStrategy.volume_multiplier,
            "min_price": BalloonTheoryStrategy.min_price
        },
        "backtest_params": {
            "initial_cash": cash,
            "commission": commission
        },
        "results": {
            "initial_equity": initial_equity,
            "final_equity": safe_float(stats.get('Equity Final [$]', 0)),
            "return_pct": safe_float(stats.get('Return [%]', 0)),
            "return_ann_pct": safe_float(stats.get('Return (Ann.) [%]', 0)),
            "total_trades": int(stats.get('# Trades', 0)),
            "win_rate_pct": safe_float(stats.get('Win Rate [%]', 0)),
            "max_drawdown_pct": safe_float(stats.get('Max. Drawdown [%]', 0)),
            "sharpe_ratio": safe_float(stats.get('Sharpe Ratio', 0))
        }
    }
    
    return result


@app.post("/api/backtest")
async def backtest_endpoint(request: BacktestRequest):
    """
    백테스팅 실행 엔드포인트
    
    예시:
    ```json
    {
        "stock_code": "005930",
        "start_date": "20220101",
        "end_date": "20231231",
        "cash": 10000000,
        "commission": 0.0015,
        "svr": "prod"
    }
    ```
    """
    try:
        result = run_backtest(
            stock_code=request.stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            cash=request.cash,
            commission=request.commission,
            svr=request.svr
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@app.get("/api/backtest")
async def backtest_get_endpoint(
    stock_code: str = "005930",
    start_date: str = "20220101",
    end_date: str = "20231231",
    cash: int = 10_000_000,
    commission: float = 0.0015,
    svr: str = "prod"
):
    """
    백테스팅 실행 엔드포인트 (GET 방식)
    
    쿼리 파라미터:
    - stock_code: 종목코드 (기본값: 005930)
    - start_date: 시작일 YYYYMMDD (기본값: 20220101)
    - end_date: 종료일 YYYYMMDD (기본값: 20231231)
    - cash: 초기 자본금 (기본값: 10000000)
    - commission: 수수료 (기본값: 0.0015)
    - svr: 서버 (prod 또는 vps, 기본값: prod)
    """
    try:
        result = run_backtest(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            cash=cash,
            commission=commission,
            svr=svr
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def run_backtest_multi(
    stock_codes: list[str],
    start_date: str,
    end_date: str,
    cash: int = 10_000_000,
    commission: float = 0.0015,
    svr: str = "prod"
) -> dict:
    """
    여러 종목으로 백테스팅 실행
    
    Returns:
        dict: 각 종목별 백테스팅 결과와 전체 통계
    """
    # 각 종목별 백테스팅 실행
    results = []
    total_initial_equity = 0
    total_final_equity = 0
    total_trades = 0
    successful_backtests = 0
    
    for stock_code in stock_codes:
        stock_code_str = str(stock_code).zfill(6)  # 6자리로 패딩
        
        try:
            result = run_backtest(
                stock_code=stock_code_str,
                start_date=start_date,
                end_date=end_date,
                cash=cash,
                commission=commission,
                svr=svr
            )
            
            results.append({
                "stock_code": stock_code_str,
                "success": True,
                "data": result
            })
            
            total_initial_equity += result["results"]["initial_equity"]
            total_final_equity += result["results"]["final_equity"]
            total_trades += result["results"]["total_trades"]
            successful_backtests += 1
            
        except Exception as e:
            results.append({
                "stock_code": stock_code_str,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            })
    
    # 전체 통계 계산
    total_return_pct = 0.0
    if total_initial_equity > 0:
        total_return_pct = ((total_final_equity - total_initial_equity) / total_initial_equity) * 100
    
    return {
        "total_stocks": len(stock_codes),
        "successful_backtests": successful_backtests,
        "failed_backtests": len(stock_codes) - successful_backtests,
        "start_date": start_date,
        "end_date": end_date,
        "backtest_params": {
            "initial_cash_per_stock": cash,
            "commission": commission
        },
        "aggregated_results": {
            "total_initial_equity": total_initial_equity,
            "total_final_equity": total_final_equity,
            "total_return_pct": safe_float(total_return_pct),
            "total_trades": total_trades,
            "avg_trades_per_stock": safe_float(total_trades / successful_backtests if successful_backtests > 0 else 0)
        },
        "individual_results": results
    }


def run_backtest_from_csv(
    csv_file: str,
    start_date: str,
    end_date: str,
    cash: int = 10_000_000,
    commission: float = 0.0015,
    svr: str = "prod"
) -> dict:
    """
    CSV 파일의 종목들로 백테스팅 실행
    
    Returns:
        dict: 각 종목별 백테스팅 결과와 전체 통계
    """
    # CSV 파일 읽기
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_file}")
    
    df_candidates = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    if df_candidates.empty:
        raise ValueError("CSV 파일이 비어있습니다")
    
    # 종목코드 컬럼 찾기 (다양한 컬럼명 지원)
    code_column = None
    for col in ['종목코드', 'code', 'stock_code', 'mksc_shrn_iscd']:
        if col in df_candidates.columns:
            code_column = col
            break
    
    if code_column is None:
        raise ValueError("CSV 파일에서 종목코드 컬럼을 찾을 수 없습니다")
    
    stock_codes = df_candidates[code_column].tolist()
    
    # run_backtest_multi 함수 재사용
    result = run_backtest_multi(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        cash=cash,
        commission=commission,
        svr=svr
    )
    
    result["csv_file"] = csv_file
    return result


@app.post("/api/backtest/csv")
async def backtest_csv_endpoint(request: BacktestCsvRequest):
    """
    CSV 파일의 종목들로 백테스팅 실행 엔드포인트
    
    daily_scanner.py에서 생성한 buy_candidates_YYYYMMDD.csv 파일을 사용합니다.
    
    예시:
    ```json
    {
        "csv_file": "buy_candidates_20251110.csv",
        "start_date": "20220101",
        "end_date": "20231231",
        "cash": 10000000,
        "commission": 0.0015,
        "svr": "prod"
    }
    ```
    """
    try:
        result = run_backtest_from_csv(
            csv_file=request.csv_file,
            start_date=request.start_date,
            end_date=request.end_date,
            cash=request.cash,
            commission=request.commission,
            svr=request.svr
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@app.get("/api/backtest/csv")
async def backtest_csv_get_endpoint(
    csv_file: str,
    start_date: str = "20220101",
    end_date: str = "20231231",
    cash: int = 10_000_000,
    commission: float = 0.0015,
    svr: str = "prod"
):
    """
    CSV 파일의 종목들로 백테스팅 실행 엔드포인트 (GET 방식)
    
    쿼리 파라미터:
    - csv_file: CSV 파일 경로 (필수, 예: "buy_candidates_20251110.csv")
    - start_date: 시작일 YYYYMMDD (기본값: 20220101)
    - end_date: 종료일 YYYYMMDD (기본값: 20231231)
    - cash: 종목당 초기 자본금 (기본값: 10000000)
    - commission: 수수료 (기본값: 0.0015)
    - svr: 서버 (prod 또는 vps, 기본값: prod)
    """
    try:
        result = run_backtest_from_csv(
            csv_file=csv_file,
            start_date=start_date,
            end_date=end_date,
            cash=cash,
            commission=commission,
            svr=svr
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@app.post("/api/backtest/multi")
async def backtest_multi_endpoint(request: BacktestMultiRequest):
    """
    여러 종목으로 백테스팅 실행 엔드포인트
    
    종목코드 리스트를 직접 전달하여 백테스팅합니다.
    백테스팅 기간 동안 각 종목의 조건 만족 여부는 백테스팅 라이브러리가 자동으로 판단합니다.
    
    예시:
    ```json
    {
        "stock_codes": ["005930", "000660", "028300"],
        "start_date": "20220101",
        "end_date": "20231231",
        "cash": 10000000,
        "commission": 0.0015,
        "svr": "prod"
    }
    ```
    """
    try:
        result = run_backtest_multi(
            stock_codes=request.stock_codes,
            start_date=request.start_date,
            end_date=request.end_date,
            cash=request.cash,
            commission=request.commission,
            svr=request.svr
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
