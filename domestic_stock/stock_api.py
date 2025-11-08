"""
국내 주식 API 기능 모음
"""
import sys
sys.path.append('..')

import kis_auth as ka
import logging

logger = logging.getLogger(__name__)


def inquire_price(stock_code, market="J"):
    """주식 현재가 시세 조회

    Args:
        stock_code: 종목코드 (예: "005930")
        market: 시장구분코드 (J: 주식, ETF, ETN)

    Returns:
        현재가 정보
    """
    auth = ka.getTREnv()

    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id = "FHKST01010100"

    params = {
        "fid_cond_mrkt_div_code": market,
        "fid_input_iscd": stock_code
    }

    result = auth.api_call(endpoint, tr_id, params=params)

    if result.get('rt_cd') == '0':
        output = result.get('output', {})
        return {
            "종목코드": stock_code,
            "현재가": int(output.get('stck_prpr', 0)),
            "전일대비": int(output.get('prdy_vrss', 0)),
            "등락률": float(output.get('prdy_ctrt', 0)),
            "거래량": int(output.get('acml_vol', 0)),
            "시가": int(output.get('stck_oprc', 0)),
            "고가": int(output.get('stck_hgpr', 0)),
            "저가": int(output.get('stck_lwpr', 0)),
            "전일종가": int(output.get('stck_sdpr', 0))
        }
    else:
        logger.error(f"시세 조회 실패: {result.get('msg1')}")
        return None


def inquire_balance():
    """주식 잔고 조회

    Returns:
        보유 주식 목록
    """
    auth = ka.getTREnv()

    endpoint = "/uapi/domestic-stock/v1/trading/inquire-balance"
    tr_id = "TTTC8434R" if auth.svr == "prod" else "VTTC8434R"

    params = {
        "CANO": auth.account,
        "ACNT_PRDT_CD": auth.product,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }

    result = auth.api_call(endpoint, tr_id, params=params)

    if result.get('rt_cd') == '0':
        stocks = []
        for item in result.get('output1', []):
            stocks.append({
                "종목코드": item.get('pdno'),
                "종목명": item.get('prdt_name'),
                "보유수량": int(item.get('hldg_qty', 0)),
                "매입평균가": int(item.get('pchs_avg_pric', 0)),
                "현재가": int(item.get('prpr', 0)),
                "평가금액": int(item.get('evlu_amt', 0)),
                "평가손익": int(item.get('evlu_pfls_amt', 0)),
                "수익률": float(item.get('evlu_pfls_rt', 0))
            })
        return stocks
    else:
        logger.error(f"잔고 조회 실패: {result.get('msg1')}")
        return None


def order_cash(stock_code, order_qty, order_price, buy_sell="buy", order_type="limit"):
    """주식 현금 주문

    Args:
        stock_code: 종목코드
        order_qty: 주문수량
        order_price: 주문가격 (시장가는 0)
        buy_sell: "buy" (매수) 또는 "sell" (매도)
        order_type: "limit" (지정가) 또는 "market" (시장가)

    Returns:
        주문 결과
    """
    auth = ka.getTREnv()

    endpoint = "/uapi/domestic-stock/v1/trading/order-cash"

    # 거래 ID 설정
    if buy_sell == "buy":
        tr_id = "TTTC0802U" if auth.svr == "prod" else "VTTC0802U"
    else:
        tr_id = "TTTC0801U" if auth.svr == "prod" else "VTTC0801U"

    # 주문구분 코드
    if order_type == "market":
        ord_dvsn = "01"  # 시장가
        order_price = "0"
    else:
        ord_dvsn = "00"  # 지정가

    body = {
        "CANO": auth.account,
        "ACNT_PRDT_CD": auth.product,
        "PDNO": stock_code,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(order_qty),
        "ORD_UNPR": str(order_price)
    }

    result = auth.api_call(endpoint, tr_id, body=body, method="POST")

    if result.get('rt_cd') == '0':
        output = result.get('output', {})
        return {
            "주문번호": output.get('ODNO'),
            "주문시각": output.get('ORD_TMD'),
            "주문수량": order_qty,
            "주문가격": order_price,
            "주문구분": "매수" if buy_sell == "buy" else "매도"
        }
    else:
        logger.error(f"주문 실패: {result.get('msg1')}")
        return None


def inquire_daily_price(stock_code, start_date="", end_date="", period="D"):
    """주식 일/주/월별 시세 조회

    Args:
        stock_code: 종목코드
        start_date: 조회 시작일 (YYYYMMDD)
        end_date: 조회 종료일 (YYYYMMDD)
        period: "D" (일봉), "W" (주봉), "M" (월봉)

    Returns:
        시세 데이터 리스트
    """
    auth = ka.getTREnv()

    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    tr_id = "FHKST01010400"

    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": stock_code,
        "fid_period_div_code": period,
        "fid_org_adj_prc": "0"
    }

    result = auth.api_call(endpoint, tr_id, params=params)

    if result.get('rt_cd') == '0':
        price_list = []
        for item in result.get('output', []):
            price_list.append({
                "일자": item.get('stck_bsop_date'),
                "시가": int(item.get('stck_oprc', 0)),
                "고가": int(item.get('stck_hgpr', 0)),
                "저가": int(item.get('stck_lwpr', 0)),
                "종가": int(item.get('stck_clpr', 0)),
                "거래량": int(item.get('acml_vol', 0)),
                "거래대금": int(item.get('acml_tr_pbmn', 0))
            })
        return price_list
    else:
        logger.error(f"일별시세 조회 실패: {result.get('msg1')}")
        return None