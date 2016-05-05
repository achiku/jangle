# -*- coding: utf-8 -*-
import click

from . import __version__


class JungleCLI(click.MultiCommand):

    """Jangle CLI main class"""

    def list_commands(self, ctx):
        """return available modules"""
        return ['ec2', 'elb', 'emr', 'asg']

    def get_command(self, ctx, name):
        """get command"""
        try:
            mod = __import__('jungle.' + name, None, None, ['cli'])
            return mod.cli
        except ImportError:
            pass


cli = JungleCLI(help="aws operation cli (v{0})".format(__version__))


if __name__ == '__main__':
    cli()
