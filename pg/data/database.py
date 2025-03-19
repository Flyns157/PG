# pg.data.database.py
import sqlite3
from typing import Callable

@DeprecationWarning
def create_database():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        hash_algorithm TEXT NOT NULL,
                        encryption_key TEXT NOT NULL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS password (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        site TEXT NOT NULL,
                        key TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        date_added TEXT DEFAULT CURRENT_TIMESTAMP,
                        date_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )''')
    conn.commit()
    conn.close()


from sqlmodel import create_engine, Session, SQLModel
from sqlmodel.orm.session import Select, _TSelectParam
from sqlalchemy import Engine


engine = create_engine('sqlite:///password_manager.db')

from enum import Enum

class FetchMode(Enum):
    ALL = 1
    ONE = 2

@DeprecationWarning
def interact(statement: Select[_TSelectParam], engine: Engine = engine, session: Session | None = None, fetch_mode: FetchMode = FetchMode.ONE):
    if (must_be_closed := session is None):
        session = Session(engine)
    tmp=session.exec(statement)

    match fetch_mode:
        case FetchMode.ALL:
            result = list(tmp.all())
        case FetchMode.ONE:
            result = tmp.first()
    
    if must_be_closed:
        session.close()
    return result

def execute(func: Callable, engine: Engine = engine, session: Session | None = None, **kwargs):
    if (must_be_closed := session is None):
        session = Session(engine)

    result=func(session=session, **kwargs)
    
    if must_be_closed:
        session.close()
    return result

def query(statement: Select[_TSelectParam], engine: Engine = engine, session: Session | None = None, fetch_mode: FetchMode = FetchMode.ALL):
    def request(session: Session):
        tmp=session.exec(statement)
        match fetch_mode:
            case FetchMode.ALL:
                return list(tmp.all())
            case FetchMode.ONE:
                return tmp.first()

    return execute(
        engine=engine,
        session=session,
        func=request
    )

def insert(orm_instance: SQLModel, engine: Engine = engine, session: Session | None = None):
    def request(session: Session):
        session.add(orm_instance)
        session.commit()
        session.refresh(orm_instance)

    return execute(
        engine=engine,
        session=session,
        func=request
    )

def update(orm_instance: SQLModel, engine: Engine = engine, session: Session | None = None):
    def request(session: Session):
        session.add(orm_instance)
        session.commit()
        session.refresh(orm_instance)

    return execute(
        engine=engine,
        session=session,
        func=request
    )

