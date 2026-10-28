"""Application configuration loaded from environment variables (.env supported)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # service identity
    app_name: str = "wastewise-api"
    app_env: str = "development"  # development | test | production
    version: str = "0.1.0"
    log_level: str = "INFO"

    # persistence — SQLite for the documented local prototype.
    # Production target: postgresql+psycopg://... (see deployment_guide.md)
    database_url: str = "sqlite:///./wastewise.db"

    # HTTP
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # demo / simulation
    demo_mode: bool = True

    # operational assumptions (demo defaults — clearly labelled in the UI)
    fuel_price_per_litre: float = 94.5
    fuel_consumption_l_per_100km: float = 18.0

    # routing: local haversine approximation with a road-distance factor.
    # Swap to a routing API adapter later (see architecture.md §7).
    routing_provider: str = "local-haversine"
    road_distance_factor: float = 1.30

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
