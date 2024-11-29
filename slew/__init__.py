from datetime import datetime


FORMATS = dict(pcfs='%Y.%j.%H:%M:%S.%f', short='%Y.%j.%H:%M:%S', sked='%y%j-%H%M%S')


def utc(**kwargs):
    """
    Decode string of time using key word
    :param kwargs: Dictionary of format key and string.
    :return: datetime in utc.
    """
    for key, text in kwargs.items():
        if key in FORMATS:
            return datetime.strptime(text, FORMATS[key])
    return datetime.utcnow()
