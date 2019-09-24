# This file contains common fixtures
import os
from shutil import rmtree
from tempfile import mkdtemp
from unittest.mock import patch
from collections import namedtuple

import pytest

from fastir.common.output import Outputs
from fastir.common.variables import HostVariables


FS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'filesystem'))


@pytest.fixture
def temp_dir():
    dirpath = mkdtemp()

    yield dirpath

    rmtree(dirpath)


@pytest.fixture
def outputs(temp_dir):
    with patch.object(Outputs, 'add_collected_command'):
        with patch.object(Outputs, 'add_collected_file'):
            outputs = Outputs(temp_dir, maxsize=None, sha256=False)
            yield outputs
            outputs.close()


@pytest.fixture
def test_variables():
    class HostVariablesForTests(HostVariables):

        def init_variables(self):
            pass

    return HostVariablesForTests()


@pytest.fixture
def fake_partitions():
    Partition = namedtuple('Partition', ['mountpoint', 'device', 'fstype'])

    partitions = [
        Partition('/', os.path.join(os.path.dirname(__file__), 'data', 'image.raw'), 'NTFS'),
        Partition(FS_ROOT, FS_ROOT, 'some_unsupported_fstype')
    ]

    with patch('psutil.disk_partitions', return_value=partitions) as mock:
        yield mock
