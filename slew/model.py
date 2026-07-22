import sys
import numpy as np
import matplotlib.pyplot as plt

from collections import defaultdict
from urllib import request

from copy import deepcopy
from pathlib import Path
from scipy import stats


from slew.database.models import get_station_records


class AxisModel:
    def __init__(self, axis, rate, offset):
        self.axis, self.rate, self.offset = axis, rate, offset
        self.r_value = self.p_value = 0

    def dt(self, delta):
        return abs(delta) * self.rate + self.offset

    def __str__(self):
        return f'{60/self.rate:7.1f} +{self.offset:4.1f} R:{self.r_value:5.3f} P:{self.p_value:5.3f}'

    @property
    def vals(self):
        return f'{60/self.rate:7.1f} +{self.offset:4.1f}'

    def title(self):
        return f'Rate: {60/self.rate:.1f} Offset: {self.offset:.1f}'

    def get_good_bad(self, data, threshold):
        good, bad = [], []
        for x, y in data:
            (good if abs(x * self.rate + self.offset - y) <= threshold else bad).append((x, y))
        return good, bad

    def update(self, data, threshold, factor, update_rate=True):
        good, bad = [], []
        for x, y in data:
            (good if abs(x * self.rate + self.offset - y) <= threshold else bad).append((x, y))
        dist, dt = zip(*good)
        x0, y0 = np.array(dist), np.array(dt)
        k, m, r_value, p_value, std_err = stats.linregress(x0, y0)
        if abs(k - self.rate) / self.rate > 0.5:
            res = x0 * self.rate + self.offset - y0
            print('change too large', np.mean(res), np.std(res))
            self.offset = self.offset + np.mean(res) + np.std(res) * factor
            return good, bad, np.std(res) * factor
        res = x0 * k + m - y0
        m1 = m + np.mean(res) + np.std(res) * factor
        if update_rate:
            self.rate = k
            self.r_value, self.p_value = r_value, p_value
        self.offset = m1
        return good, bad, np.std(res) * factor

    def analyze_offset(self, title, data, update=False):
        bins = list(range(-20, 21, 1))
        lists = [[] for _ in range(len(bins))]

        for val, dt in data:
            index = np.digitize(dt - (self.rate * val + self.offset), bins)
            if index < len(lists):
                lists[index].append((val, dt))

        row, offset, nbr = 0, 0, 0
        for index, (b, points) in enumerate(zip(bins, lists)):
            if (l := len(points)) > nbr:
                row, offset, nbr = index, b, l
        self.offset += offset
        records = lists[row] + lists[row+1]
        self.update(records, 2, 2.57, update_rate=update)

class AntennaSlewingModel:
    def __init__(self, catalog, code, apply_filter=True):
        self.code, self.apply_filter = code.capitalize(), apply_filter
        self.name, self.current_az_model, self.current_el_model = self.get_antenna_info(catalog)
        self.az_model, self.el_model = deepcopy(self.current_az_model), deepcopy(self.current_el_model)
        self.factor = 2.57 # 1.96 95% or 2.57 99%

    def get_antenna_info(self, catalog):
        if not (path := Path(catalog)).exists():
            print(f'Could not find {path.name} file. Downloading it.')
            url = "https://raw.githubusercontent.com/nvi-inc/sked_catalogs/refs/heads/main/antenna.cat"
            try:
                request.urlretrieve(url, path.name)
            except request.HTTPError:
                raise Exception(f'Could not download {path.name} from {url}')
        with open(path) as f:
            for line in f:
                if line.strip() and not line.startswith('*') and (info := line.split())[-3] == self.code:
                    return info[1], AxisModel('Azimuth', 60 / float(info[4]), float(info[5])
                                              ), AxisModel('Elevation', 60 / float(info[8]), float(info[9]))
            else:
                raise Exception(f'Could not find {self.code} in {catalog}')

    def get_data(self, dbase):
        records = get_station_records(dbase, self.code)
        scans = [dict(name=rec.name, d_az=rec.slew_az, d_el=rec.slew_el, dt=rec.slew_time, use=rec.use,
                      which=rec.last) for rec in records if rec.use and rec.radar is False]
        print(f'Found {len(scans)} useful scans')
        if len(scans) < 10:
            raise Exception('Not enough points to process')
        return scans

    def clean_scans(self, scans):
        az, el, suspicious = [], [], []
        max_az_dt, max_el_dt = self.az_model.dt(360) * 1.1, self.el_model.dt(90) * 1.1
        lines = []
        for scan in scans:
            dt, d_az, d_el = scan.get('dt'), scan.get('d_az'), scan.get('d_el')
            if scan['which'] == '??':
                d_az, d_rv = abs(d_az), abs(360-abs(d_az))
                t_az, t_rv = self.az_model.dt(d_az), self.az_model.dt(d_rv)
                t_el = self.el_model.dt(abs(d_el))
                r_az, r_rv, r_el = abs(t_az - dt), abs(t_rv - dt), abs(t_el - dt)
                _d_az, _t_az, _r_az = d_az, t_az, r_az
                if r_rv < r_az:
                    d_az, t_az, r_az = d_rv, t_rv, r_rv

                if abs(r_el - r_az) < 0.5:
                    if (self.az_model.dt(d_az) > dt) and (self.el_model.dt(d_el) > dt):
                        suspicious.append((dt, t_az, t_rv, t_el))
                    else:
                        scan['which'] = 'el' if self.az_model.dt(d_az) > dt else 'az'
                    continue
                scan['which'] = 'el' if r_el < r_az else 'az'
                res = dt - (t_el if scan['which'] == 'el' else t_az)
                lines.append(f"{scan['which']} {dt:6.2f}|{_d_az:6.2f} {_t_az:6.2f} {_r_az:5.2f}|"
                             f"{d_rv:6.2f} {t_rv:6.2f} {r_rv:5.2f}|{d_az:6.2f} {t_az:6.2f} {r_az:5.2f}|"
                             f"{d_el:6.2f} {t_el:6.2f} {r_el:5.2f} :{res:6.2f}")
            if scan['which'] == 'el':
                if dt < max_el_dt:
                    el.append((abs(d_el), dt))
            else:
                d_az, d_rv = abs(d_az), abs(360 - abs(d_az))
                t_az, t_rv = self.az_model.dt(d_az), self.az_model.dt(d_rv)
                if dt < max_az_dt:
                    az.append((d_az, dt) if abs(t_az - dt) < abs(t_rv - dt) else (d_rv, dt))
        return az, el, suspicious

    def process(self, dbase):
        # Keep all scans from stations
        az_threshold = el_threshold = 1.0
        scans = self.get_data(dbase)
        # Improve offset by fixing slope to original value.
        for _ in range(3):
            az_rec, el_rec, suspicious = self.clean_scans(scans)
            self.az_model.analyze_offset('az', az_rec)
            self.el_model.analyze_offset('el', el_rec)

        az_rec, el_rec, suspicious = [], [], 0
        for _ in range(2):
            az_rec, el_rec, suspicious = self.clean_scans(scans)
            self.az_model.analyze_offset('az', az_rec, update=True)
            self.el_model.analyze_offset('el', el_rec, update=True)
        print(f'Records Az {len(az_rec)} El {len(el_rec)} Unassigned {len(suspicious)}')
        print(f'Computed az model {self.az_model}')
        print(f'Computed el model {self.el_model}')

        az_val, az_rej = self.az_model.get_good_bad(az_rec, 10)
        el_val, el_rej = self.el_model.get_good_bad(el_rec, 10)
        self.plot_axis('azimuth', az_val, az_rej, self.current_az_model, self.az_model)
        self.plot_axis('elevation', el_val, el_rej, self.current_el_model, self.el_model)


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
        print(f'Generated {path} plot using {len(data):4d} points.')

        xr, yr = zip(*rej) if len(rej) else ([], [])
        x, y, = zip(*data)
        xo = np.array(x)

        discarded_points = f'Discarded points ({len(rej)})'
        valid_points = f'Valid points({len(data)})'

        fig = plt.figure()
        xy = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        #hist = fig.add_axes([0.7, 0.2, 0.2, 0.25])

        xy.plot(x, xo * current.rate + current.offset, 'c-', label=f'Current model {current.vals}', markersize=2)
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
