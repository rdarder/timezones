import argparse
import models
import sqlalchemy

if __name__ == '__main__':
  parser = argparse.ArgumentParser('Create timezones db')
  parser.add_argument('db_url', help='DB url (sqlalchemy format)')
  args = parser.parse_args()
  engine = sqlalchemy.create_engine(args.db_url)
  models.Base.metadata.create_all(engine)