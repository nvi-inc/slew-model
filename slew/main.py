import argparse

from pathlib import Path

from slew.fslog import read_log
from slew.azel import read_azel
from slew.database import DBASE
from slew.model import AntennaSlewingModel


def main():

    parser = argparse.ArgumentParser(description='Compute antenna slew models')
    parser.add_argument('-c', '--catalog', help='antenna catalog file', default='antenna.cat', required=False)
    parser.add_argument('station', help='station code', type=str.lower)
    parser.add_argument('-s', '--sessions', help='session codes', nargs='+', required=False)

    args = parser.parse_args()

    code, sessions = args.station, args.sessions

    folders = [Path(ses) for ses in sessions] if sessions else Path('.').iterdir()

    with DBASE("sqlite+pysqlite:///:memory:") as dbase:
        for folder in folders:
            if folder.is_dir() and (log := Path(folder, f'{folder.name}{code.lower()}.log')).exists() and (azel := Path(folder, f'{folder.name}.azel')).exists():
                print(f'Reading {log}')
                read_log(dbase, log)
                read_azel(dbase, azel, code, folder.name)

        AntennaSlewingModel(args.catalog, code).process(dbase)


if __name__ == '__main__':

    import sys
    sys.exit(main())
