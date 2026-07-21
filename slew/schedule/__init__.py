import re

from pathlib import Path
from operator import attrgetter
from itertools import combinations

from collections import OrderedDict


# Error with VCC problems
class ScheduleException(Exception):
    def __init__(self, err_msg):
        self.err_msg = err_msg


class Section:
    def __init__(self):
        self.codes, self.names = {}, {}

    def __getitem__(self, key):
        return self.codes.get(key, self.names.get(key, None))

    def __setitem__(self, key, value):
        self.codes[key] = self.names[value.name] = value

    def __str__(self):
        return '\n'.join([str(val) for val in sorted(self.values(), key=attrgetter('code'))])

    def __len__(self):
        return len(self.codes)

    def pop(self, code):
        item = self.codes.pop(code)
        return self.names.pop(item.name)

    def keys(self):
        return self.codes.keys()

    def items(self):
        return self.codes.items()

    def values(self):
        return self.codes.values()

    def vex(self):
        pass


class Experiment:

    def __init__(self):
        self.code = self.description = ''
        self.software, self.version = 'SKED', ''
        self.created = ''
        self.scheduler = self.correlator = ''
        self.start = self.end = None

    def __str__(self):
        return '\n'.join([f'Session {self.code.upper()} {self.description}',
                          f'Software {self.software} {self.version}',
                          f'Scheduler {self.scheduler} Correlator {self.correlator}']
                         )
        #f'Start: {self.start:%Y-%m-%d %H:%M:%S} End: {self.end:%Y-%m-%d %H:%M:%S}']
        #                 )


class Station:

    def __init__(self, code, name):
        self.code, self.name = code.capitalize(), name.upper()
        self.first_source = ''
        self.scans, self.nbr_obs = OrderedDict(), 0

    def __str__(self):
        return f"{self.code:12s} {self.name:12s} {len(self.scans):5d} scans {self.nbr_obs:5d} observations"


class Source:

    def __init__(self, code, name):
        self.code = code
        self.name = code if name == '$' else name
        self.scans, self.nbr_obs = OrderedDict(), 0

    def __str__(self):
        return f"{self.code:12s} {self.name:12s} {len(self.scans):5d} scans {self.nbr_obs:5d} observations"


class Scan:
    def __init__(self, name):
        self.code = self.name = name.strip()
        self.source, self.start = '', ''
        self.duration = {}

    def __eq__(self, other):
        if self.code != other.code or self.name != other.name or self.source != other.source \
                or len(self.duration) != len(other.duration):
            #print('bad scan info', self.code == other.code, self.name == other.name, self.source == other.source,
            #      len(self.duration) == len(other.duration))
            #print(f"[{self.code}] [{other.code}]")
            return False
        for code in list(sorted(self.duration.keys())):
            if self.duration.get(code, 0) != other.duration.get(code, 0):
                #print('bad scan duration', code, self.duration.get(code, 0), other.duration.get(code, 0))
                return False
        return True

    def __str__(self):
        sta = ' '.join(list(self.duration.keys()))
        return f"{self.name:12s} {self.source:12s} {self.start:%Y.%j.%H:%M:%S} [{sta}]"


class Sources(Section):
    def scans(self, scans):
        for index, (code, source) in enumerate(self.items()):
            source.scans = OrderedDict((scan.name, scan) for scan in scans.values()
                                       if scan.source in (code, source.name))

    def clean(self):
        for code in [code for code, src in self.items() if src.nbr_obs == 0]:
            src = self.codes.pop(code)
            self.names.pop(src.name)


class Stations(Section):
    def __init__(self):
        super().__init__()

    def scans(self, scans):
        for code, sta in self.items():
            sta.scans = OrderedDict((scan.name, scan) for scan in scans.values() if code in scan.duration)

    def clean(self):
        for code in [code for code, sta in self.items() if sta.nbr_obs == 0]:
            sta = self.codes.pop(code)
            self.names.pop(sta.name)


class Scans(Section):

    def __init__(self):
        super().__init__()
        self.codes = OrderedDict()


class Observation:
    def __init__(self, fr, to, scan):
        self.fr, self.to = fr, to
        self.source = scan.source
        self.duration = int(min(scan.duration[fr], scan.duration[to]))
        self.scan = scan

    def __str__(self):
        return f"{self.fr} {self.to} {self.source:12s} {self.duration:3.0f} {self.scan}"

    def __eq__(self, other):
        if self.fr != other.fr or self.to != other.to or self.source != other.source:
            return False
        if self.duration != other.duration:
            return False
        if self.scan != other.scan:
            return False
        return True
        #return self.fr == other.fr and self.to == other.to and self.source == other.source \
        #    and self.duration == other.duration and self.scan == other.scan


class Reader:
    def __init__(self, path, vex=False):
        self.path = Path(path)
        self.file, self.line_nbr, self.last_line = None, 0, ''
        self.current = None
        self.part = []
        self.remaining = ''

    def open(self):
        self.file = open(self.path)

    def close(self):
        self.file.close()

    def get_vex_line(self, count=0):
        # Get next part of line
        if self.part:
            return self.part.pop(0)
        # Read lines until ; is found
        line = self.remaining
        while ';' not in line:
            if not (next_line := self.readline()):
                return None
            line = f"{line}{next_line}"
        self.part = [p.rstrip() for p in re.findall(r'([^;]*;)', line) if p.strip() and p.strip()[0] != '*']
        if not self.part[-1].endswith(';'):
            self.remaining = self.part.pop()
        return self.get_vex_line(count+1)

    def readline(self, count=0):
        if not (line := self.file.readline()):
            return None
        self.line_nbr += 1
        self.last_line = line.rstrip()
        return self.last_line if line.strip() and not line.strip().startswith('*') else self.readline(count+1)


class Schedule:
    def __init__(self, path):
        self.experiment = Experiment()
        self.stations = Stations()
        self.sources = Sources()
        self.scans = Scans()
        self.observations = []
        self.reader = Reader(path) if Path(path).exists() else None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        if self.reader:
            self.reader.open()

    def close(self):
        if self.reader:
            self.reader.close()

    def __eq__(self, other):
        if self.experiment.code != other.experiment.code or len(self.observations) != len(other.observations):
            return False
        # Check if same observations
        for index, (obs1, obs2) in enumerate(zip(self.observations, other.observations)):
            if obs1 != obs2:
                return False
        return True

    @property
    def valid(self):
        return self._valid

    def read(self, vie_sort=False):
        return None

    def process(self, vie_sort=False):
        try:
            if not self.read(vie_sort):
                return False
        except ScheduleException as exc:
            print(f"schedule process {str(exc)}")
            return False
        self.make_observations()
        self.stations.clean()
        self.sources.clean()
        return True

    # Make observations
    def make_observations(self):
        for scan in self.scans.values():
            for (fr_name, to_name) in list(combinations([self.stations[c].name for c in scan.duration.keys()], 2)):
                fr, to = self.stations[fr_name].code, self.stations[to_name].code
                self.observations.append(Observation(fr, to, scan))
                self.sources[scan.source].nbr_obs += 1
                self.stations[fr].nbr_obs += 1
                self.stations[to].nbr_obs += 1

    def remove_stations(self, stations):
        for name in stations:
            if sta := self.stations[name]:
                for scan_name in [scan.name for scan in self.scans.values() if sta.code in scan.duration]:
                    scan = self.scans[scan_name]
                    scan.duration.pop(sta.code)
                    for code in scan.duration.keys():
                        self.stations[code].nbr_obs -= 1
                        self.sources[scan.source].nbr_obs -= len(scan.duration)
                    if len(scan.duration) == 1:
                        code = list(scan.duration.keys())[0]
                        self.stations[code].nbr_obs -= 1
                        self.sources[scan.source].nbr_obs -= 1
                        self.scans.pop(scan_name)
                        self.stations[code].scans.pop(scan_name)
                        self.sources[scan.source].scans.pop(scan_name)

                self.stations.pop(name)

    def summary(self):
        print(self.experiment)
        print(self.stations)
        print(self.sources)


