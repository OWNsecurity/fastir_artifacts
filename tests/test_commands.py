from artifacts.artifact import ArtifactDefinition
from artifacts.definitions import TYPE_INDICATOR_COMMAND

from fastir.common.commands import CommandExecutor


def command_artifact(name, command, args):
    artifact = ArtifactDefinition(name)
    artifact.AppendSource(TYPE_INDICATOR_COMMAND, {'cmd': command, 'args': args})

    return artifact


def test_command_execution(outputs, test_variables):
    collector = CommandExecutor()
    artifact = command_artifact('TestArtifact', 'echo', ['test'])

    assert collector.register_source(artifact, artifact.sources[0], test_variables) is True

    collector.collect(outputs)
    outputs.add_collected_command.assert_called_with('TestArtifact', 'echo test', b'test\n')


def test_unknown_command(outputs, test_variables, caplog):
    collector = CommandExecutor()
    artifact = command_artifact('TestArtifact', 'idontexist', [])

    assert collector.register_source(artifact, artifact.sources[0], test_variables) is True

    collector.collect(outputs)
    outputs.add_collected_command.assert_called_with('TestArtifact', 'idontexist', b'')

    log = caplog.records[0]
    assert log.levelname == "WARNING"
    assert log.message == "Command 'idontexist' for artifact 'TestArtifact' could not be found"
