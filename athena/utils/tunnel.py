import select
import SocketServer
import sys

from athena.utils.cluster import get_dns
from athena.utils.ssh import MasterNodeSSHClient


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip',
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
        except Exception as e:
            print('Incoming request to {}:{} failed: {}'.format(self.chain_host,
                                                                self.chain_port,
                                                                repr(e)))
            return
        if chan is None:
            print('Incoming request to {}:{} was rejected by the SSH server.'.format(self.chain_host, self.chain_port))
            return

        print('Connected!  Tunnel open {} -> {} -> {}'.format(self.request.getpeername(),
                                                              chan.getpeername(), (self.chain_host, self.chain_port)))
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        peername = self.request.getpeername()
        chan.close()
        self.request.close()
        print('Tunnel closed from %r' % (peername,))


def forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object.  (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHander(Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport

    ForwardServer(('', local_port), SubHander).serve_forever()


def create_tunnel(local_port, remote_port, slave=False):
    client = None

    remote_host = get_dns(slave=slave)

    print('Connecting to ssh host {}:{} ...'.format(remote_host, remote_port))
    try:
        client = MasterNodeSSHClient(get_dns()).ssh_client
    except Exception as e:
        print e
        print('*** Failed to connect to {}:{}: {}'.format(remote_host, remote_port, e))
        sys.exit(1)

    print('Now forwarding port {} to {}:{} ...'.format(local_port, remote_host, remote_port))

    try:
        forward_tunnel(local_port, remote_host, remote_port, client.get_transport())
    except KeyboardInterrupt:
        print('C-c: Port forwarding stopped.')
        sys.exit(0)
