import re

from pathlib import Path

from astropy import units
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, FK5
from astropy.time import Time

from slew import utc
from slew.database.models import find
from slew.schedule import skd, vex

def epoch(val):
    if val.startswith('2000'):
        return 'J2000.0'
    return 'B1950.0'

def to_angle(val):
    match = re.match(r"(?P<d>[+-]?\d{1,3})d(?P<m>\d{2})m(?P<s>\d{2}\.\d{1,8})s.*", str(val))
    return float(match['d']) + float(match['m']) / 60 + float(match['s']) / 3600

def compute_azel(ant_pos, time_tag, scan):
    try:
        ra = re.match(r'(?P<h>\d{2})(?P<m>\d{2})(?P<s>\d{2}\.\d?)', scan.src_ra)
        dec = re.match(r'(?P<d>[+-]?\d{2})(?P<m>\d{2})(?P<s>\d{2}\.\d?)', scan.src_dec)
        radec = f"{ra['h']} {ra['m']} {ra['s']} {dec['d']} {dec['m']} {dec['s']}"
        src = SkyCoord(radec, unit=(units.hourangle, units.deg), frame=FK5(equinox=epoch(scan.src_epoch)))
        t = Time(time_tag.strftime('%Y-%m-%d %H:%M:%S'), format = 'iso', scale = 'utc')
        azel = src.transform_to(AltAz(location=ant_pos, obstime=t))
        return to_angle(azel.az), to_angle(azel.alt)
    except Exception as exc:
        print(exc)
        exit(0)

def read_sched(dbase, sched, station, session, location):

    sched.open()
    sched.process()

    ant_loc = EarthLocation(lat=location['lat'], lon=str(360 - float(location['lon'])),
                            height=float(location['alt']) * units.m)
    previous = None
    for no, (scan_name, scheduled) in enumerate(sched.stations[station.capitalize()].scans.items()):
        time_tag, alias = scheduled.start, f'no{no:05d}'
        for name in (scan_name, alias):
            if scan := find(dbase, name=name, session=session, station=station, source=scheduled.source):
                az, el = compute_azel(ant_loc, scan.stop, scan)
                #print(scan.name, scan.azimuth, az, scan.elevation, el)
                setattr(scan, 'stop_az', az)
                setattr(scan, 'stop_el', el)
                scan.azimuth, scan.elevation = az, el
                if previous:
                    #az, el = compute_azel(ant_loc, previous.start, previous)
                    #print(f'azel 1 {previous.azimuth:6.2f} {}{previous.elevation:5.2f}')
                    #print(f'azel 2 {az:6.2f} {el:5.2f}')
                    scan.slew_az = abs(scan.azimuth - previous.azimuth)
                    scan.slew_el = abs(scan.elevation - previous.elevation)
                    #print(f'azel 1 {scan.slew_az:6.2f} {scan.slew_el:6.2f}')
                    #print(f'azel 2 {abs(scan.stop_az - az):6.2f} {abs(scan.stop_el - el):6.2f}')
                    #scan.slew_az, scan.slew_el = abs(scan.stop_az - az), abs(scan.stop_el - el)
                    scan.use = True
                previous = scan  # dict(name=name, start=time_tag, end=end, az=az, el=el)
                break
        else:
            previous = None
    dbase.commit()
