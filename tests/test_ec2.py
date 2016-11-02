# -*- coding: utf-8 -*-
import boto3
import pytest
from jungle import cli
from jungle.session import create_session


def _normalize_tabs(string):
    lines = string.split("\n")
    retval = ""
    for line in lines:
        words = line.split()
        for idx, word in enumerate(words):
            if word == '' or word == ' ':
                del words[idx]
        retval = retval + " ".join(words) + "\n"
    return retval


def _get_tag_value(x, key):
    """Get a value from tag"""
    if x is None:
        return ''
    result = [y['Value'] for y in x if y['Key'] == key]
    if result:
        return result[0]
    return ''


def _get_sorted_server_names_from_output(output, separator='\t'):
    """return server name list from output"""
    server_names = [
        row.split(separator)[0]
        for row in output.rstrip().split('\n') if row != ''
    ]
    return sorted(server_names)


def test_parse_tags():
    from jungle.ec2 import _parse_tags

    tag_list = 'Name:ec2instance ,role:webserver, cluster:webserver-cluster'
    expected_tags = {'Name': 'ec2instance',
                     'role': 'webserver',
                     'cluster': 'webserver-cluster'}
    tags = _parse_tags(tag_list)

    assert tags == expected_tags


def test_get_instance_ip_address(runner, ec2):
    from jungle.ec2 import _get_instance_ip_address

    public_server = ec2['server']
    ip = _get_instance_ip_address(public_server)
    assert ip == public_server.public_ip_address

    ip = _get_instance_ip_address(public_server, use_private_ip=True)
    assert ip == public_server.private_ip_address

    vpc = ec2['ec2'].create_vpc(CidrBlock='10.0.0.0/24')
    subnet = vpc.create_subnet(CidrBlock='10.0.0.0/25')
    vpc_server = ec2['ec2'].create_instances(ImageId='ami-xxxxx', MinCount=1, MaxCount=1, SubnetId=subnet.id)[0]

    ip = _get_instance_ip_address(vpc_server)
    assert ip == vpc_server.private_ip_address


def test_ec2_up(runner, ec2):
    """jungle ec2 up test"""
    result = runner.invoke(cli.cli, ['ec2', 'up', '-i', ec2['server'].id])
    assert result.exit_code == 0


def test_ec2_up_no_instance(runner, ec2):
    """jungle ec2 up test"""
    result = runner.invoke(cli.cli, ['ec2', 'up', '-i', 'dummy'])
    assert result.exit_code == 2


def test_ec2_down(runner, ec2):
    """jungle ec2 up test"""
    result = runner.invoke(cli.cli, ['ec2', 'down', '-i', ec2['server'].id])
    assert result.exit_code == 0


def test_ec2_down_no_instance(runner, ec2):
    """jungle ec2 up test"""
    result = runner.invoke(cli.cli, ['ec2', 'down', '-i', 'dummy'])
    assert result.exit_code == 2


@pytest.mark.parametrize('arg, expected_server_names', [
    ('*',  ['', 'server00', 'server01', 'gateway_server', 'ssh_server']),
    ('server01', ['server01']),
    ('fake-server', []),
])
def test_ec2_ls(runner, ec2, arg, expected_server_names):
    """jungle ec2 ls test"""
    result = runner.invoke(cli.cli, ['ec2', 'ls', arg])
    assert result.exit_code == 0
    assert sorted(expected_server_names) == _get_sorted_server_names_from_output(result.output)


@pytest.mark.parametrize('opt, arg, expected_server_names', [
    ('-l', '*',  ['', 'server00', 'server01', 'gateway_server', 'ssh_server']),
    ('-l', 'server01', ['server01']),
    ('-l', 'fake-server', []),
])
def test_ec2_ls_formatted(runner, ec2, opt, arg, expected_server_names):
    """jungle ec2 ls test"""
    result = runner.invoke(cli.cli, ['ec2', 'ls', opt, arg])
    assert result.exit_code == 0
    assert sorted(expected_server_names) == _get_sorted_server_names_from_output(result.output, separator=' ')


@pytest.mark.parametrize('args, expected_output, exit_code', [
    (
        ['-u', 'ubuntu'],
        "One of --instance-id/-i or --instance-name/-n or --instance-tags/-t"
        " has to be specified.\n", 1),
    (
        ['-i', 'xxx', '-n', 'xxx'],
        "Only one of --instance-id/-i or --instance-name/-n or --instance-tags/-t "
        "can be specified at the same time.\n", 1),
    (
        ['-i', 'xxx', '-t', 'xxx'],
        "Only one of --instance-id/-i or --instance-name/-n or --instance-tags/-t "
        "can be specified at the same time.\n", 1),
    (
        ['-n', 'xxx', '-t', 'xxx'],
        "Only one of --instance-id/-i or --instance-name/-n or --instance-tags/-t "
        "can be specified at the same time.\n", 1)
])
def test_ec2_ssh_arg_error(runner, ec2, args, expected_output, exit_code):
    """jungle ec2 ssh test"""
    command = ['ec2', 'ssh', '--dry-run']
    command.extend(args)
    result = runner.invoke(cli.cli, command)
    assert result.output == expected_output
    assert result.exit_code == exit_code


@pytest.mark.parametrize('args, input, expected_output, exit_code', [
    (['-n', 'server*'], "3", "selected number [3] is invalid\n", 2),
])
def test_ec2_ssh_selection_index_error(runner, ec2, args, input, expected_output, exit_code):
    """jungle ec2 ssh test"""
    command = ['ec2', 'ssh', '--dry-run']
    command.extend(args)
    result = runner.invoke(cli.cli, command, input=input)
    assert expected_output in result.output
    assert result.exit_code == exit_code


@pytest.mark.parametrize('args, expected_output, exit_code', [
    (['-u', 'ubuntu'], "ssh -l ubuntu {ip} -p 22\n", 0),
    (['-u', 'ec2user', '-p', '8022'], "ssh -l ec2user {ip} -p 8022\n", 0),
])
def test_ec2_ssh(runner, ec2, args, expected_output, exit_code):
    """jungle ec2 ssh test"""
    command = ['ec2', 'ssh', '--dry-run']
    command.extend(args)
    command.extend(['-i', ec2['ssh_target_server'].id])
    result = runner.invoke(cli.cli, command)
    assert result.output == expected_output.format(ip=ec2['ssh_target_server'].public_ip_address)
    assert result.exit_code == exit_code


@pytest.mark.parametrize('args, expected_output, exit_code', [
    (['-u', 'ubuntu', '-n', 'server01'], "ssh -l ubuntu {ip} -p 22\n", 0),
])
def test_ec2_ssh_multiple_tag_search(runner, ec2, args, expected_output, exit_code):
    """jungle ec2 ssh multiple nodes"""
    command = ['ec2', 'ssh', '--dry-run']
    command.extend(args)
    result = runner.invoke(cli.cli, command)

    conditions = [
        {'Name': 'tag:Name', 'Values': [args[-1]]},
        {'Name': 'instance-state-name', 'Values': ['running']},
    ]
    instance = list(ec2['ec2'].instances.filter(Filters=conditions).all())[0]
    assert result.output == expected_output.format(ip=instance.public_ip_address)
    assert result.exit_code == exit_code


@pytest.mark.parametrize('args, expected_output, exit_code', [
    (['-u', 'ubuntu', '-n', 'server*'], 'expected_output', 0),
])
def test_ec2_ssh_multiple_choice(runner, ec2, args, expected_output, exit_code):
    """jungle ec2 ssh multiple nodes"""
    command = ['ec2', 'ssh', '--dry-run']
    command.extend(args)
    result = runner.invoke(cli.cli, command)

    conditions = [
        {'Name': 'tag:Name', 'Values': [args[-1]]},
        {'Name': 'instance-state-name', 'Values': ['running']},
    ]
    instances = ec2['ec2'].instances.filter(Filters=conditions)
    instances_list = list(instances.all())

    menu = ""
    for idx, i in enumerate(instances):
        tag_name = _get_tag_value(i.tags, 'Name')
        menu = menu + "[{0}]: {1}\t{2}\t{3}\t{4}\t{5}\n".format(
            idx, i.id, i.public_ip_address, i.state['Name'], tag_name, i.key_name)
    menu = menu + "Please enter a valid number [0]:\n"

    # The tests seem to hit return by default
    menu = menu + "0 is selected.\n"

    # Add the ssh cmd
    menu = menu + "ssh -l {user} {ip} -p 22\n".format(user=args[1], ip=instances_list[0].public_ip_address)
    menu = menu.expandtabs()

    assert _normalize_tabs(result.output) == _normalize_tabs(menu)
    assert result.exit_code == exit_code


@pytest.mark.parametrize('args, instance_id, expected_output, exit_code', [
    (['-u', 'ubuntu'], 'i-mal',
     ("Invalid instance ID {instance_id} (An error occurred "
      "(InvalidInstanceID.NotFound) when calling the DescribeInstances operation: "
      "The instance ID '{instance_id}' does not exist)\n"), 2),
])
def test_ec2_ssh_unknown_id(runner, ec2, args, instance_id, expected_output, exit_code):
    """jungle ec2 ssh test"""
    command = ['ec2', 'ssh', '--dry-run']
    command.extend(args)
    command.extend(['-i', instance_id])
    result = runner.invoke(cli.cli, command)
    assert result.output == expected_output.format(instance_id=instance_id)
    assert result.exit_code == exit_code


@pytest.mark.parametrize('tags, key, expected', [
    ([{'Key': 'Name', 'Value': 'server01'}, {'Key': 'env', 'Value': 'prod'}], 'Name', 'server01'),
    ([{'Key': 'Name', 'Value': 'server01'}, {'Key': 'env', 'Value': 'prod'}], 'env', 'prod'),
    ([{'Key': 'Name', 'Value': 'server01'}, {'Key': 'env', 'Value': 'prod'}], 'dummy', ''),
    ([], 'dummy', ''),
    (None, 'dummy', ''),
])
def test_get_tag_value(tags, key, expected):
    """get_tag_value utility test"""
    from jungle.ec2 import get_tag_value
    assert get_tag_value(tags, key) == expected


@pytest.mark.parametrize('instance_tags, use_inst_id, username, keyfile, port, ssh_options, use_private_ip, '
                         'use_gateway, gateway_username, profile_name, expected', [
                             ({'Name': 'ssh_server'}, False, 'ubuntu', 'key.pem', 22, "-o StrictHostKeyChecking=no",
                              False, False, None, None,
                              'ssh -l ubuntu {} -i key.pem -p 22 -o StrictHostKeyChecking=no'),
                             ({'Name': 'ssh_server'}, False, 'ubuntu', None, 22, None, False, False, None, None,
                              'ssh -l ubuntu {} -p 22'),
                             ({'Name': 'ssh_server'}, False, 'ubuntu', None, 22, None, True, False, None, None,
                              'ssh -l ubuntu {} -p 22'),
                             (None, True, 'ubuntu', 'key.pem', 22, None, False, False, None, None,
                              'ssh -l ubuntu {} -i key.pem -p 22'),
                             ({'Name': 'ssh_server'}, False, 'ubuntu', 'key.pem', 22, None, False, True, None, None,
                              'ssh -tt {} -i key.pem -p 22 ssh -l ubuntu {}'),
                             ({'Name': 'ssh_server'}, False, 'ubuntu', None, 22, None, False, True, None, None,
                              'ssh -tt {} -p 22 ssh -l ubuntu {}'),
                             (None, True, 'ubuntu', 'key.pem', 22, None, False, True, None, None,
                              'ssh -tt {} -i key.pem -p 22 ssh -l ubuntu {}'),
                             (None, True, 'ubuntu', None, 22, "-A", False, True, 'ec2-user', None,
                              'ssh -tt -l ec2-user {} -p 22 -A ssh -l ubuntu {}'),
                             (None, True, 'ec2-user', None, 22, "-A", False, True, 'core', 'my_profile',
                              'ssh -tt -l core {} -p 22 -A ssh -l ec2-user {}'),
                         ])
def test_create_ssh_command(
        mocker, ec2, instance_tags, use_inst_id, username, keyfile, port, ssh_options, use_private_ip,
        use_gateway, gateway_username, profile_name, expected):
    """create_ssh_command test"""
    from jungle.ec2 import create_ssh_command
    mocker.patch('boto3.Session', new=lambda profile_name: boto3)
    mocker.patch('click.prompt', new=lambda msg, type, default: 0)
    ssh_server_instance_id = ec2[
        'ssh_target_server'].id if use_inst_id else None
    gateway_server_instance_id = ec2[
        'gateway_target_server'].id if use_gateway else None
    ssh_command = create_ssh_command(
        create_session(profile_name),
        ssh_server_instance_id, instance_tags, username, keyfile, port, ssh_options, use_private_ip,
        gateway_server_instance_id, gateway_username)
    if use_gateway:
        expected_output = expected.format(
            ec2['gateway_target_server'].public_ip_address,
            ec2['ssh_target_server'].private_ip_address)
    elif use_private_ip:
        expected_output = expected.format(
            ec2['ssh_target_server'].private_ip_address)
    else:
        expected_output = expected.format(
            ec2['ssh_target_server'].public_ip_address)
    assert ssh_command == expected_output
