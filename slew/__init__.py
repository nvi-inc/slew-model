from datetime import datetime, timedelta

FORMATS = dict(pcfs='%Y.%j.%H:%M:%S.%f', short='%Y.%j.%H:%M:%S', sked='%y%j-%H%M%S',
               skd='%y%j%H%M%S', vex='%Yy%jd%Hh%Mm%Ss')


def utc(**kwargs):
    """
    Decode string of time using key word
    :param kwargs: Dictionary of format key and string.
    :return: datetime in utc.
    """
    for key, text in kwargs.items():
        if key in FORMATS:
            if key == 'vex' and '24h' in text:
                return datetime.strptime(text[:9], '%Yy%jd') + timedelta(days=1)
            if key == 'skd' and text[-6:] == '240000':
                return datetime.strptime(text[:5], '%y%j') + timedelta(days=1)
            return datetime.strptime(text, FORMATS[key])
    raise Exception(f'{kwargs} not valid time format')
