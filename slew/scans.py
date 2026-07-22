import re

from astropy import units
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, FK5
from astropy.time import Time

from slew.database.models import find

get_ra = re.compile(r'(?P<h>\d{2})(?P<m>\d{2})(?P<s>\d{2}\.\d?)').match
get_dec = re.compile(r'(?P<d>[+-]?\d{2})(?P<m>\d{2})(?P<s>\d{2}\.\d?)').match
angle = re.compile(r"(?P<d>[+-]?\d{1,3})d(?P<m>\d{2})m(?P<s>\d{2}\.\d{1,8})s.*").match

def epoch(val):
    return 'J2000.0' if val.startswith('2000') else 'B1950.0'

def to_angle(val):
    match = angle(str(val))
    return float(match['d']) + float(match['m']) / 60 + float(match['s']) / 3600

def compute_azel(ant_pos, time_tag, scan):
    try:
        ra = get_ra(scan.src_ra)
        dec = get_dec(scan.src_dec)
        radec = f"{ra['h']} {ra['m']} {ra['s']} {dec['d']} {dec['m']} {dec['s']}"
        src = SkyCoord(radec, unit=(units.hourangle, units.deg), frame=FK5(equinox=epoch(scan.src_epoch)))
        t = Time(time_tag.strftime('%Y-%m-%d %H:%M:%S'), format = 'iso', scale = 'utc')
        azel = src.transform_to(AltAz(location=ant_pos, obstime=t))
        return to_angle(azel.az), to_angle(azel.alt)
    except Exception as exc:
        print(exc)
        exit(0)

def read_sched(dbase, sched, station, session, location):

    print(f'Reading {sched.path}')

    sched.open()
    sched.process()

    ant_loc = EarthLocation(lat=location['lat'], lon=str(360 - float(location['lon'])),
                            height=float(location['alt']) * units.m)
    previous = None
    for no, (scan_name, scheduled) in enumerate(sched.stations[station.capitalize()].scans.items()):
        time_tag, alias = scheduled.start, f'no{no:05d}'
        for name in (scan_name, alias):
            if scan := find(dbase, name=name, session=session, station=station, source=scheduled.source):
                scan.azimuth, scan.elevation = compute_azel(ant_loc, scan.stop, scan)
                if previous:
                    scan.slew_az = abs(scan.azimuth - previous.azimuth)
                    scan.slew_el = abs(scan.elevation - previous.elevation)
                    scan.use = True
                previous = scan
                break
        else:
            previous = None
    dbase.commit()
