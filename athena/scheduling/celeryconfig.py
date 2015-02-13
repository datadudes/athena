from os import listdir
from os.path import isfile, join as path_join

from slugify import slugify
from celery.schedules import crontab
import yaml
from athena.utils.config import ConfigDir, Config


def read_schedules_from(jobs_config_dir):
    jobs_path = jobs_config_dir.path
    yaml_files = [f for f in listdir(jobs_path) if isfile(path_join(jobs_path, f)) and f.endswith(".yml")]
    sched = {}
    for yaml_file in yaml_files:
        job_file = path_join(jobs_path, yaml_file)
        with open(job_file, 'r') as f:
            job = yaml.load(f.read())
        title = job.get('title')
        key = slugify(title)
        schedule = job.get('schedule')
        if schedule:
            minute = schedule.get('minute', '*')
            hour = schedule.get('hour', '*')
            day_of_week = schedule.get('day_of_week', '*')
            day_of_month = schedule.get('day_of_month', '*')
            month_of_year = schedule.get('month_of_year', '*')
            sched[key] = {
                'task': 'athena.scheduling.scheduler.process_job',
                'schedule': crontab(minute=minute, hour=hour, day_of_week=day_of_week, day_of_month=day_of_month,
                                    month_of_year=month_of_year),
                'args': (yaml_file,)
            }
    return sched

config = Config.load_default()
BROKER_URL = config.scheduling.celery_broker_url
CELERY_RESULT_BACKEND = config.scheduling.celery_result_backend
CELERY_TIMEZONE = config.scheduling.celery_timezone
CELERYBEAT_SCHEDULE = read_schedules_from(ConfigDir().sub('reports'))
