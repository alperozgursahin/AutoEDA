from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoEDA"
    DATABASE_URL: str = "postgresql+asyncpg://autoeda_user:autoeda_password@localhost:5433/autoeda"
    REDIS_URL: str = "redis://localhost:6379/0"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
