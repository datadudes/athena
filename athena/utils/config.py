from __future__ import absolute_import
from __future__ import with_statement

import errno
from os import remove, removedirs
from os.path import isfile, join as path_join
from click.utils import get_app_dir
from athena.utils.file import mkdir_p, touchopen
import yaml


def is_collection(obj):
    """Tests if an object is a collection. Strings don't count."""

    if isinstance(obj, basestring):
        return False

    return hasattr(obj, '__getitem__')


class ConfigDir(object):
    """Config Directory object."""

    def __init__(self, path=None):
        if not path:
            self.path = get_app_dir('athena', force_posix=True)
        else:
            self.path = path
        mkdir_p(self.path)  # It's at easier to just try and create the dir, even if it might already exist

    def __repr__(self):
        return '<config-dir: {}>'.format(self.path)

    def open_file(self, filename, mode='r'):
        """Returns file object from given filename. Creates it if it doesn't exist """

        fn = path_join(self.path, filename)

        return touchopen(fn, mode)

    def open_athena_config(self, mode='r'):
        return self.open_file('config.yml', mode=mode)

    def write(self, filename, content, binary=False):
        """Writes given content to given filename."""
        fn = path_join(self.path, filename)

        if binary:
            flags = 'wb'
        else:
            flags = 'w'

        with open(fn, flags) as f:
            f.write(content)

    def append(self, filename, content, binary=False):
        """Appends given content to given filename."""

        fn = path_join(self.path, filename)

        if binary:
            flags = 'ab'
        else:
            flags = 'a'

        with open(fn, flags) as f:
            f.write(content)
            return True

    def delete(self, filename=''):
        """Deletes given file or directory. If no filename is passed, current
        directory is removed.
        """
        fn = path_join(self.path, filename)

        try:
            if isfile(fn):
                remove(fn)
            else:
                removedirs(fn)
        except OSError as why:
            if why.errno == errno.ENOENT:
                pass
            else:
                raise why

    def read(self, filename, binary=False):
        """Returns contents of given file in ConfigDir.
        If file doesn't exist, returns None."""

        fn = path_join(self.path, filename)

        if binary:
            flags = 'br'
        else:
            flags = 'r'

        try:
            with open(fn, flags) as f:
                return f.read()
        except IOError:
            return None

    def sub(self, path):
        """Returns AppDir instance for given subdirectory name."""

        if is_collection(path):
            path = path_join(path)

        return ConfigDir(path_join(self.path, path))


class AthenaConfig(object):

    def __init__(self, ssh=None, cluster=None, aws=None, mailing=None, scheduling=None):
        self.ssh = ssh
        self.cluster = cluster
        self.aws = aws
        self.mailing = mailing
        self.scheduling = scheduling

    @staticmethod
    def load(config_file):
        values = yaml.safe_load(config_file)

        impala_port = values['cluster']['impala_port'] if 'impala_port' in values['cluster'] else 21050
        infra_type = values['cluster']['type'].strip() if 'type' in values['cluster'] else 'standard'
        cluster = ClusterConfig(
            infra_type,
            values['cluster']['master'].strip(),
            [slave.strip() for slave in values['cluster']['slaves'].split(',')],
            impala_port
        )

        if 'ssh' in values:
            username = values['ssh']['username'].strip() if 'username' in values['ssh'] else None
            key_path = values['ssh']['key_path'].strip() if 'key_path' in values['ssh'] else None
            ssh = SSHConfig(
                username,
                key_path
            )
        else:
            # SSH is always used, so we require a default
            ssh = SSHConfig()

        if 'aws' in values:
            aws = AWSConfig(
                values['aws']['access_key_id'].strip(),
                values['aws']['secret_access_key'].strip(),
                values['aws']['region'].strip()
            )
        else:
            aws = None

        if 'mailing' in values:
            smtp_host = values['mailing']['smtp_host'].strip() if 'smtp_host' in values['mailing'] else 'localhost'
            smtp_port = values['mailing']['smtp_port'] if 'smtp_port' in values['mailing'] else 587
            smtp_username = values['mailing']['smtp_username'].strip() if 'smtp_username' in values['mailing'] else None
            smtp_password = values['mailing']['smtp_password'].strip() if 'smtp_password' in values['mailing'] else None
            smtp_tls = values['mailing']['smtp_use_tls'] if 'smtp_use_tls' in values['mailing'] else True
            if 'from_address' in values['mailing']:
                from_address = values['mailing']['from_address'].strip()
            else:
                from_address = 'data@example.com'
            mailing = MailingConfig(
                smtp_host,
                smtp_port,
                smtp_username,
                smtp_password,
                from_address,
                smtp_tls
            )
        else:
            mailing = MailingConfig()

        if 'scheduling' in values:
            scheduling = SchedulingConfig(
                values['scheduling']['celery_broker_url'].strip(),
                values['scheduling']['celery_result_backend'].strip(),
                values['scheduling']['celery_timezone'].strip()
            )
        else:
            scheduling = None

        return AthenaConfig(ssh, cluster, aws, mailing, scheduling)

    @staticmethod
    def load_default():
        config_file = ConfigDir().open_athena_config()
        config_obj = AthenaConfig.load(config_file)
        config_file.close()
        return config_obj


class ClusterConfig(object):

    ALLOWED_INFRA_TYPES = ['standard', 'aws']

    def __init__(self, infra_type='standard', master_node='', slave_nodes=[], impala_port=21050):
        self.infra_type = infra_type
        self.master_node = master_node
        self.slave_nodes = slave_nodes
        self.impala_port = impala_port
        if self.infra_type not in self.ALLOWED_INFRA_TYPES:
            raise ConfigurationError


class SSHConfig(object):

    def __init__(self, username=None, key_path=None):
        self.username = username
        self.key_path = key_path


class AWSConfig(object):

    def __init__(self, access_key_id=None, secret_access_key=None, region=None):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region


class MailingConfig(object):

    def __init__(self, smtp_host='localhost', smtp_port=587, smtp_username=None, smtp_password=None,
                 from_address='data@example.com', smtp_use_tls=True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls
        self.from_address = from_address


class SchedulingConfig(object):

    def __init__(self, celery_broker_url=None, celery_result_backend=None, celery_timezone='Europe/Amsterdam'):
        self.celery_broker_url = celery_broker_url
        self.celery_result_backend = celery_result_backend
        self.celery_timezone = celery_timezone


class ConfigurationError(Exception):
    def __init__(self):
        super(ConfigurationError, self).__init__(
            "There is an error in the configuration, please check your configuration file")
