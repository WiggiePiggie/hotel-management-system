from datetime import datetime

DATE_FMT = '%Y-%m-%d'


def today_str():
    return datetime.now().strftime(DATE_FMT)


def parse_date(value: str):
    return datetime.strptime(value, DATE_FMT)


def valid_date(value: str) -> bool:
    try:
        parse_date(value)
        return True
    except Exception:
        return False


def valid_date_range(check_in: str, check_out: str) -> bool:
    if not (valid_date(check_in) and valid_date(check_out)):
        return False
    return parse_date(check_out) > parse_date(check_in)


def nights_between(check_in: str, check_out: str) -> int:
    return (parse_date(check_out) - parse_date(check_in)).days


def calc_total(price_per_night: float, check_in: str, check_out: str) -> float:
    return round(price_per_night * nights_between(check_in, check_out), 2)
