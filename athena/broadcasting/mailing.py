from jinja2 import Environment, PackageLoader
from mailshake import SMTPMailer, EmailMessage
import yaml
from datetime import datetime
from os import listdir
from os.path import isfile, join as path_join
from athena.queries import query_impala, query_to_csv
from slugify import slugify
from athena.utils.config import ConfigDir, AthenaConfig
from athena.utils.file import create_tmp_dir


def mail_report(name, recipients=None, stdout=False):
    reports_dir = ConfigDir().sub('reports').path
    job_file = path_join(reports_dir, name)
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
            csv_path = path_join(tmpdir, filenameretrieve)
            if item['type'] == 'sql':
                sql_query = item['query']
                if 'with_items' in item:
                    variables = item['with_items']
                    for variable in variables:
                        processed_sql_query = sql_query.replace("{{ item }}", variable)
                        processed_filename = filenameretrieve.replace("{{ item }}", variable)
                        csv_path_instance = path_join(tmpdir, processed_filename)
                        query_to_csv(processed_sql_query, csv_path_instance)
                        print(csv_path_instance)
                        csvs.append({'name': processed_filename, 'path': csv_path_instance})
                else:
                    query_to_csv(sql_query, csv_path)
                    print(csv_path)
                    csvs.append({'name': filenameretrieve, 'path': csv_path})
            else:
                raise ValueError("{} contains csv item of unknown type ({})!".format(name, item['type']))

    env = Environment(loader=PackageLoader('athena.broadcasting', 'templates'))
    template = env.get_template('datamail.html')
    html = template.render(title=title, description=description, today=today, blocks=blocks)
    if stdout:
        print html
        print "\n"
        for c in csvs:
            print c
    else:
        config = AthenaConfig.load_default()

        mailer = SMTPMailer(
            host=config.mailing.smtp_host,
            port=config.mailing.smtp_port,
            username=config.mailing.smtp_username,
            password=config.mailing.smtp_password,
            use_tls=config.mailing.smtp_use_tls
        )

        email_msg = EmailMessage(
            subject="{title} {date}".format(title=title, date=today),
            text="This mail can only be viewed as HTML",
            from_email=config.mailing.from_address,
            to=recipients,
            html=html
        )
        for c in csvs:
            email_msg.attach_file(c['path'])

        mailer.send_messages(email_msg)


def list_reports():
    jobs_dir = ConfigDir().sub('reports').path
    yaml_files = [f for f in listdir(jobs_dir) if isfile(path_join(jobs_dir, f)) and f.endswith(".yml")]
    for f in yaml_files:
        print f
