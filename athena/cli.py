import click
from click.exceptions import UsageError
from jinja2 import TemplateNotFound
from athena.utils.config import Config, ConfigDir
import queries.query as q
from queries import query_impala
from utils.cluster import get_dns
from utils.ssh import MasterNodeSSHClient, open_ssh_session
from utils.tunnel import create_tunnel
from broadcasting.mailing import mail_report, list_reports
from yaml import safe_dump
from broadcasting import slack


@click.group()
def main():
    pass


@main.command()
@click.option('--slave/--master', 'slave', default=False)
def url(slave):
    click.echo(get_dns(slave))


@main.command()
@click.argument('sql', type=click.STRING)
@click.option('--csv', type=click.Path(), help='Write the query results to the specified csv file')
def query(sql, csv):
    """ Run a SQL query on the cluster and write the results to the terminal or a CSV file. """
    click.echo(q.execute_query(sql, csv))


@main.command()
@click.argument('queryfile', type=click.File())
def batch(queryfile):
    """ Run a batch of SQL queries on the cluster and write the results to the terminal or separate CSV files. """
    q.parse_yaml_queries(queryfile)


@main.command()
@click.option('--slave/--master', 'slave', default=False)
def ssh(slave):
    """ Create an interactive SSH session to the master node of the cluster. """
    open_ssh_session(slave)


@main.command()
@click.argument('local_port', type=click.INT)
@click.argument('remote_port', type=click.INT)
@click.option('--slave/--master', 'slave', default=False)
def tunnel(local_port, remote_port, slave):
    """
    Create an ssh tunnel to the master node of the cluster, forwarding traffic from the remote_port on the master node
    to the local_port on this machine
    """
    create_tunnel(local_port, remote_port, slave)


@main.command()
@click.argument('pig_script', nargs=1, type=click.Path())
@click.argument('misc_files', nargs=-1, type=click.Path())
def pig(pig_script, misc_files):
    """ Run a Pig script on the cluster. """
    config = Config.load_default()
    client = MasterNodeSSHClient(get_dns(), username=config.ssh.username, ssh_key=config.ssh.key_path)
    client.print_output(client.run_pig_script(pig_script, misc_files))
    client.close()


@main.command()
@click.argument('job', nargs=1, type=click.STRING)
@click.argument('recipients', nargs=-1, type=click.STRING)
@click.option('--stdout/--email', default=False)
@click.option('--template', '-t', type=click.STRING, help='Template to use')
def report(job, recipients, stdout, template):
    """ Generate and mail a report, optionally with attachments """
    if job == 'list':
        list_reports()
    else:
        try:
            if len(recipients) == 0:
                recipients = None
            if not job.endswith('.yml'):
                job += '.yml'
            mail_report(job, recipients, stdout, template)
        except ValueError as e:
            raise click.BadParameter(e.message)
        except TemplateNotFound as e:
            raise click.BadParameter("Template '{}' cannot be found!".format(e.message))


@main.command()
@click.argument('sql', type=click.STRING)
@click.option('--channel', '-c', type=click.STRING, help='Slack channel you want to broadcast this query to')
@click.option('--username', '-u', type=click.STRING, help='Slack user that broadcasts this query')
@click.option('--icon', '-i', type=click.STRING, help='Icon for the resulting Slack message')
@click.option('--title', '-t', type=click.STRING, help='Title for this query')
def broadcast(sql, channel, username, icon, title):
    data, headers = query_impala(sql)
    slack.send_table(title, headers, data, username, channel, icon)


@main.command()
@click.argument('src', nargs=1, type=click.STRING)
@click.argument('dst', nargs=1, type=click.STRING)
def copy(src, dst):
    config = Config.load_default()
    client = MasterNodeSSHClient(get_dns(), username=config.ssh.username, ssh_key=config.ssh.key_path)
    client.print_output(client.dist_copy(src, dst))
    client.fix_hdfs_permissions(dst)
    client.close()


@main.command()
def init():
    config_dir = ConfigDir()

    def options(opt_list):
        def value_proc(value):
            if value in opt_list:
                return value
            else:
                raise UsageError("Response should be in [{}]".format(','.join([str(x) for x in opt_list])))
        return value_proc

    if config_dir.config_exists() and click.prompt(
            "Athena config already exists, are you sure you want to overwrite? (Y/N)",
            default='N', value_proc=options(['Y', 'y', 'N', 'n'])) == 'N':
        click.echo("Configuration already exists. No configuration initialized.")
        return

    config = {'cluster': {}}
    config['cluster']['type'] = click.prompt("Do you want to define your cluster by ip/hostnames or by "
                                             "Amazon AWS tag names? (standard/aws)",
                                             default='standard', value_proc=options(['standard', 'aws']))
    if config['cluster']['type'] == 'standard':
        master_prompt = "IP address or hostname of your master node"
        slaves_prompt = "Comma-separated list of IP addresses and/or hostnames of your slave nodes"
    else:
        master_prompt = "AWS Name tag of your master node"
        slaves_prompt = "Comma-separated list of the AWS Name tags of your slave nodes"

    config['cluster']['master'] = click.prompt(master_prompt, type=str)
    slaves = click.prompt(slaves_prompt, type=str).split(',')
    config['cluster']['slaves'] = [x.strip() for x in slaves] if len(slaves) > 1 else slaves[0].strip()

    if config['cluster']['type'] == 'aws':
        config['aws'] = {}
        config['aws']['region'] = click.prompt("AWS region where your cluster is hosted", type=str)
        config['aws']['access_key_id'] = click.prompt("Your AWS Access Key ID", type=str)
        config['aws']['secret_access_key'] = click.prompt("Your AWS Secret Access Key", type=str)

    config_dir.write('config.yml', safe_dump(config, default_flow_style=False))
    click.echo("Configuration succesfully written!")
