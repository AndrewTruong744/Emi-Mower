from pydantic import BaseModel


class GetMowerDataRequest(BaseModel):
    pass


class GetMowerDataResponse(BaseModel):
    message: str
    mower_data: dict


class UpdateMowerNameRequest(BaseModel):
    new_name: str


class UpdateMowerNameResponse(BaseModel):
    message: str
    mower_id: str
    new_name: str


class UpdateMowerOwnershipRequest(BaseModel):
    new_owner_id: str | None = None


class UpdateMowerOwnershipResponse(BaseModel):
    message: str
    mower_id: str
    new_owner_id: str | None = None
