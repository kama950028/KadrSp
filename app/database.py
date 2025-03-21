from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Синхронная строка подключения (без asyncpg)
SQLALCHEMY_DATABASE_URL = "postgresql://myuser:mypassword@localhost/mydb2"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# Синхронная зависимость
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()