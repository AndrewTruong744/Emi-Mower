"""Generated from ``backend/zenoh_asyncapi.yaml``.

Do not edit manually. Regenerate with ``backend/scripts/generate_types.sh``.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str


class UserData(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    email: str
    name: str
    created_at: datetime | None = None


class UserLoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    token: str
    expires_in: int
    user_data: UserData


class ProblemDetails(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    timestamp: datetime


WireMessage = UserLoginRequest | UserLoginResponse | ProblemDetails | dict[str, Any]
