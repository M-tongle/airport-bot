from pydantic import BaseModel


class Config(BaseModel):
    """Tongle Airport Bot Plugin Config"""
    tongle_airport_url: str = "https://panel.tongle.tech"