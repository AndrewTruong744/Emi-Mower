from pydantic import BaseModel


class GetMowerDataRequest(BaseModel):
    mower_id: str


class GetMowerDataResponse(BaseModel):
    message: str
    mower_data: dict


class UpdateMowerNameRequest(BaseModel):
    mower_id: str
    new_name: str


class UpdateMowerNameResponse(BaseModel):
    message: str
    mower_id: str
    new_name: str


class UpdateMowerOwnershipRequest(BaseModel):
    mower_id: str
    new_owner_id: str | None = None


class UpdateMowerOwnershipResponse(BaseModel):
    message: str
    mower_id: str
    new_owner_id: str | None = None
