from __future__ import print_function
import random
import boto.ec2
from athena.utils.config import AthenaConfig


def get_dns(slave=False):
    config = AthenaConfig.load_default()
    slaves = config.cluster.slave_nodes

    if slave:
        name = random.choice(slaves)
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

    # assuming one job flow per cluster
    if len(instances) == 1:
        return instances[0].public_dns_name
    elif len(instances) == 0:
        error("No clusters to connect to")
    else:
        error("Too many clusters to connect to")


def get_instances_by_tags(tags, conn=None):
    if not conn:
        config = AthenaConfig.load_default()
        conn = boto.ec2.connect_to_region(
            config.aws.region,
            aws_access_key_id=config.aws.access_key_id,
            aws_secret_access_key=config.aws.secret_access_key
        )

    instances = conn.get_only_instances(filters={'instance-state-code': 16, 'tag:Name': tags})

    return instances


def get_running_instances():
    config = AthenaConfig.load_default()
    conn = boto.ec2.connect_to_region(
        config.aws.region,
        aws_access_key_id=config.aws.access_key_id,
        aws_secret_access_key=config.aws.secret_access_key
    )

    instances = conn.get_only_instances(
        filters={'instance-state-code': [0, 16, 64, 80]})
    return instances
