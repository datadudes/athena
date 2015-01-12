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

    def __init__(self, ssh=None, cluster=None, aws=None, mailing=None):
        self.ssh = ssh
        self.cluster = cluster
        self.aws = aws
        self.mailing = mailing

    @staticmethod
    def load(config_file):
        values = yaml.safe_load(config_file)
        impala_port = values['cluster']['impala_port'] if 'impala_port' in values['cluster'] else 21050
        cluster = ClusterConfig(
            values['cluster']['type'].strip(),
            values['cluster']['master'].strip(),
            [slave.strip() for slave in values['cluster']['slaves'].split(',')],
            impala_port
        )
        ssh = SSHConfig(
            values['ssh']['username'].strip(),
            values['ssh']['key_path'].strip())
        aws = AWSConfig(
            values['aws']['access_key_id'].strip(),
            values['aws']['secret_access_key'].strip(),
            values['aws']['region'].strip())
        mailing = MailingConfig(
            values['mailing']['sendgrid_username'].strip(),
            values['mailing']['sendgrid_password'].strip(),
            values['mailing']['from'].strip()
        )
        return AthenaConfig(ssh, cluster, aws, mailing)

    @staticmethod
    def load_default():
        config_file = ConfigDir().open_athena_config()
        config_obj = AthenaConfig.load(config_file)
        config_file.close()
        return config_obj


class ClusterConfig(object):

    def __init__(self, infra_type='aws', master_node='', slave_nodes=[], impala_port=21050):
        self.infra_type = infra_type
        self.master_node = master_node
        self.slave_nodes = slave_nodes
        self.impala_port = impala_port


class SSHConfig(object):

    def __init__(self, username='', key_path=''):
        self.username = username
        self.key_path = key_path


class AWSConfig(object):

    def __init__(self, access_key_id='', secret_access_key='', region=''):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region


class MailingConfig(object):

    def __init__(self, sendgrid_username='', sendgrid_password='', from_address=''):
        self.sendgrid_username = sendgrid_username
        self.sendgrid_password = sendgrid_password
        self.from_address = from_address
