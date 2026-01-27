# tests/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    docker_compose_file: str = "docker-compose.tests.yml"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "kv_store_test"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def postgres_dsn(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


test_settings = TestSettings()
