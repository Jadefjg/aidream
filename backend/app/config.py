from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "THINK-AI"
    secret_key: str = "aidream-thinkai-local-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 7 * 24 * 60
    quota_per_unit: float = 500000
    database_url: str = "sqlite:///./aidream.db"
    upstream_base_url: str = ""
    upstream_api_key: str = ""
    server_address: str = "http://127.0.0.1:8000"
    docs_link: str = "https://zcnxuiqg768o.feishu.cn/wiki/MsWbwBaH8ijZUwkVru3cuwscnMd"
    register_gift_quota: int = 500000
    aff_quota_per_invite: int = 50000  # $0.10 邀请奖励
    cors_origins: str = "http://127.0.0.1:5180,http://localhost:5180"
    channel_circuit_threshold: int = 3
    channel_circuit_cooldown_seconds: int = 60
    database_backup_dir: str = "./backups"


settings = Settings()
