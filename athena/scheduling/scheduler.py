from celery import Celery
from athena.broadcasting.mailing import mail_report

celery_app = Celery()
celery_app.config_from_object('athena.scheduling.celeryconfig')


@celery_app.task
def process_job(name):
    mail_report(name)
