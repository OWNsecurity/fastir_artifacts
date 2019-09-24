import os

import pytest

from fastir.common.filesystem import TSKFileSystem


@pytest.fixture
def fs_test():
    return TSKFileSystem(
        None, os.path.join(os.path.dirname(__file__), 'data', 'image.raw'), '/')


def resolved_paths(outputs):
    paths = []

    for call in outputs.add_collected_file.call_args_list:
        paths.append(call[0][1].path.replace(os.path.sep, '/'))

    return paths


def test_all_files(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', '/**')
    fs_test.collect(outputs)

    # Deleted files and directories should not resolve
    assert set(resolved_paths(outputs)) == set([
        '/a_directory/another_file',
        '/a_directory/a_file',
        '/passwords.txt',
    ])


def test_is_symlink(fs_test):
    path_object = fs_test.get_fullpath('/passwords.txt')
    assert path_object.is_symlink() is False


def test_several_patterns(fs_test, outputs):
    # This test is meant to verify that the cache is functionnal
    fs_test.add_pattern('TestArtifact', '/**')
    fs_test.add_pattern('TestArtifact2', '/a_directory/*')
    fs_test.collect(outputs)

    # Deleted files and directories should not resolve
    paths = resolved_paths(outputs)
    assert set(paths) == set([
        '/a_directory/another_file',
        '/a_directory/a_file',
        '/passwords.txt',
    ])
    assert paths.count('/a_directory/a_file') == 2


def test_read_chunks(fs_test):
    path_object = fs_test.get_fullpath('/passwords.txt')
    content = next(path_object.read_chunks())

    assert content == b"""place,user,password
bank,joesmith,superrich
alarm system,-,1234
treasure chest,-,1111
uber secret laire,admin,admin
"""


def test_get_size(fs_test):
    path_object = fs_test.get_fullpath('/passwords.txt')
    assert path_object.get_size() == 116
