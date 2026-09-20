from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./patients.db"
    api_key: str = ""
    vapi_api_key: str = ""
    vapi_webhook_secret: str = ""
    vapi_assistant_id: str = ""
    vapi_phone_number_id: str = ""
    public_base_url: str = ""
    llm_model: str = "gpt-4o-mini"
    vapi_voice_id: str = "Elliot"
    log_level: str = "INFO"
    log_patient_payload: bool = True
    port: int = 8000

    @model_validator(mode="after")
    def production_safety(self):
        if self.database_url.startswith(("postgres://", "postgresql://")):
            self.database_url = "postgresql+psycopg://" + self.database_url.split("://", 1)[1]
        if self.app_env == "production":
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires persistent PostgreSQL")
            if not self.api_key or not self.vapi_webhook_secret:
                raise ValueError("Production requires API_KEY and VAPI_WEBHOOK_SECRET")
        return self


settings = Settings()
