import StringIO
import socket
from paramiko.client import SSHClient
from paramiko.client import AutoAddPolicy
from paramiko.sftp_client import SFTPClient
import os
import time
from athena.utils.config import Config
from cluster import get_dns
import subprocess
from os.path import join as path_join


def open_ssh_session(slave=False):
    config = Config.load_default()
    ssh_key = config.ssh.key_path
    dns = get_dns(slave)
    username = config.ssh.username
    cmd = "ssh -i {} {}@{} -oStrictHostKeyChecking=no".format(ssh_key, username, dns)
    subprocess.call(cmd, shell=True)


class MasterNodeSSHClient():
    def __init__(self, host, username=None, ssh_key=None):
        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        self.ssh_client.connect(host, username=username, key_filename=os.path.expanduser(ssh_key))
        self.ssh_client.get_transport().set_keepalive(30)

    def _send_command_and_wait(self, cmd):
        ssh = self.ssh_client

        chan = ssh.get_transport().open_session()

        try:
            # Execute the given command
            chan.exec_command(cmd)

            # To capture Data. Need to read the entire buffer to caputure output

            contents = StringIO.StringIO()
            error = StringIO.StringIO()

            while not chan.exit_status_ready():

                if chan.recv_ready():
                    data = chan.recv(1024)
                    # print "Indside stdout"
                    while data:
                        contents.write(data)
                        data = chan.recv(1024)

                if chan.recv_stderr_ready():

                    error_buff = chan.recv_stderr(1024)
                    while error_buff:
                        error.write(error_buff)
                        error_buff = chan.recv_stderr(1024)

            exit_status = chan.recv_exit_status()

        except socket.timeout:
            raise socket.timeout

        out = contents.getvalue()
        err = error.getvalue()

        return out, err, exit_status

    def test(self):
        output = self._send_command_and_wait('echo "ssh connection successful"')
        self.print_output(output)

    def copy(self, src, dst):
        scp = SFTPClient.from_transport(self.ssh_client.get_transport())
        scp.put(src, dst)

    def create_tmp_dir(self, prefix=''):
        scp = SFTPClient.from_transport(self.ssh_client.get_transport())
        dirpath = path_join('/tmp', prefix + str(int(time.time() * 1000)))
        scp.mkdir(dirpath)
        return dirpath

    def dist_copy(self, src, dest):
        cmd = 'sudo -u hdfs hadoop distcp {} {}'.format(src, dest)
        return self._send_command_and_wait(cmd)

    def run_pig_script(self, pig_script, support_scripts=[]):
        tmp_dir = self.create_tmp_dir('pig_scripts')

        def copy_script(full_path):
            filename = os.path.basename(full_path)
            dest = path_join(tmp_dir, filename)
            self.copy(full_path, dest)

        copy_script(pig_script)
        for script in support_scripts:
            copy_script(script)
        cmd = 'cd {} && pig {}'.format(tmp_dir, os.path.basename(pig_script))
        return self._send_command_and_wait(cmd)

    def run_impala_script(self, impala_script):
        filename = os.path.basename(impala_script)
        dest = path_join(self.create_tmp_dir('impala_scripts'), filename)
        self.copy(impala_script, dest)
        cmd = 'impala-shell -i {} -f {}'.format(get_dns(slave=True), dest)
        return self._send_command_and_wait(cmd)

    def fix_hdfs_permissions(self, hdfs_dir):
        return self._send_command_and_wait('sudo -u hdfs hdfs dfs -chmod -R 777 {}'.format(hdfs_dir))

    @staticmethod
    def print_output(output_tuple):
        for line in output_tuple[0].split('\n'):
            print line
        for line in output_tuple[1].split('\n'):
            print line

    def close(self):
        self.ssh_client.close()
