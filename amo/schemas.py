from pydantic import BaseModel


class OauthStateSchema(BaseModel):
    created_by_id: int
