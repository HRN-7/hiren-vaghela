from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = ''
    firebase_project_id: str = ''
    firebase_service_account_json: str = ''
    cors_origins: str = 'http://localhost:4173,http://terminal.local:4173'
    data_gov_api_key: str = ''
    data_gov_resource_id: str = '9ef84268-d588-465a-a308-a864a43d0070'
    osrm_url: str = 'https://router.project-osrm.org'
    nominatim_url: str = 'https://nominatim.openstreetmap.org'
    overpass_url: str = 'https://overpass-api.de/api/interpreter'
    partner_data_url: str = ''
    partner_api_key: str = ''
    model_directory: str = 'models'
    environment: str = 'development'
    push_delivery_enabled: bool = True
    push_poll_seconds: int = 15

@lru_cache
def settings():
    return Settings()
