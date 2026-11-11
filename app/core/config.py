from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "MultiAgent_gym"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = (
        "mysql+pymysql://root:your_password@127.0.0.1:3306/"
        "multiagent_gym?charset=utf8mb4"
    )
    auto_create_tables: bool = True
    seed_demo_data: bool = False
    allow_legacy_plaintext_passwords: bool = False

    jwt_secret: str = "change-me-before-production-multiagent-gym-python-2026"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 主 Agent 使用 OpenAI 兼容接口，默认沿用原有火山方舟配置。
    agent_name: str = "Mira"
    agent_provider: str = "ark"
    agent_model: str = "deepseek-v4-flash-ga-260731"
    agent_api_key: str = ""
    agent_base_url: str = ""
    agent_temperature: float = 0.3
    agent_max_tokens: int = 1600
    agent_timeout_seconds: float = 60.0
    agent_max_tool_rounds: int = 4
    agent_knowledge_top_k: int = 5
    agent_knowledge_file: str = "data/健身知识大全_核心版_v0.5.md"

    rag_enabled: bool = True
    rag_required: bool = False
    rag_auto_index: bool = True
    rag_milvus_uri: str = ""
    rag_milvus_token: str = ""
    rag_collection: str = "gym_knowledge_v1"
    rag_dense_dimensions: int = 1024
    rag_candidate_limit: int = 20
    rag_dense_weight: float = 0.4
    rag_keyword_weight: float = 0.6
    rag_embedding_concurrency: int = 3
    embedding_api_key: str = ""
    embedding_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    embedding_model: str = "doubao-embedding-vision-251215"
    embedding_timeout_seconds: float = 60.0

    waitlist_offer_minutes: int = 15
    checkin_token_seconds: int = 45
    checkin_open_minutes_before: int = 30
    checkin_close_minutes_after: int = 15
    no_show_grace_minutes: int = 30
    no_show_lookback_days: int = 2
    no_show_auto_enabled: bool = True
    maintenance_interval_seconds: int = 60
    frontend_public_url: str = "http://127.0.0.1:9000"

    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins or ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
