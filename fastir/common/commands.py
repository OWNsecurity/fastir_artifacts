from subprocess import check_output, STDOUT, CalledProcessError

import artifacts

from fastir.common.logging import logger
from fastir.common.collector import AbstractCollector


class CommandExecutor(AbstractCollector):
    def __init__(self):
        self._commands = []

    def add_command(self, artifact, cmd, args):
        self._commands.append({
            'artifact': artifact,
            'cmd': cmd,
            'args': args
        })

    def collect(self, output):
        for command in self._commands:
            full_command = [command['cmd']] + command['args']
            full_command_str = ' '.join(full_command)

            try:
                command_output = check_output(full_command, stderr=STDOUT)
            except CalledProcessError as e:
                logger.warning(f"Command '{full_command_str}' for artifact '{command['artifact']}' returned error code '{e.returncode}'")
                command_output = e.output
            except FileNotFoundError:
                logger.warning(f"Command '{command['cmd']}' for artifact '{command['artifact']}' could not be found")
                command_output = b''

            output.add_collected_command(command['artifact'], full_command_str, command_output)

    def register_source(self, artifact_definition, artifact_source, variables):
        if artifact_source.type_indicator == artifacts.definitions.TYPE_INDICATOR_COMMAND:
            self.add_command(artifact_definition.name, artifact_source.cmd, artifact_source.args)
            return True

        return False
