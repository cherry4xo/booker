from pydantic import BaseModel, UUID4


class CredentialsSchema(BaseModel):
    email: str | None
    password: str

    class Config:
        json_schema_extra = {"example": {"email": "my_mail@email.com", "password": "qwerty"}}


class JWTToken(BaseModel):
    refresh_token: str
    access_token: str
    token_type: str


class JWTAccessToken(BaseModel):
    access_token: str
    token_type: str


class JWTRefreshToken(BaseModel):
    resresh_token: str
    token_type: str


class JWTTokenData(BaseModel):
    mail: str = None


class JWTTokenPayload(BaseModel):
    user_uuid: UUID4 = None
    token_kind: str = None


class RefreshToken(BaseModel):
    refresh_token: str


class Msg(BaseModel):
    message: str = None