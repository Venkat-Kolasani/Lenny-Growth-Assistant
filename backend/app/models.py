from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    user_metadata: dict = Field(default_factory=dict)


class SessionOut(BaseModel):
    id: str
    model_provider: str
    model_name: str
    title: str | None = None
    archived: bool = False


class SessionPatch(BaseModel):
    title: str | None = None
    archived: bool | None = None


class MessageIn(BaseModel):
    content: str = Field(min_length=1)


class Citation(BaseModel):
    guest: str
    episode_title: str
    youtube_url: str | None
    chunk_id: str


class ArtifactOut(BaseModel):
    id: str
    type: str
    title: str | None
    content: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    skill_used: str | None
    citations: list[Citation]
    reasoning: str | None = None
    artifact: ArtifactOut | None = None


class ProviderSwitch(BaseModel):
    provider: str


class ProviderInfo(BaseModel):
    id: str
    label: str
    model: str
