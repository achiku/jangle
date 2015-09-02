# -*- coding: utf-8 -*-
import subprocess
import sys

import boto3
import botocore
import click


def get_tag_value(x, key):
    """Get a value from tag"""
    if x is not None:
        result = [y['Value'] for y in x if y['Key'] == key]
        if len(result) == 0:
            return None
        return result[0]


@click.group()
def cli():
    """EC2 CLI group"""
    pass


@cli.command(help='List EC2 instances')
@click.argument('name', default='*')
def ls(name):
    """List EC2 instances"""
    ec2 = boto3.resource('ec2')
    if name == '*':
        instances = ec2.instances.filter()
    else:
        instances = ec2.instances.filter(
            Filters=[{'Name': 'tag:Name', 'Values': [name]}])
    for i in instances:
        tag_name = get_tag_value(i.tags, 'Name')
        click.echo('{}\t{}\t{}\t{}\t{}'.format(
            tag_name, i.state['Name'], i.id, i.private_ip_address, i.public_ip_address))


@cli.command(help='Start EC2 instance')
@click.option('--instance-id', '-i', 'instance_id',
              required=True, help='EC2 instance id')
def up(instance_id):
    """Start EC2 instance"""
    client = boto3.client('ec2')
    client.start_instances(InstanceIds=[instance_id])


@cli.command(help='Stop EC2 instance')
@click.option('--instance-id', '-i', 'instance_id',
              required=True, help='EC2 instance id')
def down(instance_id):
    """Stop EC2 instance"""
    client = boto3.client('ec2')
    client.stop_instances(InstanceIds=[instance_id])


@cli.command(help='SSH to EC2 instance')
@click.option('--instance-id', '-i', 'instance_id',
              default=None, help='EC2 instance id')
@click.option('--instance-name', '-n', 'instance_name',
              default=None, help='EC2 instance Name Tag')
@click.option('--username', '-u', 'username',
              default='ubuntu', help='Login username')
@click.option('--key-file', '-k', 'keyfile_path',
              required=True, help='SSH Key file path', type=click.Path())
@click.option('--port', '-p', 'port', help='SSH port', default=22)
def ssh(instance_id, instance_name, username, keyfile_path, port):
    """SSH to EC2 instance"""
    if instance_id is None and instance_name is None:
        click.echo("One of --instance-id/-i or --instance-name/-n has to be specified.", err=True)
        sys.exit(2)
    elif instance_id is not None and instance_name is not None:
        click.echo("Both --instance-id/-i and --instance-name/-n "
                   "can't to be specified at the same time.", err=True)
        sys.exit(2)

    ec2 = boto3.resource('ec2')
    if instance_id is not None:
        try:
            instance = ec2.Instance(instance_id)
            hostname = instance.public_ip_address
        except botocore.exceptions.ClientError as e:
            click.echo("Invalid instance ID {} ({})".format(instance_id, e), err=True)
            sys.exit(2)
    elif instance_name is not None:
        try:
            instances = ec2.instances.filter(
                Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}])

            list_instances = []
            for idx, i in enumerate(instances):
                list_instances.append(i)
                tag_name = get_tag_value(i.tags, 'Name')
                click.echo('[{}]: {}\t{}\t{}\t{}'.format(
                    idx, i.id, i.private_ip_address, i.state['Name'], tag_name))
            selected_idx = click.prompt("Please enter a valid number", type=int, default=0)
            click.echo("{} is selected.".format(selected_idx))
            hostname = list_instances[selected_idx].public_ip_address
        except botocore.exceptions.ClientError as e:
            click.echo("Invalid instance ID {} ({})".format(instance_id, e), err=True)
            sys.exit(2)

    cmd = 'ssh {}@{} -i {} -p {}'.format(username, hostname, keyfile_path, port)
    subprocess.call(cmd, shell=True)
