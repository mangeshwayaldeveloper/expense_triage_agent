from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env",env_file_encoding="utf-8")
    
    CHAT_MODEL:str="llama3.1"
    BASE_URL:str="http://localhost:11434"
    TEMPERATURE:float=0.75

settings=Settings()
    
    