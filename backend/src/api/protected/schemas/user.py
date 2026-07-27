from pydantic import BaseModel


class CreateUserDataRequest(BaseModel):
    pass


class CreateUserDataResponse(BaseModel):
    message: str
    user_data: dict


class GetUserDataRequest(BaseModel):
    pass


class GetUserDataResponse(BaseModel):
    message: str
    user_data: dict


class UpdateUserEmailRequest(BaseModel):
    new_id_token: str


class UpdateUserEmailResponse(BaseModel):
    message: str
    user_id: str
    new_email: str | None = None


class UpdateUserNameRequest(BaseModel):
    new_user_name: str


class UpdateUserNameResponse(BaseModel):
    message: str
    user_id: str
    new_user_name: str


class GetZenohTokenRequest(BaseModel):
    pass


class GetZenohTokenResponse(BaseModel):
    message: str
    token: str
