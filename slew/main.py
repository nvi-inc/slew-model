import argparse
import sys

from pathlib import Path

from slew.azel import read_azel
from slew.fslog import read_log
from slew.database import DBASE
from slew.model import AntennaSlewingModel
from slew.schedule import skd, vex
from slew.scans import read_sched

def get_schedule(folder):
    suffixes = [(".skd", skd.SKD), (".vex", vex.VEX)]
    for suffix, cls in suffixes:
        if (path := Path(folder, f"{folder}{suffix}")).exists():
            return cls(path)
    return None

def config():
    from urllib import request

    # Create executable file
    print('Create bin/slew script')
    venv = sys.prefix
    folder = Path(venv).parent
    script = Path(folder, 'bin', 'slew')
    script.parent.mkdir(parents=True, exist_ok=True)
    if not script.exists():
        with open(script, 'w') as f:
            print("#!/bin/bash", file=f)
            print(f"{venv}/bin/slew $@", file=f)
        script.chmod(0o755)
    # Download antenna.cat file
    print('Downloading antenna.cat latest file')
    if not (catalog := Path(folder, 'antenna.cat')).exists():
        url = "https://api.github.com/repos/nvi-inc/sked_catalogs/contents/antenna.cat?ref=main"
        #url = "https://raw.githubusercontent.com/nvi-inc/sked_catalogs/refs/heads/main/antenna.cat"
        try:
            request.urlretrieve(url, catalog.name)
        except request.HTTPError:
            print(f'Could not download {catalog.name} from {url}')


def main():

    parser = argparse.ArgumentParser(description='Compute antenna slew models')
    parser.add_argument('-c', '--catalog', help='antenna catalog file', default='antenna.cat', required=False)
    parser.add_argument('-v', '--verbose', help='output records', action='store_true')
    parser.add_argument('station', help='station code', type=str.lower)
    parser.add_argument('-s', '--session', help='session codes', nargs='+', required=False)

    args = parser.parse_args()

    code, sessions = args.station, args.session

    folders = [Path(ses) for ses in sessions] if sessions else Path('.').iterdir()

    try:
        asm = AntennaSlewingModel(args.catalog, code)
        with DBASE("sqlite+pysqlite:///:memory:") as dbase:
            for folder in folders:
                if folder.is_dir():
                    if (azel := Path(folder, f"{folder.name}.azel")).exists() or (sched := get_schedule(folder)):
                        for suffix in ('.log', '_full.log.bz2'):
                            if (log := Path(folder, f'{folder.name}{code.lower()}{suffix}')).exists():
                                print(f'Reading {log}')
                                location = read_log(dbase, log, args.verbose)
                                if azel.exists():
                                    read_azel(dbase, azel, code, folder.name)
                                else:
                                    read_sched(dbase, sched, code, folder.name, location)
                                break

            asm.process(dbase)
    except Exception as err:
        print(f"{str(err)} Terminated!")


if __name__ == '__main__':

    sys.exit(main())
