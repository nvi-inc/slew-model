import re

from slew import utc
from slew.database.models import find


def read_azel(dbase, path, station, session):
    with open(path) as f:
        # Read header
        for line in f:
            if line.startswith('name'):
                sta_id = line[21:].split().index(station.capitalize())
                break
        else:
            print(f'Did not find header record in {path}')
            return
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
                    if previous:
                        scan.slew_az = abs(scan.azimuth - previous.azimuth)
                        scan.slew_el = abs(scan.elevation - previous.elevation)
                        scan.use = True
                    previous = scan  # dict(name=name, start=time_tag, end=end, az=az, el=el)
                else:
                    previous = None
            dbase.commit()
