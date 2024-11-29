import re
from slew import utc
from slew.database.models import Scan

is_pcfs = re.compile(r'(?P<time>\d{4}\.\d{3}\.\d{2}:\d{2}:\d{2}\.\d{2})(?P<data>.*)').match
is_scan = re.compile(r':scan_name=(?P<name>.*),(?P<session>.*),(?P<station>\w{2}),\d*,\d*').match  # test scan_name
is_source = re.compile(r':source=(?P<name>.*),(.*,){3}(?P<wrap>neutral|cw|ccw)').match  # test source
is_acquired = re.compile(
    '(?:flagr/antenna,acquired|#trakl#Source acquired|#trakl# Source acquired|#start#Source reached)'
).match
is_preob = re.compile(':preob').match  # test preob
is_postob = re.compile('^.{20}:postob').match  # test postob
is_end = re.compile(r':sched_end').match  # test end
is_radar = re.compile('#trakl# Masking Radar').match  # test if Masking radar
is_err = re.compile(r'#trakl#{AzErr (?P<az_err>.*) ElErr (?P<el_err>.*)}').match
is_pos = re.compile(r'#trakl#\[az\s*(?P<az>.*) el\s*(?P<el>.*) azv.*\]').match


def read_log(dbase, path):

    def make_record():
        if all((name, start_slewing, stop_slewing)):
            scan = dbase.get_or_create(Scan, name=name, station=station, session=session)
            scan.source, scan.session = source, session
            scan.start, scan.stop, scan.preob = start_slewing, stop_slewing, preob
            scan.slew_time = (stop_slewing - start_slewing).total_seconds()
            scan.late = (scan.preob - stop_slewing).total_seconds() if scan.preob else 0.0
            scan.wrap, scan.radar = wrap, radar
            if all((pos, err)):
                max_az_err = max_el_err  # abs(max_el_err / math.cos(math.radians(pos[0][1])))
                for (az, el), (a_err, e_err) in zip(pos[2:], err[2:]):
                    if abs(a_err) < max_az_err and abs(a_err) < abs(e_err):
                        scan.last = 'el'
                        break
                    if abs(e_err) < max_el_err and abs(e_err) < abs(a_err):
                        scan.last = 'az'
                        break
            dbase.commit()

    with open(path) as fh:
        max_el_err = 0.1
        wrap, radar = 'neutral', False
        name = station = session = source = start_slewing = stop_slewing = preob = None
        pos, err = [], []
        first = False
        for line in fh:
            if not (record := is_pcfs(line)):  # not a pcfs line
                continue
            data = record['data']
            if is_end(data):
                break
            if is_postob(data):
                make_record()
                pos, err = [], []
                name = None
            elif scan_rec := is_scan(data):
                make_record()
                pos, err = [], []
                name, station, session = scan_rec['name'], scan_rec['station'], scan_rec['session']
                if name.lower().startswith('no'):
                    name = f"no{int(name[2:]):05d}"
                wrap, radar = 'neutral', False
                source = start_slewing = stop_slewing = preob = None
            elif src_rec := is_source(data):
                if not source:
                    source, start_slewing, wrap = src_rec['name'], utc(pcfs=record['time']), src_rec['wrap']
            elif is_acquired(data):
                stop_slewing = stop_slewing if stop_slewing else utc(pcfs=record['time'])
            elif is_preob(data):
                preob = preob if preob else utc(pcfs=record['time'])
            elif is_radar(data):
                radar = True
            elif found := is_pos(data):
                pos.append((float(found['az']), float(found['el'])))
                first = True
            elif (found := is_err(data)) and first:
                err.append((float(found['az_err']), float(found['el_err'])))
