from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./wallet.db"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    MARKET_REFRESH_INTERVAL_MINUTES: int = 30
    EXCHANGE_RATE_API_KEY: str = ""
    EXCHANGE_RATE_API_URL: str = "https://open.er-api.com/v6/latest"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
