"""
백테스팅을 위한 과거 데이터 로더
"""
import sys
from datetime import datetime
from typing import Optional

import pandas as pd

sys.path.extend(['.'])
import kis_auth as ka
from examples_llm_stock.inquire_daily_itemchartprice.inquire_daily_itemchartprice import inquire_daily_itemchartprice


def load_stock_data(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjusted: bool = True,
    mode: str = "vps"
) -> pd.DataFrame:
    """
    KIS API에서 주식 일봉 데이터를 가져와 backtesting.py 형식으로 변환

    Args:
        stock_code: 종목 코드 (예: "005930" - 삼성전자)
        start_date: 시작일 (YYYYMMDD 형식, 예: "20230101")
        end_date: 종료일 (YYYYMMDD 형식, 예: "20231231")
        adjusted: True면 수정주가, False면 원주가
        mode: "prod"(실전) 또는 "vps"(모의), 기본값 "vps"

    Returns:
        pd.DataFrame: backtesting.py 형식의 DataFrame
            - Index: 날짜 (datetime)
            - Columns: Open, High, Low, Close, Volume

    Example:
        >>> ka.auth(svr="vps")  # 먼저 인증 필요
        >>> df = load_stock_data("005930", "20230101", "20231231")
        >>> print(df.head())
    """
    # KIS API 인증 (아직 인증 안 되어 있으면)
    try:
        ka.getTREnv().my_token
    except AttributeError:
        ka.auth(svr=mode)

    # 환경 설정
    env_dv = "real" if mode == "prod" else "demo"

    # 일봉 데이터 조회
    _, df = inquire_daily_itemchartprice(
        env_dv=env_dv,
        fid_cond_mrkt_div_code="J",  # J: KRX
        fid_input_iscd=stock_code,
        fid_input_date_1=start_date,
        fid_input_date_2=end_date,
        fid_period_div_code="D",  # D: 일봉
        fid_org_adj_prc="0" if adjusted else "1"  # 0: 수정주가, 1: 원주가
    )

    if df.empty:
        raise ValueError(f"데이터를 가져올 수 없습니다: {stock_code}")

    # backtesting.py 형식으로 변환
    # KIS API output2 컬럼명 확인 필요 (첫 조회 후 확인)
    # 일반적으로: stck_bsop_date(날짜), stck_oprc(시가), stck_hgpr(고가),
    #            stck_lwpr(저가), stck_clpr(종가), acml_vol(거래량)

    result_df = pd.DataFrame({
        'Open': pd.to_numeric(df['stck_oprc']),
        'High': pd.to_numeric(df['stck_hgpr']),
        'Low': pd.to_numeric(df['stck_lwpr']),
        'Close': pd.to_numeric(df['stck_clpr']),
        'Volume': pd.to_numeric(df['acml_vol'])
    })

    # 날짜를 인덱스로 설정 (YYYYMMDD -> datetime)
    result_df.index = pd.to_datetime(df['stck_bsop_date'], format='%Y%m%d')
    result_df.index.name = 'Date'

    # 날짜 순으로 정렬 (오래된 날짜 -> 최근 날짜)
    result_df = result_df.sort_index()

    return result_df