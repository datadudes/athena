from __future__ import print_function
import random
from athena.utils.config import AthenaConfig
from IPy import IP


def get_ips_or_hostnames(ip_list):
    ip_hostname_list = []
    for item in ip_list:
        try:
            ips = IP(item)
            ip_hostname_list.extend([str(i) for i in ips])
        except ValueError:
            ip_hostname_list.append(item)
    return ip_hostname_list


def get_dns(slave=False):
    config = AthenaConfig.load_default()

    if config.cluster.infra_type == 'standard':
        if slave:
            node = random.choice(get_ips_or_hostnames(config.cluster.slave_nodes))
        else:
            node = config.cluster.master_node
    else:
        # only possible type currently, next to 'standard', is 'aws'
        import boto.ec2
        if slave:
            name = random.choice(config.cluster.slave_nodes)
        else:
            name = config.cluster.master_node

        conn = boto.ec2.connect_to_region(
            config.aws.region,
            aws_access_key_id=config.aws.access_key_id,
            aws_secret_access_key=config.aws.secret_access_key
        )
        instances = get_instances_by_tags(name, conn=conn)

        def error(msg):
            import sys
            print("ERROR:", msg, file=sys.stderr)
            return None

        # Assumes there is only 1 node with that name
        if len(instances) == 1:
            node = instances[0].public_dns_name
        elif len(instances) == 0:
            error("No clusters to connect to")
            node = None
        else:
            error("Too many clusters to connect to")
            node = None
    return node


def get_instances_by_tags(tags, conn=None):
    if not conn:
        import boto.ec2
        config = AthenaConfig.load_default()
        conn = boto.ec2.connect_to_region(
            config.aws.region,
            aws_access_key_id=config.aws.access_key_id,
            aws_secret_access_key=config.aws.secret_access_key
        )

    instances = conn.get_only_instances(filters={'instance-state-code': 16, 'tag:Name': tags})

    return instances


def get_running_instances():
    import boto.ec2
    config = AthenaConfig.load_default()
    conn = boto.ec2.connect_to_region(
        config.aws.region,
        aws_access_key_id=config.aws.access_key_id,
        aws_secret_access_key=config.aws.secret_access_key
    )

    instances = conn.get_only_instances(
        filters={'instance-state-code': [0, 16, 64, 80]})
    return instances
