# tests/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    docker_compose_file: str = "docker-compose.tests.yml"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


test_settings = TestSettings()
