Athena [![Stories in Ready](https://badge.waffle.io/datadudes/athena.png?label=ready&title=Ready)](https://waffle.io/datadudes/athena) [![Build Status](https://travis-ci.org/datadudes/athena.svg?branch=master)](https://travis-ci.org/datadudes/athena)
======
[![Live examples](terminal.gif)](https://asciinema.org/a/15439)

Athena is a convenient command line tool that enables you to interact with and query a Hadoop cluster from your local terminal, 
removing the need for remote SSH sessions. Athena makes the life of every data scientist and engineer a lot easier by 
providing comprehensive querying features and easy automation of daily tasks, from the convenience of your local command line!

**Features**

- Query Impala and show the results in your terminal or save the results to a CSV file
- Run a batch of queries (as defined in a YAML file) on Impala, saving the results to the specified CSV file(s)
- Define a report with one or more queries and mail it to one or more people. Reports are rendered in a neutral and good looking template.
- Schedule reports using the built-in scheduler. Send reports on specific dates or intervals, to any number of people.
- Ship a Pig script and related libraries/UDFs to your Hadoop cluster and run it there.
- Start an SSH session to a node on your cluster, or even create a tunnel without having to remember hostnames/ip addresses.
- Start a distributed copy job by just providing a source and destination. Works with HDFS and S3.
- Works with static hostnames/IPs or dynamic hostnames for clusters on Amazon Web Services.

All of this works from the local terminal on your laptop/client machine. The only thing Athena needs is either an open 
port to Impala (for most features) and/or SSH access.

The bulk of Athena's functionality so far was built with Impala in mind, but expect interaction with other parts of your 
Hadoop cluster to come in the near future!

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

## Configuration

Configuration is done with one simple YAML file. For most use cases, quite little configuration is needed. You can create
a new configuration by using:
```bash
$ athena init
```
and answering the configuration questions.

The master node is accessed by all functionality requiring SSH access, such as `athena copy`, `athena pig`. The slave 
nodes are accessed when running queries, making reports, and anything else that involves Impala. Athena assumes the 
Impala daemon is running on your slave nodes and will randomly choose a node from the list of slave nodes for running a 
query.

#### Advanced configuration

To get the most out of Athena, you can make use of the more advanced configuration options.

If you have not created a configuration automatically by using `athena init`, you can manually configure Athena by 
executing the following steps:

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

Use the following reference to find all the possible configuration options with their default values. As you can see, 
only the `cluster > master` and `cluster > slaves` need to be provided, as they don't have defaults.

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

A note on when to use **the _aws_ cluster type**: in most cases the IP addresses and/or hostnames of the master and 
slave nodes are static and known beforehand. If, however, your Hadoop cluster is running on Amazon Web Services, and it 
is regularly spun-up and torn-down (to save costs, for instance), it becomes cumbersome to have to change the configuration 
all the time. One way to fix it, is to buy some _elastic ip addresses_ from Amazon and attach them to the nodes each 
time when spinning up a cluster. Athena provides another way however. If you choose cluster type 'aws', you can provide 
the _Names_ of your master and slave nodes. This should be the value that is in the _Name_ tag of each of your EC2 
machines. See AWS documentation for [more details](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html).
Athena will then use the AWS API to find the hostnames of your cluster nodes.

## Usage guide

**Query Impala and show the results in the terminal**

```bash
$ athena query "SELECT * FROM sample_07 LIMIT 10"
```

**Query Impala and save the results to a CSV file**

```bash
$ athena query "SELECT * FROM sample_07" --csv sample.csv
```

Athena uses [Impyla](https://github.com/cloudera/impyla) under the hood for querying Impala. Because Impyla supports
retrieving the results in chunks, memory will not be an issue here. Even for large resultsets, creating the CSV is no
problem. The results will just be written to disk in parts.

The same goes for the `athena batch` command (see below).

**Run a batch of queries defined in a YAML file and save the results to one or more CSV files**

```bash
$ athena batch my_queries.yml
```

The YAML file can be anywhere on your system, as long as you provide the right path. The YAML file you provide, should 
have the following format:

```yaml
- query: <SQL query>                        # e.g. SELECT * FROM foo WHERE bla < 10
  output: <path of the CSV file to create>  # e.g. myresults0.csv
- query: <SQL query>
  output: <path of the CSV file to create>
...
```

You can also use the built-in variable substitution to run similar queries without having to copy and paste:

```yaml
- query: SELECT * FROM foo WHERE bar = '{{ item }} rocks!'
  with_items:
  - "Spark"
  - "Impala"
  - "Hadoop"
  output: {{ item }}.csv
```

**Ship a Pig script to the cluster, optionally with UDFs, and run it**

```bash
$ athena pig calculate_avg_salary.pig my_udfs.py
```
Athena creates an SSH connection to the master node for shipping the script(s) to the cluster. In order for this to work,
you should provide an SSH _username_ in your configuration. You can optionally provide a path to an SSH key in the configuration
as well, if there are no valid keys in your default SSH directory.
The output from running the Pig script is returned in your terminal. Any files the Pig script creates on the local file
system of your master node, are not copied over to your local machine.

**Create and send a report by email**

One powerful feature of Athena is the ability to create and send reports with query results. For this to work, you need 
to configure an SMTP service in the Athena configuration. Using a service like [SendGrid](https://sendgrid.com/) is 
recommended, but you can also use a local SMTP server.

Reports are defined using YAML files with a simple syntax:

```yaml
title: Cloudera Quickstart VM report
description: A report on all those glorious samples
recipients: john@mycompany.com mary.ceo@mycompany.com
data:
  inline:
    - name: Sample 07
      description: Salaries one way
      type: sql
      query: SELECT * FROM sample_07 LIMIT 10
    - name: Sample 08
      description: Salaries the other way
      type: sql
      query: SELECT * FROM sample_08 LIMIT 10
  csv:
    - filename: sample07.csv
      type: sql
      query: SELECT * FROM sample_07 LIMIT 10
    - filename: sample08.csv
      type: sql
      query: SELECT * FROM sample_08 LIMIT 10 
```

- **title** defines the title at the top of the mail
- **description** sets the description that appears below the title in the mail
- **recipients** is a comma-separated list of email addresses that the report should be delivered to 
- **data** contains the query blocks that define the data that will be in the report. Athena supports two types:
  - _inline_ blocks appear as tables in the email
  - _csv_ blocks will be added as attachments to the email

Both _inline_ and _csv_ blocks also allow variable substitution like with the `athena batch` command (see above).
  
Report definitions go as YAML files into a special directory inside the Athena configuration directory: 
`<athena-config-dir>/reports/`. For instance, on OS X and Linux this will be: `~/.athena/reports/`

You can see a list of available reports with:

```bash
$ athena report list
```

You can send a report with:

```bash
$ athena report my_report.yml
```

The extension is optional. You can override the recipients by providing email addresses after the report name. You can 
also redirect the resulting _html_ to the stdout, by using the `--stdout` switch.

The above report will look [like this](http://htmlpreview.github.io/?https://github.com/datadudes/athena/blob/master/example_report.html)

You can also schedule reports to be sent at specific dates/times. See below for more information.

**SSH to a cluster node**

Athena adds a way to conveniently start an SSH session to the master or a slave node. SSH needs to be configured for this.

```bash
$ athena ssh
```

By default this creates an SSH session to the master node. Provide `--slave` to create an SSH session to a slave node instead.

**Create SSH tunnel to cluster node**

Athena allows you to create a tunnel from a local port to a port on the master or a slave node. This is especially
convenient if the Impala port isn't reachable directly from your local machine. SSH needs to be configured for this.

```bash
$ athena tunnel <local_port> <remote_port>
```

By default this creates an SSH tunnel to a port on the master node. Provide `--slave` to create an SSH tunnel to the 
provided port on a slave node instead.

**Distributed copy**

Athena can copy files from and to HDFS and S3 using the Hadoop _DistCp_ utility. SSH needs to be configured for this to 
work.

```bash
$ athena copy <src_file(s)> <destination>
```

For more information, see the [DistCp manual](http://hadoop.apache.org/docs/r1.2.1/distcp.html).

## Scheduling

One way that can make the Athena reporting facilities really powerful, is by automating the sending of reports using the 
built-in _Scheduler_. By adding a `schedule` section to your report definitions, you can decide when a report should be 
mailed. Athena scheduling is best used on a server that is on 24.7. Athena uses [Celery](http://www.celeryproject.org/) 
for its scheduling feature.

To make use of the scheduler, you have to have Celery installed. This happens automatically when you install Athena with 
`pip install athena[scheduler]`. Furthermore you must provide the `celery_broker_url`, `celery_result_backend` and 
`celery_timezone` in your Athena configuration. When you use Redis as a broker for Celery, your _broker url_ and _result 
backend_ will look like: `redis://localhost:6379/1`. For more information on the choice of brokers and the configuration, 
have a look at the [Celery documentation](http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html)

To enable the Scheduler, use the following commands:

- start worker(s): `celery -A athena.scheduling.scheduler worker --loglevel=INFO`
- start scheduler: `celery beat -A athena.scheduling.scheduler --loglevel=INFO`

Add the following to a report that you want to be sent at certain dates/times:

```yaml
schedule:
  minute: 15
  hour: 9
  day_of_week: 1
  day_of_month: 10-17
  month_of_year: 1, 2, 3
```

Just like with crontabs, you can use a `*` for a interval, to mean "any". If no value is specified, `*` is assumed. In 
the example, the report will be sent on 9:15 AM, on a monday between the 10th and the 17th of the month, but only in January, 
February or March.

For more information on possible values for the `schedule`, see the [Celery documentation](http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html#crontab-schedules)

## Future plans

We have a lot more in store for Athena! Athena has only recently been released to the public, and while we use it in our 
daily jobs with great success, it is far from complete, and probably has bugs. 

To have a look at what's currently in our minds for Athena, have a look at the [GitHub issues](https://github.com/datadudes/athena/issues). 
We are using [Waffle.io](https://waffle.io/datadudes/athena) to make working with GitHub issues easier, and it also 
gives you insight on what exactly we are working on _right now!_

To list a couple of things that are in the pipeline:

- Automatic interactive configuration initialization
- Building and submitting Spark Jobs
- Custom report templates
- ... **Let us know what you want!**

## Contributing

You're more than welcome to create issues for any bugs you find and ideas you have. Contributions in the form of pull 
requests are also very much appreciated!

## Authors

Athena was created with passion by:

- [Daan Debie](https://github.com/DandyDev) - [Website](http://dandydev.net/)
- [Marcel Krcah](https://github.com/mkrcah) - [Website](http://marcelkrcah.net/)

## Acknowledgements

Athena would not have been possible without the awesome work of [Uri Laserson](https://github.com/laserson) on 
[Impyla](https://github.com/cloudera/impyla), the Impala library for Python.