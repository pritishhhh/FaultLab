from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from faultlab.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):  # type: ignore[no-untyped-def]
        connection.execute("PRAGMA foreign_keys=ON")

Session = sessionmaker(engine, expire_on_commit=False)


def get_db():  # type: ignore[no-untyped-def]
    with Session() as session:
        yield session
