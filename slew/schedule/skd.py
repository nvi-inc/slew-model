import re
import string

from collections import defaultdict
from operator import attrgetter

from slew import utc
from slew.schedule import ScheduleException, Schedule, Source, Station, Scan

is_block = re.compile(r'\s*(?P<name>\$.*)').match


class Block:

    def __init__(self, name):
        self.name = name.strip()
        self.lines = []

    def read(self, reader):
        while line := reader.readline():
            if found := is_block(line):
                return found['name'].strip()
            self.lines.append(line)
        return None


class KeyBlock(Block):
    def __init__(self, name):
        super().__init__(name)
        self.items = defaultdict(list)

    def read(self, reader):
        while line := reader.readline():
            if found := is_block(line):
                return found['name'].strip()
            code, remaining = line.split(maxsplit=1)
            self.items[code].append(remaining)
        return None


class SKD(Schedule):

    def __init__(self, path):
        super().__init__(path)

    def read(self, vie_sort=False):
        if not self.reader:
            return False

        blocks = {'$PARAM': KeyBlock('$PARAM'), '$SOURCES': KeyBlock('$SOURCES'), '$STATIONS': KeyBlock('$STATIONS')}
        # Make sure first line starts with $EXPER and decode session code
        if not (line := self.reader.readline()) or not line.startswith('$EXPER'):
            raise ScheduleException('First line does not start with $EXPER')
        self.experiment.code = line.split()[-1].strip().lower()
        # Decode all sections using special readers
        while line := self.reader.readline():
            if found := is_block(line):
                name = found['name'].strip()
                blocks[name] = block = blocks.get(name, Block(name))
                while name := block.read(self.reader):
                    blocks[name] = block = blocks.get(name, Block(name))
                break

        self.extract_experiment_data(blocks)
        keys = self.extract_station_data(blocks)
        self.extract_source_data(blocks)
        self.extract_scan_data(blocks, keys, vie_sort)
        return True

    def extract_experiment_data(self, blocks):
        items = blocks['$PARAM'].items
        self.experiment.software = items['SCHEDULING_SOFTWARE'][0].strip()
        self.experiment.version = items['SOFTWARE_VERSION'][0].strip()
        self.experiment.description = items['DESCRIPTION'][0].strip()
        self.experiment.scheduler, self.experiment.correlator = items['SCHEDULER'][0].split()[:2]

    def extract_source_data(self, blocks):
        for code, info in blocks['$SOURCES'].items.items():
            self.sources[code] = Source(code, info[0].split()[0])

    def extract_station_data(self, blocks):
        items = blocks['$STATIONS'].items
        for line in items['P']:
            code, name, _ = [v.strip() for v in line.split(maxsplit=2)]
            self.stations[code] = Station(code, name)

        return dict([(lambda v: (v[0].strip(), self.stations[v[1].strip()].code))(l.split()) for l in items['A']])

    def extract_scan_data(self, blocks, keys, vie_sort):
        scans = defaultdict(list)
        for line in blocks['$SKED'].lines:
            info = line.split()
            source, start = info[0], utc(skd=info[4])
            name = start.strftime('%j-%H%M')
            scans[name].append(scan := Scan(name))
            scan.source, scan.start = source, start
            # Extract station keys and duration
            codes = [keys[k[0]] for k in re.findall(r'..', info[9])]
            durations = [int(val) for val in info[-len(codes):]]
            scan.duration = dict(sorted(zip(codes, durations)))

        # VieSched do not sort scans as done by SKED.
        # When comparing skd and vex, skd VieSched scans should not be sorted
        sort_it = self.experiment.software == 'SKED' or not vie_sort
        for name, scans in dict(sorted(scans.items())).items():
            if len(scans) == 1:
                self.scans[scans[0].name] = scans[0]
            else:
                scans = sorted(scans, key=attrgetter('start', 'source')) if sort_it else scans
                for i, scan in enumerate(scans):
                    scan.code = scan.name = f"{name}{string.ascii_lowercase[i]}"
                    self.scans[scan.name] = scan

        for name, scan in self.scans.items():
            self.sources[scan.source].scans[name] = scan
            for code in scan.duration.keys():
                self.stations[code].scans[name] = scan



