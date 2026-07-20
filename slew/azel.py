import re

from astropy import units
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, FK5
from astropy.time import Time

from slew import utc
from slew.database.models import find

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

def read_azel(dbase, path, station, location, session):
    with open(path) as f:
        # Read header
        for line in f:
            if line.startswith('name'):
                sta_id = line[21:].split().index(station.capitalize())
                break
        else:
            print(f'Did not find header record in {path}')
            return
        ant_loc = EarthLocation(lat=location['lat'], lon=str(360-float(location['lon'])),
                                height=float(location['alt'])*units.m)
        previous = None
        # read all record for this station
        for no, line in enumerate(f):
            if not line or line.startswith('End'):
                break
            unique, *data, durations, _ = line.split('|')
            source, start = unique.split()
            az_el, duration = data[sta_id], re.findall(r'.{4}', durations)[sta_id]
            if az_el.strip() and duration.strip():
                time_tag, name, alias = utc(sked=start), start[2:10], f'no{no:05d}'
                if (scan := find(dbase, name=name, session=session, station=station, source=source))\
                        or (scan := find(dbase, name=alias, session=session, station=station, source=source)):
                    scan.azimuth, scan.elevation = map(float, az_el.split())
                    az, el = compute_azel(ant_loc, scan.stop, scan)
                    #print(scan.name, scan.azimuth, az, scan.elevation, el)
                    setattr(scan, 'stop_az', az)
                    setattr(scan, 'stop_el', el)
                    scan.azimuth, scan.elevation = az, el
                    if previous:
                        az, el = compute_azel(ant_loc, previous.start, previous)

                        #print(f'azel 1 {previous.azimuth:6.2f} {}{previous.elevation:5.2f}')
                        #print(f'azel 2 {az:6.2f} {el:5.2f}')
                        scan.slew_az = abs(scan.azimuth - previous.azimuth)
                        scan.slew_el = abs(scan.elevation - previous.elevation)
                        #print(f'azel 1 {scan.slew_az:6.2f} {scan.slew_el:6.2f}')
                        #print(f'azel 2 {abs(scan.stop_az - az):6.2f} {abs(scan.stop_el - el):6.2f}')
                        #scan.slew_az, scan.slew_el = abs(scan.stop_az - az), abs(scan.stop_el - el)
                        scan.use = True
                    previous = scan  # dict(name=name, start=time_tag, end=end, az=az, el=el)
                else:
                    previous = None
            dbase.commit()
