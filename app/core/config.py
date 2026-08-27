# [FILE] — app/core/config.py
"""Configuration applicative lue depuis l'environnement.

Seule source de configuration du projet : tout module qui a besoin d'un
paramètre importe le singleton ``settings`` — jamais ``os.environ``.
Les valeurs par défaut ciblent le développement local et sont écrasées
par ``.env`` puis par les variables d'environnement réelles.
"""

# ─── IMPORTS ───
from pydantic_settings import BaseSettings, SettingsConfigDict

# ──────────────

# [CODE_START]


class Settings(BaseSettings):
    """Paramètres de l'application.

    Invariants :
    - ``database_url`` doit rester cohérent avec les trois variables
      ``postgres_*`` (même utilisateur, même mot de passe, même base) ;
    - ``database_url`` utilise le driver ``postgresql+asyncpg`` : le projet
      n'ouvre aucune connexion synchrone.
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
