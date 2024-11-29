from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, and_
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Class logging status for a file
class Scan(Base):
    __tablename__ = 'scans'

    session = Column('session', String(15), primary_key=True)
    station = Column('station', String(2), primary_key=True)
    name = Column('name', String(50), primary_key=True)
    source = Column('source', String(15), nullable=False)

    start = Column('start', DateTime, nullable=False)
    stop = Column('stop', DateTime, nullable=False)
    preob = Column('preob', DateTime, nullable=True)

    wrap = Column('wrap', String(25), default='neutral', nullable=False)
    radar = Column('radar', Boolean, default=False, nullable=False)

    azimuth = Column('azimuth', Float, default=0.0, nullable=False)
    elevation = Column('elevation', Float, default=0.0, nullable=False)

    slew_time = Column('slew_time', Float, default=0.0, nullable=False)
    slew_az = Column('slew_az', Float, default=0.0, nullable=False)
    slew_el = Column('slew_el', Float, default=0.0, nullable=False)
    late = Column('late', Float, default=0.0, nullable=False)
    last = Column('last', String(2), default='??', nullable=False)

    use = Column('use', Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"scan {self.name} {self.source} {self.start} {self.duration})"

    def __str__(self):
        return f"{self.name} {self.session} {self.source} {self.start} {self.stop} {self.duration})"

    def __init__(self, name, station, session):
        self.name, self.station, self.session = name, station, session

    @property
    def duration(self):
        return (self.start - self.stop).total_seconds()

    @property
    def expected(self):
        return self.slew_time, self.slew_az, self.slew_el


def find(dbase, name, session, station):
    return (dbase.orm_ses.query(Scan).filter(
        and_(Scan.name.like(f'{name}%'), Scan.session == session, Scan.station == station)).first())


def get_station_list(dbase):
    return [code[0].capitalize() for code in dbase.orm_ses.query(Scan.station.distinct()).all()]


def get_station_records(dbase, station):
    return dbase.orm_ses.query(Scan).filter(Scan.station == station.casefold()).all()
