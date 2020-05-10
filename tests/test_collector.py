import pytest
from artifacts.artifact import ArtifactDefinition
from artifacts.definitions import TYPE_INDICATOR_COMMAND, TYPE_INDICATOR_FILE, TYPE_INDICATOR_PATH

from fastir.common.collector import Collector
from fastir.common.filesystem import FILE_INFO_TYPE
from fastir.common.helpers import get_operating_system


@pytest.fixture
def command_echo():
    artifact = ArtifactDefinition('EchoCommand')
    artifact.AppendSource(TYPE_INDICATOR_COMMAND, {'cmd': 'echo', 'args': ['test']})

    return artifact


@pytest.fixture
def passwords_file():
    artifact = ArtifactDefinition('PasswordsFile')
    artifact.AppendSource(TYPE_INDICATOR_FILE, {'paths': ['/passwords.txt']})

    return artifact


@pytest.fixture
def passwords_file_info():
    artifact = ArtifactDefinition('PasswordsFileInfo')
    artifact.AppendSource(FILE_INFO_TYPE, {'paths': ['/passwords.txt']})

    return artifact


@pytest.fixture
def path_artifact():
    artifact = ArtifactDefinition('PathArtifact')
    artifact.AppendSource(TYPE_INDICATOR_PATH, {'paths': ['/passwords.txt']})

    return artifact


def test_collector(command_echo, passwords_file, passwords_file_info, outputs, fake_partitions):
    collector = Collector(get_operating_system())

    collector.register_source(command_echo, command_echo.sources[0])
    collector.register_source(passwords_file, passwords_file.sources[0])
    collector.register_source(passwords_file_info, passwords_file_info.sources[0])
    collector.collect(outputs)

    assert outputs.add_collected_file.call_count == 1
    assert outputs.add_collected_command.call_count == 1
    assert outputs.add_collected_file_info.call_count == 1


def test_unsupported_source(path_artifact, caplog):
    collector = Collector(get_operating_system())

    collector.register_source(path_artifact, path_artifact.sources[0])

    log = caplog.records[0]
    assert log.levelname == "WARNING"
    assert log.message == "Cannot process source for 'PathArtifact' because type 'PATH' is not supported"
