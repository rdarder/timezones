from contextlib import contextmanager
import pinject
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import models


class SessionContext(object):
  def __init__(self, provide_db_session):
    self.provide_db_session = provide_db_session

  @property
  def session(self):
    return self.provide_db_session()

  @contextmanager
  def __call__(self):
    session = self.provide_db_session()
    try:
      yield session
      session.commit()
    except:
      session.rollback()
      raise


class DbCreator(object):
  def __init__(self, db_engine):
    self.engine = db_engine

  def create_db(self):
    models.Base.metadata.create_all(self.engine)


class DbModule(pinject.BindingSpec):
  def provide_db_engine(self, db_url, db_verbose):
    return create_engine(db_url, echo=db_verbose)

  def provide_db_session_factory(self, db_engine):
    return sessionmaker(bind=db_engine)

  def provide_db_session(self, db_session_factory):
    return db_session_factory()
