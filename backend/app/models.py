from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    user_metadata: dict = Field(default_factory=dict)


class SessionOut(BaseModel):
    id: str
    model_provider: str
    model_name: str


class MessageIn(BaseModel):
    content: str = Field(min_length=1)


class Citation(BaseModel):
    guest: str
    episode_title: str
    youtube_url: str | None
    chunk_id: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    skill_used: str | None
    citations: list[Citation]
