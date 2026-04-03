import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Supply Chain Intelligence OS"
    API_V1_STR: str = "/api/v1"
    
    # ─── BACKEND ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field("change-this-to-a-long-random-secret", validation_alias="SECRET_KEY")
    ALGORITHM: str = Field("HS256", validation_alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(1440, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    BACKEND_PORT: int = Field(8000, validation_alias="BACKEND_PORT")
    CORS_ORIGINS: str = Field("http://localhost:5173,http://localhost:3000", validation_alias="CORS_ORIGINS")

    # ─── POSTGRES ─────────────────────────────────────────────────────────────────
    POSTGRES_USER: str = Field("scuser", validation_alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("changeme", validation_alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("supply_chain", validation_alias="POSTGRES_DB")
    POSTGRES_HOST: str = Field("postgres", validation_alias="POSTGRES_HOST")
    POSTGRES_PORT: str = Field("5432", validation_alias="POSTGRES_PORT")

    # ─── REDIS ────────────────────────────────────────────────────────────────────
    REDIS_HOST: str = Field("redis", validation_alias="REDIS_HOST")
    REDIS_PORT: str = Field("6379", validation_alias="REDIS_PORT")
    REDIS_PASSWORD: str = Field("", validation_alias="REDIS_PASSWORD")

    # ─── KAFKA ────────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field("kafka:9092", validation_alias="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_TOPIC_AIS: str = Field("ais-feed", validation_alias="KAFKA_TOPIC_AIS")
    KAFKA_TOPIC_FLIGHT: str = Field("flight-feed", validation_alias="KAFKA_TOPIC_FLIGHT")
    KAFKA_TOPIC_GEO_EVENTS: str = Field("geo-events", validation_alias="KAFKA_TOPIC_GEO_EVENTS")

    # ─── NEO4J ────────────────────────────────────────────────────────────────────
    NEO4J_URI: str = Field("bolt://neo4j:7687", validation_alias="NEO4J_URI")
    NEO4J_USERNAME: str = Field("neo4j", validation_alias="NEO4J_USERNAME")
    NEO4J_PASSWORD: str = Field("changeme", validation_alias="NEO4J_PASSWORD")

    # ─── LOCAL DATA PATHS ─────────────────────────────────────────────────────────
    DATA_RAW_PATH: str = Field("./data/raw", validation_alias="DATA_RAW_PATH")
    DATA_PROCESSED_PATH: str = Field("./data/processed", validation_alias="DATA_PROCESSED_PATH")
    
    # ─── DATA APIs ────────────────────────────────────────────────────────────────
    AISSTREAM_API_KEY: str = Field("", validation_alias="AISSTREAM_API_KEY")
    OPENSKY_USERNAME: str = Field("", validation_alias="OPENSKY_USERNAME")
    OPENSKY_PASSWORD: str = Field("", validation_alias="OPENSKY_PASSWORD")
    # ─── SUPPLIER INTELLIGENCE APIs ───────────────────────────────────────────────
    HUNTER_API_KEY: str = Field("", validation_alias="HUNTER_API_KEY")
    NEWS_API_KEY: str = Field("", validation_alias="NEWS_API_KEY")
    
    GDELT_BASE_URL: str = Field("https://api.gdeltproject.org/api/v2/doc/doc", validation_alias="GDELT_BASE_URL")
    RAPIDAPI_KEY: str = Field("", validation_alias="RAPIDAPI_KEY")
    RAPIDAPI_HOST_SUPPLYCHAIN: str = Field("supply-chain-news-api.p.rapidapi.com", validation_alias="RAPIDAPI_HOST_SUPPLYCHAIN")
    
    # ─── MLFLOW ───────────────────────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = Field("http://localhost:5000", validation_alias="MLFLOW_TRACKING_URI")

    # ─── NEO4J ────────────────────────────────────────────────────────────────────
    NEO4J_URI: str = Field("bolt://localhost:7687", validation_alias="NEO4J_URI")
    NEO4J_USER: str = Field("neo4j", validation_alias="NEO4J_USER")
    NEO4J_PASSWORD: str = Field("changeme", validation_alias="NEO4J_PASSWORD")
    
    # ─── LLM & AGENT CORE ─────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field("", validation_alias="GEMINI_API_KEY")
    SLACK_BOT_TOKEN: str = Field("", validation_alias="SLACK_BOT_TOKEN")
    SLACK_CHANNEL_ID: str = Field("", validation_alias="SLACK_CHANNEL_ID")
    
    # Base configuration loading the `.env` from mono-repo root
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def sync_database_url(self) -> str:
        import os
        return os.environ.get('DATABASE_URL', 'postgresql://scuser:scuser@postgres:5432/supply_chain')

settings = Settings()
