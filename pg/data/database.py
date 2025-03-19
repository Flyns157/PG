# pg.data.database.py
from typing_extensions import deprecated

from sqlmodel import create_engine, Session, SQLModel
from sqlmodel.main import is_table_model_class
from sqlmodel.orm.session import Select, _TSelectParam
from sqlalchemy import Engine
from typing import Callable


engine = create_engine('sqlite:///password_manager.db')

from enum import Enum

class FetchMode(Enum):
    ALL = 1
    ONE = 2

@deprecated("Use the execute function instead or the query function with the fetch_mode parameter")
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

def query(statement: Select[_TSelectParam], engine: Engine = engine, session: Session | None = None, fetch_mode: FetchMode = FetchMode.ONE):
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
    if not is_table_model_class(orm_instance.__class__):
        raise ValueError("Instance is not a SQLModel instance")

    def request(session: Session):
        session.add(orm_instance)
        session.commit()
        session.refresh(orm_instance)
        orm_instance.__class__.model_validate(orm_instance)

    return execute(
        engine=engine,
        session=session,
        func=request
    )

def update(orm_instance: SQLModel, engine: Engine = engine, session: Session | None = None):
    if not is_table_model_class(orm_instance.__class__):
        raise ValueError("Instance is not a SQLModel instance")
    
    def request(session: Session):
        session.add(orm_instance)
        session.commit()
        session.refresh(orm_instance)

    return execute(
        engine=engine,
        session=session,
        func=request
    )

def delete(orm_instance: SQLModel, engine: Engine = engine, session: Session | None = None):
    if not is_table_model_class(orm_instance.__class__):
        raise ValueError("Instance is not a SQLModel instance")
    
    def request(session: Session):
        session.delete(orm_instance)
        session.commit()

    return execute(
        engine=engine,
        session=session,
        func=request
    )