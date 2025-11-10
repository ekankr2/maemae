"""
환경 변수 설정 관리 (Pydantic Settings)
.env 파일이 없거나 필수 값이 누락되면 서버 시작 시 에러 발생
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """한국투자증권 API 설정"""

    # 실전투자 (필수)
    real_app: str = Field(..., description="실전투자 앱키")
    real_sec: str = Field(..., description="실전투자 앱키 시크릿")
    my_real_stock: str = Field(..., description="실전투자 증권계좌 8자리")
    my_htsid: str = Field(..., description="HTS ID")
    my_prod: str = Field(default="01", description="계좌상품코드 (기본: 01)")

    # 모의투자 (선택)
    paper_app: str = Field(default="", description="모의투자 앱키")
    paper_sec: str = Field(default="", description="모의투자 앱키 시크릿")
    my_paper_stock: str = Field(default="", description="모의투자 증권계좌 8자리")

    # 도메인 (고정값)
    domain_prod: str = "https://openapi.koreainvestment.com:9443"
    domain_vps: str = "https://openapivts.koreainvestment.com:29443"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# 싱글톤 인스턴스
# 서버 시작 시 환경 변수 검증 (없으면 에러)
settings = Settings()