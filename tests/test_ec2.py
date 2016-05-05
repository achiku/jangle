# -*- coding: utf-8 -*-
import pytest

from jungle import cli


def _get_sorted_server_names_from_output(output, separator='\t'):
    """return server name list from output"""
    server_names = [
        row.split(separator)[0]
        for row in output.rstrip().split('\n') if row != ''
    ]
    return sorted(server_names)


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


@pytest.mark.parametrize('inst_name, use_inst_id, username, keyfile, keydir, port, use_gateway, expected', [
    ('ssh_server', False, 'ubuntu', 'key.pem', "", 22, False, 'ssh ubuntu@{} -i key.pem -p 22'),
    (None, True, 'ubuntu', 'key.pem', "", 22, False, 'ssh ubuntu@{} -i key.pem -p 22'),
    ('ssh_server', False, 'ubuntu', 'key.pem', "", 22, True, 'ssh -tt ubuntu@{} -i key.pem -p 22 ssh ubuntu@{}'),
    (None, True, 'ubuntu', 'key.pem', "", 22, True, 'ssh -tt ubuntu@{} -i key.pem -p 22 ssh ubuntu@{}'),
])
def test_create_ssh_command(mocker, ec2, inst_name, use_inst_id, username,
                            keyfile, keydir, port, use_gateway, expected):
    """create_ssh_command test"""
    from jungle.ec2 import create_ssh_command
    mocker.patch('click.prompt', new=lambda msg, type, default: 0)
    ssh_server_instance_id = ec2['ssh_target_server'].id if use_inst_id else None
    gateway_server_instance_id = ec2['gateway_target_server'].id if use_gateway else None
    ssh_command = create_ssh_command(
        ssh_server_instance_id, inst_name, username, keyfile, keydir, port, gateway_server_instance_id)
    if use_gateway:
        expected_output = expected.format(
            ec2['gateway_target_server'].public_ip_address,
            ec2['ssh_target_server'].private_ip_address)
    else:
        expected_output = expected.format(ec2['ssh_target_server'].public_ip_address)
    assert ssh_command == expected_output
