# [FILE] — app/core/config.py
"""Application configuration read from the environment.

The project's single source of configuration: any module that needs a
setting imports the ``settings`` singleton — never ``os.environ``.
Default values target local development and are overridden by ``.env``
then by the real environment variables.
"""

# ─── IMPORTS ───
from pydantic_settings import BaseSettings, SettingsConfigDict

# ──────────────

# [CODE_START]


class Settings(BaseSettings):
    """Application settings.

    Invariants:
    - ``database_url`` must stay consistent with the three ``postgres_*``
      variables (same user, same password, same database);
    - ``database_url`` uses the ``postgresql+asyncpg`` driver: the
      project opens no synchronous connection.
    """

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/alpha_scope_dev"
    debug: bool = False
    log_level: str = "INFO"
    postgres_db: str = "alpha_scope_dev"
    postgres_password: str = "password"
    postgres_user: str = "postgres"
    sqlalchemy_echo: bool = False


settings = Settings()
