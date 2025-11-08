import os
import json
import yaml
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 설정 파일 경로
config_root = os.path.join(os.path.expanduser("~"), "KIS", "config")
os.makedirs(config_root, exist_ok=True)

# 전역 변수
g_auth = None


class KISAuth:
    """한국투자증권 API 인증 클래스"""

    def __init__(self, svr="vps", product="01"):
        """
        Args:
            svr: "prod" (실전투자) 또는 "vps" (모의투자)
            product: 계좌 상품 코드 (01: 종합계좌, 03: 선물옵션 등)
        """
        self.svr = svr
        self.product = product

        # kis_devlp.yaml 파일 로드
        yaml_path = os.path.join(os.path.dirname(__file__), "kis_devlp.yaml")
        with open(yaml_path, encoding='UTF-8') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

        # API 서버 URL 설정
        if svr == "prod":
            self.base_url = "https://openapi.koreainvestment.com:9443"
            self.app_key = self.config['my_app']
            self.app_secret = self.config['my_sec']
            self.account = self.config['my_acct_stock']
        else:  # vps (모의투자)
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            self.app_key = self.config['paper_app']
            self.app_secret = self.config['paper_sec']
            self.account = self.config['my_paper_stock']

        self.hts_id = self.config['my_htsid']
        self.user_agent = self.config['my_agent']
        self.access_token = None
        self.token_expire = None

        # 토큰 파일 경로
        self.token_file = os.path.join(config_root, f"token_{svr}.dat")

    def get_access_token(self):
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"

        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            response.raise_for_status()

            data = response.json()
            self.access_token = data['access_token']

            # 토큰 만료 시간 설정 (발급 후 24시간)
            self.token_expire = datetime.now() + timedelta(hours=23, minutes=50)

            # 토큰 파일 저장
            self._save_token()

            logger.info(f"새 토큰 발급 완료 (만료: {self.token_expire})")
            return self.access_token

        except Exception as e:
            logger.error(f"토큰 발급 실패: {e}")
            raise

    def _save_token(self):
        """토큰을 파일에 저장"""
        token_data = {
            "access_token": self.access_token,
            "token_expire": self.token_expire.isoformat()
        }
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f)

    def _load_token(self):
        """파일에서 토큰 로드"""
        if not os.path.exists(self.token_file):
            return False

        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)

            self.access_token = token_data['access_token']
            self.token_expire = datetime.fromisoformat(token_data['token_expire'])

            # 토큰이 유효한지 확인
            if datetime.now() < self.token_expire:
                logger.info(f"저장된 토큰 로드 완료 (만료: {self.token_expire})")
                return True
            else:
                logger.info("저장된 토큰이 만료됨")
                return False

        except Exception as e:
            logger.error(f"토큰 로드 실패: {e}")
            return False

    def ensure_token(self):
        """토큰이 유효한지 확인하고, 필요시 재발급"""
        if not self._load_token():
            self.get_access_token()
        return self.access_token

    def get_headers(self, tr_id, custtype="P"):
        """API 호출용 공통 헤더 생성

        Args:
            tr_id: 거래 ID (예: FHKST01010100)
            custtype: 고객구분 (P: 개인, B: 법인)
        """
        self.ensure_token()

        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": custtype,
            "user-agent": self.user_agent
        }

    def api_call(self, endpoint, tr_id, params=None, body=None, method="GET"):
        """API 호출 공통 함수

        Args:
            endpoint: API 엔드포인트
            tr_id: 거래 ID
            params: 쿼리 파라미터 (GET)
            body: 요청 바디 (POST)
            method: HTTP 메서드
        """
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers(tr_id)

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            else:
                response = requests.post(url, headers=headers, json=body)

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            raise


def auth(svr="vps", product="01"):
    """인증 초기화 (전역 변수에 저장)"""
    global g_auth
    g_auth = KISAuth(svr=svr, product=product)
    g_auth.ensure_token()
    return g_auth


def getTREnv():
    """현재 인증 객체 반환"""
    global g_auth
    if g_auth is None:
        raise Exception("인증이 필요합니다. kis_auth.auth()를 먼저 호출하세요.")
    return g_auth


def get_current_price(stock_code):
    """주식 현재가 조회 (간단한 예제)

    Args:
        stock_code: 종목코드 (예: "005930" - 삼성전자)
    """
    auth_obj = getTREnv()

    endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id = "FHKST01010100"

    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": stock_code
    }

    result = auth_obj.api_call(endpoint, tr_id, params=params)
    return result