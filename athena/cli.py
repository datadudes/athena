import click
from athena.utils.config import AthenaConfig
import queries.query as q
from utils.cluster import get_dns
from utils.ssh import MasterNodeSSHClient, open_ssh_session
from utils.tunnel import create_tunnel
from broadcasting.mailing import mail_report, list_reports


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
def ssh():
    """ Create an interactive SSH session to the master node of the cluster. """
    open_ssh_session()


@main.command()
@click.argument('local_port', type=click.INT)
@click.argument('remote_port', type=click.INT)
def tunnel(local_port, remote_port):
    """
    Create an ssh tunnel to the master node of the cluster, forwarding traffic from the remote_port on the master node
    to the local_port on this machine
    """
    create_tunnel(local_port, remote_port)


@main.command()
@click.argument('pig_script', nargs=1, type=click.Path())
@click.argument('misc_files', nargs=-1, type=click.Path())
def pig(pig_script, misc_files):
    """ Run a Pig script on the cluster. """
    config = AthenaConfig.load_default()
    client = MasterNodeSSHClient(get_dns(), username=config.ssh.username, ssh_key=config.ssh.key_path)
    client.print_output(client.run_pig_script(pig_script, misc_files))
    client.close()


@main.command()
@click.argument('job', nargs=1, type=click.STRING)
@click.argument('recipients', nargs=-1, type=click.STRING)
@click.option('--stdout/--email', default=False)
def report(job, recipients, stdout):
    """ Generate and mail a report, optionally with attachments """
    if job == 'list':
        list_reports()
    else:
        try:
            if len(recipients) == 0:
                recipients = None
            if not job.endswith('.yml'):
                job += '.yml'
            mail_report(job, recipients, stdout)
        except ValueError as e:
            raise click.BadParameter(e.message)


@main.command()
@click.argument('src', nargs=1, type=click.STRING)
@click.argument('dst', nargs=1, type=click.STRING)
def copy(src, dst):
    config = AthenaConfig.load_default()
    client = MasterNodeSSHClient(get_dns(), username=config.ssh.username, ssh_key=config.ssh.key_path)
    client.print_output(client.dist_copy(src, dst))
    client.fix_hdfs_permissions(dst)
    client.close()
