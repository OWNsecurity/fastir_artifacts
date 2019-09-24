import os

import pytest
from artifacts.artifact import ArtifactDefinition
from artifacts.definitions import TYPE_INDICATOR_FILE

from fastir.common.filesystem import FileSystemManager, OSFileSystem, TSKFileSystem


FS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'filesystem'))


def fp(relative_path):
    """Create a full path from a relative path"""
    return os.path.join(FS_ROOT, relative_path)


def resolved_paths(outputs):
    paths = []

    for call in outputs.add_collected_file.call_args_list:
        paths.append(call[0][1].path)

    return paths


def file_artifact(name, pattern):
    artifact = ArtifactDefinition(name)
    artifact.AppendSource(TYPE_INDICATOR_FILE, {'paths': [pattern]})

    return artifact


def test_get_path(fake_partitions):
    manager = FileSystemManager()

    assert isinstance(manager.get_path_object('/passwords.txt').filesystem, TSKFileSystem)
    assert isinstance(manager.get_path_object(fp('root.txt')).filesystem, OSFileSystem)


def test_add_artifacts(fake_partitions, outputs, test_variables):
    manager = FileSystemManager()

    artifact = file_artifact('TestArtifact', '/passwords.txt')
    manager.register_source(artifact, artifact.sources[0], test_variables)

    artifact = file_artifact('TestArtifact2', fp('root.txt'))
    manager.register_source(artifact, artifact.sources[0], test_variables)

    manager.collect(outputs)

    assert set(resolved_paths(outputs)) == set(['/passwords.txt', fp('root.txt')])


def test_artifact_all_mountpoinrs(fake_partitions, outputs, test_variables):
    manager = FileSystemManager()

    artifact = file_artifact('TestArtifact', '\\passwords.txt')
    manager.register_source(artifact, artifact.sources[0], test_variables)

    manager.collect(outputs)

    assert resolved_paths(outputs) == ['/passwords.txt']


def test_no_mountpoin(fake_partitions):
    manager = FileSystemManager()

    with pytest.raises(IndexError):
        manager.get_path_object('im_not_a_mountpoint/file.txt')
