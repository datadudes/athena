from impala.dbapi import connect
from athena.utils.cluster import get_dns
from athena.utils.config import Config
from athena.utils.file import write_csv


def query_impala(sql, params=None, fetch_one=False):
    try:
        cursor = query_impala_cursor(sql, params=params)
        field_names = [i[0] for i in cursor.description]
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        return result, field_names
    except Exception as e:
        print e
        return None


def query_impala_cursor(sql, params=None):
    config = Config.load_default()
    conn = connect(host=get_dns(slave=True), port=config.cluster.impala_port)
    cursor = conn.cursor()
    cursor.execute(sql.encode('utf-8'), params)
    return cursor


def get_date_range(days):
    from datetime import datetime, timedelta
    last_midnight = datetime.today().date()
    start_midnight = last_midnight - timedelta(days=days)

    def format_date(d):
        return '{:%Y-%m-%d 00:00:00}'.format(d)
    return format_date(start_midnight), format_date(last_midnight)


def query_to_csv(sql, csv_file):
    c = query_impala_cursor(sql)
    headers = [i[0] for i in c.description]
    write_csv(csv_file, c, headers)
