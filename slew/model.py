import numpy as np
import matplotlib.pyplot as plt

from copy import deepcopy
from pathlib import Path
from scipy import stats

from slew.database.models import get_station_records



class AxisModel:
    def __init__(self, axis, rate, offset):
        self.axis, self.rate, self.offset = axis, rate, offset

    def dt(self, delta):
        return delta * self.rate + self.offset

    def __str__(self):
        return f'{60/self.rate:7.1f}+{self.offset:4.1f}'

    def title(self):
        return f'Rate: {60/self.rate:.1f} Offset: {self.offset:.1f}'

    def update(self, data, threshold, factor):
        good, bad = [], []
        for x, y in data:
            (good if abs(x * self.rate + self.offset - y) <= threshold else bad).append((x, y))
        dist, dt = zip(*good)
        x0, y0 = np.array(dist), np.array(dt)
        k, m, r_value, p_value, std_err = stats.linregress(x0, y0)
        res = x0 * k + m - y0
        m1 = m + np.mean(res) + np.std(res) * factor
        self.rate, self.offset = k, m1
        return good, bad, np.std(res) * factor


class AntennaSlewingModel:
    def __init__(self, catalog, code, apply_filter=True):
        self.catalog = catalog
        self.code, self.apply_filter = code.capitalize(), apply_filter
        self.name, self.current_az_model, self.current_el_model = self.get_antenna_info()
        self.az_model, self.up_model = deepcopy(self.current_az_model), deepcopy(self.current_el_model)
        self.dn_model = deepcopy(self.current_el_model)
        self.factor = 2.57  # 1.96 95% or 2.57 99%

    def get_antenna_info(self):
        if not (path := Path(self.catalog)).exists():
            raise Exception(f'Could not find {self.catalog}')
        with open(path) as f:
            for line in f:
                if line.strip() and not line.startswith('*') and (info := line.split())[-1] == self.code:
                    return info[1], AxisModel('Azimuth', 60 / float(info[4]), float(info[5])
                                              ), AxisModel('Elevation', 60 / float(info[8]), float(info[9]))
            else:
                raise Exception(f'Could not find {self.code} in antenna.cat')

    def get_data(self, dbase):
        records = get_station_records(dbase, self.code)
        scans = [dict(name=rec.name, d_az=rec.slew_az, d_el=rec.slew_el, dt=rec.slew_time, use=rec.use,
                      which=rec.last) for rec in records if rec.use and rec.last != '??']
        print(f'Found {len(scans)} useful scans')
        return scans

    def clean_scans(self, dbase):
        az, el = [], []
        for scan in self.get_data(dbase):
            if scan['which'] == 'el':
                el.append((abs(scan['d_el']), scan['dt']))
            else:
                dt, d_az = scan.get('dt'), scan.get('d_az')
                #if dt > 25:
                #    print(scan['name'], 'az', dt, d_az)
                d_az, d_rv = abs(d_az), abs(360 - abs(d_az))
                t_az, t_rv = self.current_az_model.dt(d_az), self.current_az_model.dt(d_rv)
                if abs(t_az - dt) < abs(t_rv - dt):
                    # az.append((d_az if t_az < t_rv else d_rv, dt))
                    az.append((d_az, dt))
                else:
                    az.append((d_rv, dt))

        return az, el, []

    def process(self, scans):
        # Keep all scans from stations
        az_threshold = up_threshold = dn_threshold = 100
        az_rec, up_rec, dn_rec = self.clean_scans(scans)
        for iteration in range(10):
            az_val, az_rej, az_threshold = self.az_model.update(az_rec, max(2, az_threshold*2), self.factor)
            up_val, up_rej, up_threshold = self.up_model.update(up_rec, max(2, up_threshold*2), self.factor)
            #  dn_val, dn_rej, dn_threshold = self.dn_model.update(dn_rec, max(2, dn_threshold*2), self.factor)
        print(f'Computed az model {self.az_model}')
        print(f'Computed el model {self.up_model}')
        self.plot_axis('azimuth', az_val, az_rej, self.current_az_model, self.az_model)
        self.plot_axis('elevation', up_val, up_rej, self.current_el_model, self.up_model)

    def save_slow_scans(self, scans, filename):
        with open(filename, 'w') as f:
            for scan in scans:
                start, end, preob = scan.get('begin'), scan.get('end'), scan.get('preob')
                d_az, d_el = scan.get('d_az'), scan.get('d_el')
                if all((start, end, preob, d_az, d_el)):
                    d_az, d_rv, d_el = abs(d_az), abs(360 - abs(d_az)), abs(d_el)
                    dt = (end - start).total_seconds()
                    t_az, t_rv, t_el = abs(self.az.dt(d_az)), abs(self.az.dt(d_rv)), abs(self.el.dt(d_el))
                    if dt > max(min(t_az, t_rv), t_el):
                        print(f"{scan['name']:12s} {d_az:5.1f} {d_el:5.1f} {dt:5.1f} {t_az:5.1f}"
                              f"{t_rv:5.1f} {t_el:5.1f} {scan['which']}", file=f)

    def remove_bad_res(self, code, data):
        dist, dt = zip(*data)
        x0, y0 = np.array(dist), np.array(dt)
        vel, cnt = self.estimated.get(code)
        threshold = np.std(x0 * vel + cnt - y0) * self.factor
        good, bad = [], []
        for x, y in data:
            (good if abs(x * vel + cnt - y) <= threshold else bad).append((x,y))
        return good, bad

    def plot_axis(self, code, data, rej, current, estimated):

        if not data:
            print('Could not generate plot. No data points!')
            return
        path = Path(self.code.capitalize(), f'{code[:2]}.png')
        path.parent.mkdir(exist_ok=True)
        print(f'Generate {path} plot using {len(data):4d} points.')

        xr, yr = zip(*rej) if len(rej) else ([], [])
        x, y, = zip(*data)
        xo = np.array(x)

        discarded_points = f'Discarded points ({len(rej)})'
        valid_points = f'Valid points({len(data)})'

        fig = plt.figure()
        xy = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        #hist = fig.add_axes([0.7, 0.2, 0.2, 0.25])

        #current, estimated = (self.current_az_model, self.az_model) if code == 'azimuth' else (self.current_el_model, self.el_model)
        xy.plot(x, xo * current.rate + current.offset, 'c-', label=f'Current model {current}', markersize=2)
        xy.plot(x, xo * estimated.rate + estimated.offset, 'k-', label='Calculated model', markersize=2)
        #xy.plot(xo / calc[0] + calc[1], x, 'k-', label='Calculated model', markersize=2)
        xy.plot(xr, yr, 'rx', label=discarded_points, markersize=2)
        xy.plot(x, y, 'b+', label=valid_points, markersize=2)
        xy.legend(loc='upper left', numpoints=1)
        xy.grid(True)
        xy.set_xlabel(r'$Distance [Degree]$')
        xy.set_ylabel(r'$Time [s]$')
        xy.set_title(f'{self.name} {code} \n{estimated.title()}')
        xy.set_xlim(left=0)
        xy.set_ylim(bottom=0)

        #self.plotHistogram(hist, code)
        plt.savefig(path)
        plt.close()


def get_sessions():
    return [file for file in Path('.').iterdir() if file.is_dir()]


def validate_folders(station, folders):
    return [folder for folder in folders if Path(folder, f'{folder.name}.azel').exists() and
            Path(folder, f'{folder.name}{station.lower()}.log').exists()]
