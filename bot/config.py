import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    OWNER_CHAT_ID: int = int(os.getenv("OWNER_CHAT_ID", "0") or 0)
    TZ: str = os.getenv("TZ", "Europe/Moscow")


settings = Settings()
