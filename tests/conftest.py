# -*- coding: utf-8 -*-
import boto3
import pytest
from click.testing import CliRunner
from moto import mock_autoscaling, mock_ec2, mock_elb, mock_emr


@pytest.fixture
def runner():
    """Define test runner"""
    return CliRunner()


@pytest.yield_fixture(scope='function')
def asg():
    """AutoScaling mock service"""
    mock = mock_autoscaling()
    mock.start()

    client = boto3.client('autoscaling')
    groups = []
    lcs = []
    for i in range(3):
        lc_config = dict(
            LaunchConfigurationName='lc-{0}'.format(i),
            ImageId='ami-xxxxxx',
            KeyName='mykey',
            InstanceType='c3.xlarge',
        )
        client.create_launch_configuration(**lc_config)
        lcs.append(lc_config)
        asg_config = dict(
            AutoScalingGroupName='asg-{0}'.format(i),
            LaunchConfigurationName='lc-{0}'.format(i),
            MaxSize=10,
            MinSize=2,
        )
        client.create_auto_scaling_group(**asg_config)
        groups.append(asg_config)

    yield {'lcs': lcs, 'groups': groups}
    mock.stop()


@pytest.yield_fixture(scope='function')
def emr():
    """EMR mock service"""
    # TODO: implement fixture after moto is ready
    # https://github.com/spulec/moto/pull/456
    boto3.set_stream_logger()
    mock = mock_emr()
    mock.start()

    client = boto3.client('emr')
    clusters = []
    for i in range(2):
        cluster = client.run_job_flow(
            Name='cluster{}'.format(i),
            Instances={
                'MasterInstanceType': 'c3.xlarge',
                'SlaveInstanceType': 'c3.xlarge',
                'InstanceCount': 3,
                'Placement': {'AvailabilityZone': 'ap-northeast-1a'},
                'KeepJobFlowAliveWhenNoSteps': True,
            },
            VisibleToAllUsers=True,
        )
        clusters.append(cluster)
    yield {'clusters': clusters}
    mock.stop()


@pytest.yield_fixture(scope='function')
def elb():
    """ELB mock service"""
    mock = mock_elb()
    mock.start()

    client = boto3.client('elb')
    lbs = []
    for i in range(2):
        lb = client.create_load_balancer(
            LoadBalancerName='loadbalancer-01',
            Listeners=[
                {
                    'Protocol': 'http',
                    'LoadBalancerPort': 80,
                    'InstanceProtocol': 'http',
                    'InstancePort': 80,
                }
            ]
        )
        lbs.append(lb)
    yield {'lbs': lbs}
    mock.stop()


@pytest.yield_fixture(scope='function')
def ec2():
    """EC2 mock service"""
    mock = mock_ec2()
    mock.start()

    ec2 = boto3.resource('ec2')
    ssh_server = ec2.create_instances(ImageId='ami-xxxxx', MinCount=1, MaxCount=1)
    for s in ssh_server:
        ec2.create_tags(
            Resources=[s.id],
            Tags=[{'Key': 'Name', 'Value': 'ssh_server'}])

    gateway_server = ec2.create_instances(ImageId='ami-xxxxx', MinCount=1, MaxCount=1)
    for s in gateway_server:
        ec2.create_tags(
            Resources=[s.id],
            Tags=[{'Key': 'Name', 'Value': 'gateway_server'}])

    server = ec2.create_instances(ImageId='ami-xxxxx', MinCount=1, MaxCount=1)
    servers = ec2.create_instances(ImageId='ami-xxxxx', MinCount=2, MaxCount=2)
    for i, s in enumerate(servers):
        ec2.create_tags(
            Resources=[s.id],
            Tags=[{'Key': 'Name', 'Value': 'server{:0>2d}'.format(i)}])

    yield dict(
        ec2=ec2,
        servers=servers,
        server=server[0],
        ssh_target_server=ssh_server[0],
        gateway_target_server=gateway_server[0],
    )

    mock.stop()
