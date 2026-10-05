import os
import sqlite3

# Importamos los modelos explícitamente
from models import Company, JobSource
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

db_path = os.getenv("DB_PATH", "./data/cv_builder.db")

if not db_path.startswith("sqlite://"):
    sqlite_url = f"sqlite:///{db_path}"
else:
    sqlite_url = db_path

connect_args = {"check_same_thread": False, "timeout": 30}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def init_db():

    SQLModel.metadata.create_all(engine)

    # Creamos los valores por defecto si no existen
    with Session(engine) as session:
        # 1. Verificar o crear Company por defecto
        default_company = session.exec(
            select(Company).where(Company.name == "Manual")
        ).first()
        if not default_company:
            default_company = Company(name="Manual")
            session.add(default_company)

        # 2. Verificar o crear JobSource por defecto
        default_source = session.exec(
            select(JobSource).where(JobSource.name == "Direct Message")
        ).first()
        if not default_source:
            default_source = JobSource(name="Direct Message")
            session.add(default_source)

        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
