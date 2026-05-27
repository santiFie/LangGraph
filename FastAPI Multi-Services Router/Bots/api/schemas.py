from pydantic import BaseModel
import datetime
from typing import Optional

class BotRecordBase(BaseModel):
    ip: str

class BotRecordCreate(BotRecordBase):
    pass

class BotRecordUpdate(BaseModel):
    last_attack: Optional[datetime.datetime] = None
    blocked_window: Optional[int] = None
    num_attacks: Optional[int] = None

class BotRecord(BotRecordBase):
    last_attack: datetime.datetime
    blocked_window: int
    num_attacks: int

    class Config:
        from_attributes = True
