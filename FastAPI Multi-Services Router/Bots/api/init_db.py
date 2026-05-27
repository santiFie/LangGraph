import datetime
import random
from database import engine, SessionLocal
import models

models.Base.metadata.create_all(bind=engine)

def seed_db():
    db = SessionLocal()
    if db.query(models.BotRecord).count() == 0:
        for i in range(1, 21):
            ip = f"192.168.1.{i}"
            record = models.BotRecord(
                ip=ip,
                last_attack=datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30)),
                blocked_window=random.randint(1, 5),
                num_attacks=random.randint(1, 100)
            )
            db.add(record)
        db.commit()
    db.close()

if __name__ == "__main__":
    seed_db()
    print("Database seeded with 20 records.")
