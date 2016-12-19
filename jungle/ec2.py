# -*- coding: utf-8 -*-
import subprocess
import sys

import botocore
import click
from jungle.session import create_session

reload(sys)
sys.setdefaultencoding("utf-8")

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


def get_tag_value(x, key):
    """Get a value from tag"""
    if x is None:
        return ''
    result = [y['Value'] for y in x if y['Key'] == key]
    if result:
        return result[0]
    return ''


@click.group()
@click.option('--profile-name', '-P', default=None, help='AWS profile name')
@click.pass_context
def cli(ctx, profile_name):
    """EC2 CLI group"""
    ctx.obj = {'AWS_PROFILE_NAME': profile_name}


@cli.command(help='List EC2 instances')
@click.argument('name', default='*')
@click.option('--list-formatted', '-l', is_flag=True)
@click.pass_context
def ls(ctx, name, list_formatted):
    """List EC2 instances"""
    session = create_session(ctx.obj['AWS_PROFILE_NAME'])
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
@click.pass_context
def up(ctx, instance_id):
    """Start EC2 instance"""
    session = create_session(ctx.obj['AWS_PROFILE_NAME'])
    ec2 = session.resource('ec2')
    try:
        instance = ec2.Instance(instance_id)
        instance.start()
    except botocore.exceptions.ClientError as e:
        click.echo("Invalid instance ID {0} ({1})".format(instance_id, e), err=True)
        sys.exit(2)


@cli.command(help='Stop EC2 instance')
@click.option('--instance-id', '-i', required=True, help='EC2 instance id')
@click.pass_context
def down(ctx, instance_id):
    """Stop EC2 instance"""
    session = create_session(ctx.obj['AWS_PROFILE_NAME'])
    ec2 = session.resource('ec2')
    try:
        instance = ec2.Instance(instance_id)
        instance.stop()
    except botocore.exceptions.ClientError as e:
        click.echo("Invalid instance ID {0} ({1})".format(instance_id, e), err=True)
        sys.exit(2)


def create_ssh_command(session, instance_id, instance_name, username, key_file, port, ssh_options,
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
    elif instance_name is not None:
        try:
            conditions = [
                {'Name': 'tag:Name', 'Values': [instance_name]},
                {'Name': 'instance-state-name', 'Values': ['running']},
            ]
            instances = ec2.instances.filter(Filters=conditions)
            target_instances = []
            for idx, i in enumerate(instances):
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
            gateway_username_option, gateway_public_ip, key_file_option,
            port, ssh_options, username_option, hostname)
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
@click.option('--username', '-u', default=None, help='Login username')
@click.option('--key-file', '-k', help='SSH Key file path', type=click.Path())
@click.option('--port', '-p', help='SSH port', default=22)
@click.option('--private-ip', '-e', help='Use instance private ip', is_flag=True, default=False)
@click.option('--ssh-options', '-s', help='Additional SSH options', default=None)
@click.option('--gateway-instance-id', '-g', default=None, help='Gateway instance id')
@click.option('--gateway-username', '-x', default=None, help='Gateway username')
@click.option('--dry-run', is_flag=True, default=False, help='Print SSH Login command and exist')
@click.pass_context
def ssh(ctx, instance_id, instance_name, username, key_file, port, ssh_options, private_ip,
        gateway_instance_id, gateway_username, dry_run):
    """SSH to EC2 instance"""
    session = create_session(ctx.obj['AWS_PROFILE_NAME'])

    if instance_id is None and instance_name is None:
        click.echo(
            "One of --instance-id/-i or --instance-name/-n"
            " has to be specified.", err=True)
        sys.exit(1)
    elif instance_id is not None and instance_name is not None:
        click.echo(
            "Both --instance-id/-i and --instance-name/-n "
            "can't to be specified at the same time.", err=True)
        sys.exit(1)
    cmd = create_ssh_command(
        session, instance_id, instance_name, username, key_file, port, ssh_options, private_ip,
        gateway_instance_id, gateway_username)
    if not dry_run:
        subprocess.call(cmd, shell=True)
    else:
        click.echo(cmd)
