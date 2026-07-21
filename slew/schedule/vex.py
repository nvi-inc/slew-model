import re

from collections import defaultdict

from slew import utc
from slew.schedule import ScheduleException, Schedule, Station, Source, Scan


time_units = {'psec': 1.0e-12, 'nsec': 1.0e-9, 'usec': 1.0e-6, 'msec': 1.0e-3, 'sec': 1.0, 'min': 60.0, 'hr': 3600,
              'yr': 3.154e+7}


# Compute scale between 2 time units
def time_scale(fr_unit, to_unit):
    return time_units[fr_unit] / time_units[to_unit]


# Decode time unit
def time_vex(txt, out_unit='sec'):
    dt, unit = txt.split()
    return float(dt.strip()) * time_scale(unit.strip(), out_unit)


_references = defaultdict(list)
_definitions = defaultdict(list)

is_block = re.compile(r'\s*(?P<name>\$.*);').match
is_ref = re.compile(r'\s*ref (?P<block>\$.*)\s+=\s+(?P<ref>.*);').match
is_def = re.compile(r'\s*(?P<type>def|scan) (?P<name>.*);').match
is_param = re.compile(r'\s*(?P<key>.*)\s*=\s*(?P<val>.*);').match


class Block:
    def __init__(self, name):
        self.name = name.strip()
        self.references = defaultdict(list)
        self.definitions = {}

    def read(self, reader):
        while line := reader.get_vex_line():
            if found := is_block(line):
                return found['name'].strip()
            elif found := is_ref(line):
                self.references[found['block']].append(found['ref'])
            elif (found := is_def(line)) and (_def := Definition(found['name'], found['type'])):
                self.definitions[_def.name] = _def
                _def.read(reader)
            elif found := is_param(line):
                setattr(self, found['key'], found['val'])
            else:
                raise ScheduleException(f'Line not decoded {line}')

        return None


class Definition:
    def __init__(self, name, def_type):
        self.name = name.strip()
        self.references = defaultdict(list)
        self.end = f'end{def_type}'
        self.literal = []

    def __getitem__(self, key):
        return getattr(self, key, [])

    def __setitem__(self, key, value):
        if not hasattr(self, key):
            setattr(self, key, [])
        getattr(self, key).append(value)

    def read_literal(self, reader):
        while line := reader.readline():
            if 'end_literal' in line:
                return line
            self.literal.append(line)

    def read(self, reader):
        while line := reader.get_vex_line():
            if 'start_literal' in line:
                self.read_literal(reader)
            elif self.end in line:
                return
            elif found := is_ref(line):
                self.references[found['block']].append(found['ref'])
            elif found := is_param(line):
                self[found['key'].strip()] = found['val'].strip()
        raise ScheduleException(f'No enddef found at line {line}')


class VEX(Schedule):

    def __init__(self, path):
        super().__init__(path)

    # Read skd file and extract information
    def read(self, vie_sort=False):
        if not self.reader:
            return False
        # Read first line
        if not self.reader.readline().startswith('VEX_rev'):
            raise ScheduleException('First line does not start with VEX_rev')
        # Decode all sections using special readers
        blocks = {}
        while line := self.reader.get_vex_line():
            if found := is_block(line):
                name = found['name'].strip()
                blocks[name] = block = Block(name)
                while block:
                    while name := block.read(self.reader):
                        if not (block := blocks.get(name, Block(name))):
                            break
                        blocks[name] = block
                    break
                break

        self.extract_experiment_data(blocks)
        self.extract_scan_data(blocks)
        self.extract_source_data(blocks)
        self.extract_station_data(blocks)
        return True

    def extract_experiment_data(self, blocks):
        code = blocks['$GLOBAL'].references['$EXPER'][0]
        info = blocks['$EXPER'].definitions[code]
        self.experiment.code = code.lower()
        self.experiment.description = info.exper_description[0]

    def extract_scan_data(self, blocks):
        for name, definition in blocks['$SCHED'].definitions.items():
            self.scans[name] = scan = Scan(name)
            scan.source = definition.source[0].upper()
            scan.start = utc(vex=definition.start[0])
            dur = [(lambda v: (v[0].strip(), int(time_vex(v[2]))))(val.split(':')) for val in definition.station]
            scan.duration = dict(sorted(dur))

    def extract_station_data(self, blocks):
        for code, definition in blocks['$STATION'].definitions.items():
            code, name = code.capitalize(), definition.references['$SITE'][0].upper()
            self.stations.codes[code] = self.stations.names[name] = Station(code, name)

        self.stations.scans(self.scans)

    def extract_source_data(self, blocks):
        for name, definition in blocks['$SOURCE'].definitions.items():
            name, code = name.upper(), definition.source_name[0]
            self.sources[code] = Source(code, name)

        self.sources.scans(self.scans)





