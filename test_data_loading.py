"""
데이터 로딩 테스트 스크립트

KIS API에서 데이터를 제대로 가져오는지 확인
"""
import sys
sys.path.append('.')

import kis_auth as ka
from examples_llm_stock.inquire_daily_itemchartprice.inquire_daily_itemchartprice import inquire_daily_itemchartprice


def test_data_loading():
    """
    KIS API 데이터 로딩 테스트
    """
    print("=" * 60)
    print("데이터 로딩 테스트")
    print("=" * 60)

    # 1. KIS API 인증
    print("\n[1/3] KIS API 인증 중 (실전투자 API)...")
    try:
        ka.auth(svr="prod")  # 실전투자
        print("✓ 인증 완료")
    except Exception as e:
        print(f"✗ 인증 실패: {e}")
        return

    # 2. 데이터 조회
    print("\n[2/3] 삼성전자 일봉 데이터 조회 중...")
    print("  - 종목: 005930 (삼성전자)")
    print("  - 기간: 2024-01-01 ~ 2024-12-31")

    try:
        output1, output2 = inquire_daily_itemchartprice(
            env_dv="real",  # 실전투자
            fid_cond_mrkt_div_code="J",  # KRX
            fid_input_iscd="005930",  # 삼성전자
            fid_input_date_1="20240101",
            fid_input_date_2="20241231",
            fid_period_div_code="D",  # 일봉
            fid_org_adj_prc="1"  # 원주가
        )
        print("✓ 데이터 조회 완료")
    except Exception as e:
        print(f"✗ 데이터 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. 데이터 확인
    print("\n[3/3] 데이터 확인")
    print(f"\noutput1 (메타 정보):")
    print(f"  - 타입: {type(output1)}")
    print(f"  - 크기: {output1.shape if not output1.empty else 'Empty'}")
    if not output1.empty:
        print(f"  - 컬럼: {list(output1.columns)}")
        print(f"\n샘플:\n{output1}")

    print(f"\noutput2 (일봉 데이터):")
    print(f"  - 타입: {type(output2)}")
    print(f"  - 크기: {output2.shape if not output2.empty else 'Empty'}")
    print(f"  - 데이터 개수: {len(output2)}개 봉")

    if not output2.empty:
        print(f"\n컬럼 목록:")
        for i, col in enumerate(output2.columns, 1):
            print(f"  {i:2d}. {col}")

        print(f"\n첫 5개 데이터:")
        print(output2.head())

        print(f"\n마지막 5개 데이터:")
        print(output2.tail())

        # OHLCV 컬럼 찾기
        print("\n" + "=" * 60)
        print("OHLCV 컬럼 매핑 확인")
        print("=" * 60)

        # 예상되는 컬럼명들
        possible_columns = {
            'Date': ['stck_bsop_date', 'date', 'business_date'],
            'Open': ['stck_oprc', 'open_price', 'open'],
            'High': ['stck_hgpr', 'high_price', 'high'],
            'Low': ['stck_lwpr', 'low_price', 'low'],
            'Close': ['stck_clpr', 'close_price', 'close'],
            'Volume': ['acml_vol', 'volume', 'vol']
        }

        found_columns = {}
        for ohlcv_type, candidates in possible_columns.items():
            for candidate in candidates:
                if candidate in output2.columns:
                    found_columns[ohlcv_type] = candidate
                    print(f"✓ {ohlcv_type:10s} → {candidate}")
                    break
            else:
                print(f"✗ {ohlcv_type:10s} → 못 찾음")

        # 실제 데이터 샘플 (찾은 컬럼으로)
        if len(found_columns) >= 5:
            print("\n실제 OHLCV 데이터 샘플:")
            sample_data = output2[[found_columns.get(k) for k in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'] if k in found_columns]].head()
            print(sample_data)

        return output1, output2
    else:
        print("✗ 데이터가 비어있습니다!")
        return None, None


if __name__ == "__main__":
    try:
        output1, output2 = test_data_loading()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
