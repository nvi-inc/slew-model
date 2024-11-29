from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine, event, exists, and_
from slew.database import models


# Class to handle sqlite database using sqlalchemy
# scoped_sessions is used for multithreading
class DBASE:
    def __init__(self, url):
        self.engine, self.orm_ses = create_engine(url), None
        #self.engine, self.orm_ses = None, None
        models.Base.metadata.create_all(self.engine)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        self.orm_ses = scoped_session(sessionmaker(bind=self.engine))

    def close(self):
        self.orm_ses.close()

    def commit(self):
        self.orm_ses.commit()

    def delete(self, cls, **kwargs):
        obj = self.orm_ses.query(cls).filter_by(**kwargs).first()
        if obj:
            self.orm_ses.delete(obj)

    def rollback(self):
        self.orm_ses.rollback()

    def add(self, obj):
        self.orm_ses.add(obj)

    def get_or_create(self, cls, **kwargs):
        obj = self.orm_ses.query(cls).filter_by(**kwargs).first()
        if not obj:
            obj = cls(**kwargs)
            self.orm_ses.add(obj)
        return obj
        # return self.orm_ses.query(cls).filter(**kwargs**kwargs).one()

    def get(self, cls, **kwargs):
        return self.orm_ses.query(cls).filter_by(**kwargs).first()
