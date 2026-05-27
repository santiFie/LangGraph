from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime

import models, schemas, database
from database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bots API", description="API to manage bot IPs and attacks")

@app.get("/bots/", response_model=List[schemas.BotRecord])
def read_bots(skip: int = 0, limit: int = 20, db: Session = Depends(database.get_db)):
    bots = db.query(models.BotRecord).offset(skip).limit(limit).all()
    return bots

@app.get("/bots/{ip}", response_model=schemas.BotRecord)
def read_bot(ip: str, db: Session = Depends(database.get_db)):
    bot = db.query(models.BotRecord).filter(models.BotRecord.ip == ip).first()
    if bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot

@app.post("/bots/report", response_model=schemas.BotRecord)
def report_bot(bot_ip: schemas.BotRecordCreate, db: Session = Depends(database.get_db)):
    bot = db.query(models.BotRecord).filter(models.BotRecord.ip == bot_ip.ip).first()
    if bot:
        bot.num_attacks += 1
        bot.blocked_window += 1
        bot.last_attack = datetime.datetime.now()
    else:
        bot = models.BotRecord(
            ip=bot_ip.ip,
            last_attack=datetime.datetime.now(),
            blocked_window=1,
            num_attacks=1
        )
        db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot
