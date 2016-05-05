# -*- coding: utf-8 -*-
import pytest

from jungle import cli


@pytest.mark.parametrize('asg_name', [
    ('*'),
    ('asg-*'),
    ('asg-2'),
    ('dummy-asg'),
])
def test_asg_ls(runner, asg, asg_name):
    """jungle asg ls test"""
    result = runner.invoke(cli.cli, ['asg', 'ls', asg_name])
    assert result.exit_code == 0
