[![Stories in Ready](https://badge.waffle.io/datadudes/athena.png?label=ready&title=Ready)](https://waffle.io/datadudes/athena)
Athena
======
Athena is a convenient command line tool that enables you to interact with and query a Hadoop cluster from your local terminal, removing the need for remote SSH sessions. Athena makes the life of every data scientist and engineer a lot easier by providing comprehensive querying features and easy automation of daily tasks, from the convenience of your local command line!

The bulk of Athena's functionality so far was built with Impala in mind, but expect interaction with other parts of your Hadoop cluster to come in the near future!

**Features**

- Query Impala and show the results in your terminal or save the results to a CSV file
- Run a batch of queries (as defined in a YAML file) on Impala, saving the results to the specified CSV file(s)
- Define a report with one or more queries and mail it to one or more people. Reports are rendered in a neutral and good looking template.
- Schedule reports using the built-in scheduler. Send reports on specific dates or intervals, to any number of people.
- Ship a Pig script and related libraries/UDFs to your Hadoop cluster and run it there.
- Start an SSH session to a node on your cluster, or even create a tunnel without having to remember hostnames/ip addresses.
- Start a distributed copy job by just providing a source and destination. Works with HDFS and S3.
- Works with static hostnames/IPs or dynamic hostnames for clusters on Amazon Web Services.

All of this works from the local terminal on your laptop/client machine. The only thing Athena needs is either an open port to Impala (for most features) and/or SSH access.

## Installation & Requirements

Athena works with Python 2.6 or 2.7 installed. It takes care of the dependencies so you don't have to! All you have to do is:

```bash
# basic installation
$ pip install athena

# or when you want to use the scheduler
$ pip install athena[scheduler]

# or you need dynamic hostname discovery on AWS
$ pip install athena[aws]

# or both
$ pip install athena[scheduler,aws]
```

## Examples

<script type="text/javascript" src="https://asciinema.org/a/15439.js" id="asciicast-15439" async data-autoplay="true" data-loop="true"></script>

**Query Impala and show the results in the terminal**

```bash
$ athena query "SELECT * FROM sample_07 LIMIT 10"
```

**Query Impala and save the results to a CSV file**

```bash
$ athena query "SELECT * FROM sample_07" --csv sample.csv
```

**Run a batch of queries defined in a YAML file and save the results to one or more CSV files**

```bash
$ athena batch my_queries.yml
```

**Ship a Pig script to the cluster together with some UDFs and run it**

_(SSH must be configured for this to work)_

```bash
$ athena pig calculate_avg_salary.pig my_udfs.py
```

For a detailed usage guide, see below.

## Configuration

Configuration is done with one simple YAML file. For most use cases, quite little configuration is needed. Execute the following steps to configure Athena:

1. Create a `.athena` directory in your home directory. 
	- On OS X, this should be: `/Users/myusername/.athena`
	- On most Linux distros, this should be: `/home/myusername/.athena`
2. In the `.athena` directory, create a file `config.yml`
3. Enter the following in your `config.yml`:

```yaml
cluster:
  master: <hostname or ip of your master node> # usually the node running the NameNode service, YARN ResourceManager etc.
  slaves: <comma separated list of hostnames/ips of your slave nodes> # all the other nodes (data nodes)
```

The master node is accessed by all functionality requiring SSH access, such as `athena copy`, `athena pig`. The slave nodes are accessed when running queries, making reports, and anything else that involved Impala. Athena assumes the Impala daemon is running on your slave nodes and will randomly choose a node from the list of slave nodes for running a query.

#### Complete configuration example

Below is a documented example of all the configuration options with their default values. As you can see, only the `cluster > master` and `cluster > slaves` need to be provided, as they don't have defaults.

```yaml
cluster:                            # Basic cluster information
  type: standard                    # Type of cluster. Can be 'standard' or 'aws'. Use 'aws' when you run a Hadoop cluster on AWS EC2 and want Athena to find out the hostname of master and slaves through the AWS API, using the 'Name' tags of your machines. 
  master: NO DEFAULT                # IP or Hostname of the Master node. When cluster type is 'aws', this should be the 'Name' (tag) of your master node.
  slaves: NO DEFAULT                # Comma separated list of IP addresses and/or Hostnames (can be mixed) of the Slave nodes. When cluster type is 'aws', this should be the 'Name's (tags) of your slave nodes.
  impala_port: 21050                # port on which Impala can be accessed
mailing:
  smtp_host: localhost              # SMTP server for sending mail. Used for the reporting functionality
  smtp_port: 587
  smtp_username: <empty>
  smtp_password: <empty>
  smtp_use_tls: true
  from_address: data@example.com    # email address that is used as the "from:" address when sending reports
ssh:
  username: <empty>                 # username that should be used when creating an SSH session or tunnel
  key_path: <empty>                 # path to private key for creating an SSH session or tunnel
aws:                                # Amazon Web Services credentials for using the API. Only relevant with cluster type 'aws'
  access_key_id: <empty>
  secret_access_key: <empty>
  region: <empty>
scheduling:							# Athena uses Celery for scheduling. See Celery documentation for details
  celery_broker_url: <empty>
  celery_result_backend: <empty>
  celery_timezone: Europe/Amsterdam
```

A note on when to use **the _aws_ cluster type**: in most cases the IP addresses and/or hostnames of the master and slave nodes are static and known beforehand. If, however, your Hadoop cluster is running on Amazon Web Services, and it regularly spun-up and torn-down (to save costs, for instance), it becomes cumbersome to have to change the configuration all the time. One way to fix it, is to buy some _elastic ip addresses_ from Amazon and attach them to the nodes each time when spinning up a cluster. Athena provides another way however. If you choose cluster type 'aws', you can provide the _Names_ of your master and slave nodes. This should be the value that is in the _Name_ tag of each of your EC2 machines. See AWS documentation for [more details](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html).

## Usage guide

coming soon