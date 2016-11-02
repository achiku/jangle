# -*- coding: utf-8 -*-
import subprocess
import sys

import botocore
import click
from jungle.session import create_session


def format_output(instances, flag):
    """return formatted string for instance"""
    out = []
    line_format = '{0}\t{1}\t{2}\t{3}\t{4}'
    name_len = _get_max_name_len(instances) + 3
    if flag:
        line_format = '{0:<' + str(name_len) + '}{1:<16}{2:<21}{3:<16}{4:<16}'

    for i in instances:
        tag_name = get_tag_value(i.tags, 'Name')
        out.append(line_format.format(
            tag_name, i.state['Name'], i.id, i.private_ip_address, str(i.public_ip_address)))
    return out


def _get_instance_ip_address(instance, use_private_ip=False):
    if use_private_ip:
        return instance.private_ip_address
    elif instance.public_ip_address is not None:
        return instance.public_ip_address
    else:
        click.echo("Public IP address not set. Attempting to use the private IP address.")
        return instance.private_ip_address


def _get_max_name_len(instances):
    """get max length of Tag:Name"""
    # FIXME: ec2.instanceCollection doesn't have __len__
    for i in instances:
        return max([len(get_tag_value(i.tags, 'Name')) for i in instances])
    return 0


def _parse_tags(tags):
    tags_dict = {}
    tags_list = tags.split(',')
    for tag in tags_list:
        tag_key, tag_value = tag.strip().split(':')
        tags_dict[tag_key] = tag_value

    return tags_dict


def get_tag_value(x, key):
    """Get a value from tag"""
    if x is None:
        return ''
    result = [y['Value'] for y in x if y['Key'] == key]
    if result:
        return result[0]
    return ''


@click.group()
def cli():
    """EC2 CLI group"""
    pass


@cli.command(help='List EC2 instances')
@click.argument('name', default='*')
@click.option('--list-formatted', '-l', is_flag=True)
@click.option('--profile-name', '-P')
def ls(name, list_formatted, profile_name):
    """List EC2 instances"""
    session = create_session(profile_name)
    ec2 = session.resource('ec2')
    if name == '*':
        instances = ec2.instances.filter()
    else:
        condition = {'Name': 'tag:Name', 'Values': [name]}
        instances = ec2.instances.filter(Filters=[condition])
    out = format_output(instances, list_formatted)
    click.echo('\n'.join(out))


@cli.command(help='Start EC2 instance')
@click.option('--instance-id', '-i', required=True, help='EC2 instance id')
@click.option('--profile-name', '-P')
def up(instance_id, profile_name):
    """Start EC2 instance"""
    session = create_session(profile_name)
    ec2 = session.resource('ec2')
    try:
        instance = ec2.Instance(instance_id)
        instance.start()
    except botocore.exceptions.ClientError as e:
        click.echo("Invalid instance ID {0} ({1})".format(instance_id, e), err=True)
        sys.exit(2)


@cli.command(help='Stop EC2 instance')
@click.option('--instance-id', '-i', required=True, help='EC2 instance id')
@click.option('--profile-name', '-P')
def down(instance_id, profile_name):
    """Stop EC2 instance"""
    session = create_session(profile_name)
    ec2 = session.resource('ec2')
    try:
        instance = ec2.Instance(instance_id)
        instance.stop()
    except botocore.exceptions.ClientError as e:
        click.echo("Invalid instance ID {0} ({1})".format(instance_id, e), err=True)
        sys.exit(2)


def create_ssh_command(session, instance_id, instance_tags, username, key_file, port, ssh_options,
                       use_private_ip, gateway_instance_id, gateway_username):
    """Create SSH Login command string"""
    ec2 = session.resource('ec2')
    if instance_id is not None:
        try:
            instance = ec2.Instance(instance_id)
            hostname = _get_instance_ip_address(instance, use_private_ip)
        except botocore.exceptions.ClientError as e:
            click.echo("Invalid instance ID {0} ({1})".format(instance_id, e), err=True)
            sys.exit(2)
    elif instance_tags is not None:
        try:
            conditions = [
                {'Name': 'instance-state-name', 'Values': ['running']},
            ]
            for key, value in instance_tags.items():
                conditions.append({'Name': 'tag:{0}'.format(key), 'Values': [value]})
            instances = ec2.instances.filter(Filters=conditions)
            target_instances = []
            for idx, i in enumerate(sorted(instances, key=lambda instance: get_tag_value(instance.tags, 'Name'))):
                target_instances.append(i)
            if len(target_instances) == 1:
                instance = target_instances[0]
                hostname = _get_instance_ip_address(instance, use_private_ip)
            else:
                for idx, i in enumerate(instances):
                    tag_name = get_tag_value(i.tags, 'Name')
                    click.echo('[{0}]: {1}\t{2}\t{3}\t{4}\t{5}'.format(
                        idx, i.id, i.public_ip_address, i.state['Name'], tag_name, i.key_name))
                selected_idx = click.prompt("Please enter a valid number", type=int, default=0)
                if len(target_instances) - 1 < selected_idx or selected_idx < 0:
                    click.echo("selected number [{0}] is invalid".format(selected_idx), err=True)
                    sys.exit(2)
                click.echo("{0} is selected.".format(selected_idx))
                instance = target_instances[selected_idx]
                hostname = _get_instance_ip_address(instance, use_private_ip)
        except botocore.exceptions.ClientError as e:
            click.echo("Invalid instance ID {0} ({1})".format(instance_id, e), err=True)
            sys.exit(2)

    # TODO: need to refactor and make it testable
    if key_file is None:
        key_file_option = ''
    else:
        key_file_option = ' -i {0}'.format(key_file)

    gateway_username_option = build_option_username(gateway_username)
    username_option = build_option_username(username)

    if ssh_options is None:
        ssh_options = ''
    else:
        ssh_options = ' {0}'.format(ssh_options)
    if gateway_instance_id is not None:
        gateway_instance = ec2.Instance(gateway_instance_id)
        gateway_public_ip = gateway_instance.public_ip_address
        hostname = instance.private_ip_address
        cmd = 'ssh -tt{0} {1}{2} -p {3}{4} ssh{5} {6}'.format(
            gateway_username_option, gateway_public_ip, key_file_option, port, ssh_options, username_option, hostname)
    else:
        cmd = 'ssh{0} {1}{2} -p {3}{4}'.format(username_option, hostname, key_file_option, port, ssh_options)
    return cmd


def build_option_username(username):
    if username is None:
        return ''
    else:
        return ' -l {0}'.format(username)


@cli.command(help='SSH login to EC2 instance')
@click.option('--instance-id', '-i', default=None, help='EC2 instance id')
@click.option('--instance-name', '-n', default=None, help='EC2 instance Name Tag')
@click.option('--instance-tags', '-t', default=None,
              help='EC2 instance Tags\nFormat: \n\n tag_name:tag_value[,tag_name:tag_value...]')
@click.option('--username', '-u', default=None, help='Login username')
@click.option('--key-file', '-k', help='SSH Key file path', type=click.Path())
@click.option('--port', '-p', help='SSH port', default=22)
@click.option('--private-ip', '-e', help='Use instance private ip', is_flag=True, default=False)
@click.option('--ssh-options', '-s', help='Additional SSH options', default=None)
@click.option('--gateway-instance-id', '-g', default=None, help='Gateway instance id')
@click.option('--gateway-username', '-x', default=None, help='Gateway username')
@click.option('--dry-run', is_flag=True, default=False, help='Print SSH Login command and exist')
@click.option('--profile-name', '-P')
def ssh(instance_id, instance_name, instance_tags, username, key_file, port, ssh_options, private_ip,
        gateway_instance_id, gateway_username, dry_run, profile_name):
    """SSH to EC2 instance"""
    session = create_session(profile_name)
    filters = (instance_id, instance_name, instance_tags).count(None)
    if filters == 3:
        click.echo(
            "One of --instance-id/-i or --instance-name/-n or --instance-tags/-t"
            " has to be specified.", err=True)
        sys.exit(1)
    elif filters < 2:
        click.echo(
            "Only one of --instance-id/-i or --instance-name/-n or --instance-tags/-t "
            "can be specified at the same time.", err=True)
        sys.exit(1)
    if instance_name is not None:
        instance_tags_dict = {'Name': instance_name}
    elif instance_tags is not None:
        instance_tags_dict = _parse_tags(instance_tags)
    else:
        instance_tags_dict = None
    cmd = create_ssh_command(
        session,
        instance_id, instance_tags_dict, username, key_file, port, ssh_options, private_ip,
        gateway_instance_id, gateway_username)
    if not dry_run:
        subprocess.call(cmd, shell=True)
    else:
        click.echo(cmd)
