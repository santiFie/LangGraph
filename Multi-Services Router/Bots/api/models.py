from sqlalchemy import Column, String, Integer, DateTime
from database import Base
import datetime

class BotRecord(Base):
    __tablename__ = "bots"

    ip = Column(String, primary_key=True, index=True)
    last_attack = Column(DateTime, default=datetime.datetime.utcnow)
    blocked_window = Column(Integer, default=1)
    num_attacks = Column(Integer, default=1)
