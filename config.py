import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    discord_token: str
    neis_api_key: str


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    api_key = os.getenv("NEIS_API_KEY", "").strip()
    missing = [
        name
        for name, value in (
            ("DISCORD_TOKEN", token),
            ("NEIS_API_KEY", api_key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "필수 환경변수가 설정되지 않았습니다: "
            + ", ".join(missing)
            + " (.env 파일을 확인하세요.)"
        )
    return Config(discord_token=token, neis_api_key=api_key)
