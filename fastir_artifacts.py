import os
import sys
import locale

import artifacts.reader
import artifacts.definitions
import configargparse

from fastir.common.output import Outputs
from fastir.common.collector import Collector
from fastir.common.logging import logger, PROGRESS
from fastir.common.helpers import get_operating_system


# Using a static blacklist to avoid automatic execution of steps
# that could have a big impact on performance.
BLACKLIST = [
    'WMILoginUsers',
    'WMIUsers',
    'WMIVolumeShadowCopies'
]

REGISTRY_TYPES = [
    artifacts.definitions.TYPE_INDICATOR_WINDOWS_REGISTRY_KEY,
    artifacts.definitions.TYPE_INDICATOR_WINDOWS_REGISTRY_VALUE
]


def get_artifacts_registry(use_library, paths):
    reader = artifacts.reader.YamlArtifactsReader()
    registry = artifacts.registry.ArtifactDefinitionsRegistry()

    if not paths or use_library:
        path = os.path.join(sys.prefix, 'share', 'artifacts')
        registry.ReadFromDirectory(reader, path)

    if paths:
        for path in paths:
            registry.ReadFromDirectory(reader, path)

    return registry


def resolve_artifact_groups(registry, artifact_names):
    if artifact_names:
        artifact_names = artifact_names.split(',')
        resolved_names = set()

        for artifact in artifact_names:
            definition = registry.GetDefinitionByName(artifact)

            if definition:
                resolved_names.add(artifact)
                for source in definition.sources:
                    if source.type_indicator == artifacts.definitions.TYPE_INDICATOR_ARTIFACT_GROUP:
                        artifact_names += source.names

        return resolved_names


def get_artifacts_to_collect(registry, include, exclude, platform, collect_registry):
    for artifact_definition in registry.GetDefinitions():
        # Apply BLACKLIST, except if the artifact is explicitely requested
        if artifact_definition.name in BLACKLIST:
            if not include or artifact_definition.name not in include:
                continue

        # If a specific list of Artifacts was specified, ignore everything else
        if include and artifact_definition.name not in include:
            continue

        # Apply exclusion list
        if exclude and artifact_definition.name in exclude:
            continue

        # We only care about artefacts available for current platform
        if artifact_definition.supported_os and platform not in artifact_definition.supported_os:
            continue

        for artifact_source in artifact_definition.sources:
            if artifact_source.supported_os and platform not in artifact_source.supported_os:
                continue

            # Exclude registry artifacts when using the default setup
            # Full hives are already collected
            if not collect_registry and artifact_source.type_indicator in REGISTRY_TYPES:
                continue

            yield artifact_definition, artifact_source


def main(arguments):
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        pass
    output = Outputs(arguments.output, arguments.maxsize, arguments.sha256)

    logger.log(PROGRESS, "Loading artifacts ...")

    platform = get_operating_system()
    collector = Collector(platform)

    artifacts_registry = get_artifacts_registry(arguments.library, arguments.directory)

    include_artifacts = resolve_artifact_groups(artifacts_registry, arguments.include)
    exclude_artifacts = resolve_artifact_groups(artifacts_registry, arguments.exclude)

    for artifact_definition, artifact_source in get_artifacts_to_collect(
        artifacts_registry, include_artifacts, exclude_artifacts, platform,
        arguments.include or (arguments.directory and not arguments.library)
    ):
        collector.register_source(artifact_definition, artifact_source)

    collector.collect(output)


if __name__ == "__main__":
    parser = configargparse.ArgumentParser(
        default_config_files=[os.path.join((os.path.dirname(__file__), os.path.dirname(sys.executable))[hasattr(sys, 'frozen')], 'fastir_artifacts.ini')],
        description='FastIR Artifacts - Collect ForensicArtifacts')

    parser.add_argument('-i', '--include', help='Artifacts to collect (comma-separated)')
    parser.add_argument('-e', '--exclude', help='Artifacts to ignore (comma-separated)')
    parser.add_argument('-d', '--directory', help='Directory containing Artifacts definitions', nargs='+')
    parser.add_argument(
        '-l', '--library',
        help='Keep loading Artifacts definitions from the ForensicArtifacts library (in addition to custom directories)',
        action='store_true')
    parser.add_argument('-m', '--maxsize', help='Do not collect file with size > n')
    parser.add_argument('-o', '--output', help='Directory where the results are created', default='.')
    parser.add_argument('-s', '--sha256', help='Compute SHA-256 of collected files', action='store_true')

    main(parser.parse_args())
