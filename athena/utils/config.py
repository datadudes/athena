from __future__ import absolute_import
from __future__ import with_statement

import errno
from os import remove, removedirs
from os.path import isfile, join as path_join, exists
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

    def file_exists(self, filename):
        fn = path_join(self.path, filename)
        return exists(fn) and isfile(fn)

    def config_exists(self):
        return self.file_exists('config.yml')

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


class Config(object):

    DEFAULT_CONFIG = {
        'cluster': {
            'type': 'standard',
            'impala_port': 21050
        },
        'ssh': {
            'username': None,
            'key_path': None
        },
        'mailing': {
            'smtp_host': 'localhost',
            'smtp_port': 587,
            'smtp_username': None,
            'smtp_password': None,
            'smtp_use_tls': True,
            'from_address': 'data@example.com',
            'default_template': 'datamail.html'
        },
        'slack': {
            'token': None,
            'default_channel': None,
            'default_username': 'athena',
            'default_icon': None
        }
    }

    def __init__(self, config_dict):
        """
        From a dictionary with arbitrary nesting, recursively creates a class hierarchy allowing dot-notation access to
        attributes with any depth.
        """
        for k, v in config_dict.iteritems():
            if isinstance(v, (list, tuple)):
                setattr(self, k, [Config(x) if isinstance(x, dict) else x for x in v])
            else:
                setattr(self, k, Config(v) if isinstance(v, dict) else v)

    def __getattribute__(self, name):
        val = object.__getattribute__(self, name)
        if isinstance(val, basestring):
            return val.strip()
        elif isinstance(val, (list, tuple)):
            return [x.strip() for x in val]
        else:
            return val

    @staticmethod
    def load(config_file):
        values = yaml.safe_load(config_file)
        config_dict = Config._merge(dict(Config.DEFAULT_CONFIG), values)
        return Config(config_dict)

    @staticmethod
    def _merge(a, b, path=None):
        """
        Recursively merges dicts A and B so that any key/value in dict B on a certain path, will overwrite that same
        key/value in dict A if it exists. Config uses _merge to combine a user config with the default config,
        overriding the latter values with the former.
        """
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    Config._merge(a[key], b[key], path + [str(key)])
                else:
                    a[key] = b[key]
            else:
                a[key] = b[key]
        return a

    @staticmethod
    def load_default():
        config_file = ConfigDir().open_athena_config()
        config_obj = Config.load(config_file)
        config_file.close()
        return config_obj


class ConfigurationError(Exception):
    def __init__(self):
        super(ConfigurationError, self).__init__(
            "There is an error in the configuration, please check your configuration file")
