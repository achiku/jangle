# jungle

[![PyPI version](https://img.shields.io/pypi/v/jungle.svg)](https://pypi.python.org/pypi/jungle)
[![PyPI downloads](https://img.shields.io/pypi/dm/jungle.svg)](https://pypi.python.org/pypi/jungle)
[![Build Status](https://travis-ci.org/achiku/jungle.svg)](https://travis-ci.org/achiku/jungle)
[![Requirements Status](https://requires.io/github/achiku/jungle/requirements.svg?branch=master)](https://requires.io/github/achiku/jungle/requirements/?branch=master)
[![codecov.io](http://codecov.io/github/achiku/jungle/coverage.svg?branch=master)](http://codecov.io/github/achiku/jungle?branch=master)
[![Code Issues](https://www.quantifiedcode.com/api/v1/project/deacbd1de84b474d97493cb5fbae967e/badge.svg)](https://www.quantifiedcode.com/app/project/deacbd1de84b474d97493cb5fbae967e)


## Description

jungle makes AWS operations from terminal simpler and more intuitive.


## Why created

awscli is by far the most comprehensive CLI tool manipulating various AWS services, and I really like its flexible options and up-to-date release cycle. However, day-to-day AWS operations from my terminal don't need that much flexibility and that many services. Rather, I wanted just small set of UNIX-like commands which are easy to use and remember.

## Installation

```
pip install jungle
```

## Usage


### EC2

Listing all EC2 instances (each attribute is separated by a tab)

```
jungle ec2 ls
```

Listing all EC2 instances in formatted output(each attribute is separated with space and is aligned)

```
jungle ec2 ls -l
```

Filtering EC2 instances by Name tag

```
jungle ec2 ls blog-web-server-01
```

Filtering EC2 instances by Name tag using wildcard

```
jungle ec2 ls '*web*'
```

Starting instance

```
jungle ec2 up -i i-xxxxxx
```

Stopping instance

```
jungle ec2 down -i i-xxxxxx
```

SSH login to instance specified by instance id

```
jungle ec2 ssh -i i-xxxxxx --key-file /path/to/key.pem --port 1234
```

SSH login to instance specified by Tag Name

```
jungle ec2 ssh -n blog-web-server-01 --key-file /path/to/key.pem
```

SSH login to instance specified by Tag Name with wildcard (you'll be prompted to choose which server to log in)

```
jungle ec2 ssh -n 'blog-web-server-*' --key-file /path/to/key.pem
```

SSH login to instance specified by Tag Name through gateway instance

```
jungle ec2 ssh -n blog-web-server-01 --key-file /path/to/key.pem -g i-xxxxxx
```

SSH login to instance specified by Tag Name using auto ssh key discovery

```
jungle ec2 ssh -n blog-web-server-01
```

#### Auto ssh key discovery

If you don't specify a key-file with -k or --key-file, jungle will read the
key file name off of the instance and then attempt to find a local key with
the same name in `~/.ssh/``

Example:
ec2 instance reports a key name of FooBar, jungle will look for a key name of
`~/.ssh/FooBar.pem`

The search path for keys defaults to `~/.ssh/` but can be overridden with
`--key-dir'


### ELB

Listing all ELB instances

```
jungle elb ls
```

Listing a ELB instance

```
jungle elb ls production-blog-elb
```

Listing ELB attached EC2 instances

```
jungle elb ls -l production-blog-elb
```


### EMR

```
jungle emr ls
```

```
jungle emr ssh -k /path/to/key.pem -i j-xxxxxxx
```


## Configuration

You can create the credential file yourself. By default, its location is at ```~/.aws/credentials```

```
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```


You may also want to set a default region. This can be done in the configuration file. By default, its location is at ```~/.aws/config```

```
[default]
region = us-east-1
```

More detailed configurations can be found in the boto3 documentation.

[Boto3 Doc - Configuration](http://boto3.readthedocs.org/en/latest/guide/configuration.html#guide-configuration)
