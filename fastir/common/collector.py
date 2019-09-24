import artifacts

from fastir.common.logging import logger, PROGRESS


class AbstractCollector:
    def collect(self, output):
        raise NotImplementedError

    def register_source(self, artifact_definition, artifact_source, variables):
        raise NotImplementedError


class Collector:
    def __init__(self, platform):
        self._platform = platform
        self._variables = None
        self._sources = 0

        from fastir.common.commands import CommandExecutor
        from fastir.common.filesystem import FileSystemManager
        self._collectors = [FileSystemManager(), CommandExecutor()]

        if platform == 'Windows':
            from fastir.windows.variables import WindowsHostVariables
            self._variables = WindowsHostVariables()

            from fastir.windows.wmi import WMIExecutor
            from fastir.windows.registry import RegistryCollector
            self._collectors.append(WMIExecutor())
            self._collectors.append(RegistryCollector())
        else:
            from fastir.unix.variables import UnixHostVariables
            self._variables = UnixHostVariables()

    def register_source(self, artifact_definition, artifact_source):
        supported = False

        for collector in self._collectors:
            if collector.register_source(artifact_definition, artifact_source, self._variables):
                supported = True

        if supported:
            self._sources += 1
        elif artifact_source.type_indicator != artifacts.definitions.TYPE_INDICATOR_ARTIFACT_GROUP:
            logger.warning(f"Cannot process source for '{artifact_definition.name}' because type '{artifact_source.type_indicator}' is not supported")

    def collect(self, output):
        logger.log(PROGRESS, f"Collecting artifacts from {self._sources} sources ...")

        for collector in self._collectors:
            collector.collect(output)

        logger.log(PROGRESS, "Finished collecting artifacts")
        output.close()
