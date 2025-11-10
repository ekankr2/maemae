"""
백테스팅을 위한 과거 데이터 로더
"""
import sys
from datetime import datetime, timedelta
from typing import Optional
import time

import pandas as pd

sys.path.extend(['.'])
import kis_auth as ka
from examples_llm_stock.inquire_daily_itemchartprice.inquire_daily_itemchartprice import inquire_daily_itemchartprice


def load_stock_data(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjusted: bool = True
) -> pd.DataFrame:
    """
    KIS API에서 주식 일봉 데이터를 가져와 backtesting.py 형식으로 변환

    KIS API는 한 번에 최대 100개 봉만 반환하므로,
    100일씩 나눠서 여러 번 요청해서 데이터를 이어붙임

    Args:
        stock_code: 종목 코드 (예: "005930" - 삼성전자)
        start_date: 시작일 (YYYYMMDD 형식, 예: "20230101")
        end_date: 종료일 (YYYYMMDD 형식, 예: "20231231")
        adjusted: True면 수정주가, False면 원주가

    Returns:
        pd.DataFrame: backtesting.py 형식의 DataFrame
            - Index: 날짜 (datetime)
            - Columns: Open, High, Low, Close, Volume

    Example:
        >>> ka.auth(svr="prod")  # 먼저 인증 필요
        >>> df = load_stock_data("005930", "20220101", "20231231")
        >>> print(df.head())
    """
    # KIS API 인증 (아직 인증 안 되어 있으면)
    try:
        ka.getTREnv().my_token
    except AttributeError:
        ka.auth(svr="prod")

    # 실전투자 환경
    env_dv = "real"

    # 날짜 범위를 100일씩 나눠서 여러 번 요청
    all_data = []

    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")

    current_end = end_dt

    while current_end >= start_dt:
        # 100일 전 날짜 계산 (주말 포함해서 약 140일 = 100 거래일)
        current_start = max(current_end - timedelta(days=140), start_dt)

        # API 호출
        _, df = inquire_daily_itemchartprice(
            env_dv=env_dv,
            fid_cond_mrkt_div_code="J",  # J: KRX
            fid_input_iscd=stock_code,
            fid_input_date_1=current_start.strftime("%Y%m%d"),
            fid_input_date_2=current_end.strftime("%Y%m%d"),
            fid_period_div_code="D",  # D: 일봉
            fid_org_adj_prc="0" if adjusted else "1"  # 0: 수정주가, 1: 원주가
        )

        if not df.empty:
            all_data.append(df)

        # 다음 구간으로 이동 (하루 전으로)
        current_end = current_start - timedelta(days=1)

        # API rate limit 방지 (초당 20회 제한)
        time.sleep(0.1)

    if not all_data:
        raise ValueError(f"데이터를 가져올 수 없습니다: {stock_code}")

    # 모든 데이터 합치기
    combined_df = pd.concat(all_data, ignore_index=True)

    # 중복 제거 (날짜 기준)
    combined_df = combined_df.drop_duplicates(subset=['stck_bsop_date'], keep='first')

    # backtesting.py 형식으로 변환
    result_df = pd.DataFrame({
        'Open': pd.to_numeric(combined_df['stck_oprc']),
        'High': pd.to_numeric(combined_df['stck_hgpr']),
        'Low': pd.to_numeric(combined_df['stck_lwpr']),
        'Close': pd.to_numeric(combined_df['stck_clpr']),
        'Volume': pd.to_numeric(combined_df['acml_vol'])
    })

    # 날짜를 인덱스로 설정 (YYYYMMDD -> datetime)
    result_df.index = pd.to_datetime(combined_df['stck_bsop_date'], format='%Y%m%d')
    result_df.index.name = 'Date'

    # 날짜 순으로 정렬 (오래된 날짜 -> 최근 날짜)
    result_df = result_df.sort_index()

    return result_df