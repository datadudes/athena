from celery import Celery
from jinja2 import Environment, PackageLoader
import sendgrid
import yaml
from datetime import datetime
from os import listdir
from os.path import isfile, join
from athena.queries import query_impala, query_to_csv
from slugify import slugify
from athena.utils.config import ConfigDir, AthenaConfig
from athena.utils.file import create_tmp_dir

celery_app = Celery()
celery_app.config_from_object('athena.scheduling.celeryconfig')


@celery_app.task
def process_job(name, recipients=None, stdout=False):
    jobs_dir = ConfigDir().sub('reports').path
    job_file = jobs_dir + '/' + name
    if not isfile(job_file):
        raise ValueError("{} does not exist or is not a readable file!".format(name))
    with open(job_file, 'r') as f:
        job = yaml.load(f.read())
    title = job.get('title')
    description = job.get('description')
    data = job.get('data')
    inline_blocks = data.get('inline')
    csv_items = data.get('csv')
    today = datetime.now().date().strftime('%d %b %Y')

    if not recipients:
        job_recepients = job.get('recipients')
        recipients = [recipient.strip() for recipient in job_recepients.split(',')] if job_recepients else None
    if not data or (not inline_blocks and not csv_items):
        raise ValueError("Your job config must contain a 'data' section with one or more inline or csv entries")
    if not recipients and not stdout:
        raise ValueError("No recipients to send the data!")

    blocks = []
    if inline_blocks:
        for block_item in inline_blocks:
            block = {'name': block_item['name'], 'description': block_item['description']}
            if block_item['type'] == 'sql':
                rows, headers = query_impala(block_item['query'])
                block['data'] = {'headers': headers, 'rows': rows}
            else:
                raise ValueError("{} contains an inline block of unknown type ({})!".format(name, block_item['type']))

            blocks.append(block)
    csvs = []
    if csv_items:
        tmpdir = create_tmp_dir(prefix=slugify(title, separator='_'))
        for item in csv_items:
            filenameretrieve = item['filename']
            csv_path = tmpdir + '/' + filenameretrieve
            if item['type'] == 'sql':
                sql_query = item['query']
                if 'with_variables' in item:
                    variables = item['with_variables']
                    for variable in variables:
                        processed_sql_query = sql_query.replace("{{ variable }}", variable)
                        processed_filename = filenameretrieve.replace("{{ variable }}", variable)
                        csv_path_instance = tmpdir + '/' + processed_filename
                        query_to_csv(processed_sql_query, csv_path_instance)
                        print(csv_path_instance)
                        csvs.append({'name': processed_filename, 'path': csv_path_instance})
                else:
                    query_to_csv(sql_query, csv_path)
                    print(csv_path)
                    csvs.append({'name': filenameretrieve, 'path': csv_path})
            else:
                raise ValueError("{} contains csv item of unknown type ({})!".format(name, item['type']))

    env = Environment(loader=PackageLoader('scheduling', 'templates'))
    template = env.get_template('datamail.html')
    html = template.render(title=title, description=description, today=today, blocks=blocks)
    if stdout:
        print html
        print "\n"
        for c in csvs:
            print c
    else:
        config = AthenaConfig.load_default()
        sg = sendgrid.SendGridClient(config.mailing.sendgrid_username, config.mailing.sendgrid_password)
        message = sendgrid.Mail()
        message.set_subject("{title} {date}".format(title=title, date=today))
        message.set_html(html)
        message.set_text('This mail can only be viewed as HTML')
        message.set_from(config.mailing.from_address)
        for recipient in recipients:
            message.add_to(recipient)
        for c in csvs:
            message.add_attachment(c['name'], c['path'])
        status, msg = sg.send(message)


def list_jobs():
    jobs_dir = ConfigDir().sub('reports').path
    yaml_files = [f for f in listdir(jobs_dir) if isfile(join(jobs_dir, f)) and f.endswith(".yml")]
    for f in yaml_files:
        print f
