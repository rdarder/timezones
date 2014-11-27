from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

#TODO: optimistic locking support (version field)
class User(Base):
  __tablename__ = 'users'
  id = Column(Integer, primary_key=True)
  login = Column(String(50), nullable=False, unique=True)
  name = Column(String(50))
  password = Column(String(100), nullable=False)


class Timezone(Base):
  __tablename__ = 'timezones'

  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('users.id'))
  user = relationship("User")
  gmt_delta_seconds = Column(Integer)
  city = Column(String(200))
