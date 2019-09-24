import os

import pytest

from fastir.common.filesystem import OSFileSystem


FS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'filesystem'))


@pytest.fixture
def fs_test():
    return OSFileSystem(FS_ROOT)


def fp(relative_path):
    """Create a full path from a relative path"""
    return os.path.join(FS_ROOT, relative_path)


def resolved_paths(outputs):
    paths = []

    for call in outputs.add_collected_file.call_args_list:
        assert call[0][0] == 'TestArtifact'
        paths.append(
            os.path.relpath(call[0][1].path, FS_ROOT).replace(os.path.sep, '/'))

    return paths


def test_path_resolution_simple(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('root.txt'))
    fs_test.collect(outputs)

    assert resolved_paths(outputs) == ['root.txt']


def test_path_resolution_simple2(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('l1/l2/l2.txt'))
    fs_test.collect(outputs)

    assert resolved_paths(outputs) == ['l1/l2/l2.txt']


def test_path_resolution_globbing_star(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('*.txt'))
    fs_test.collect(outputs)

    assert set(resolved_paths(outputs)) == set(['root.txt', 'root2.txt', 'test.txt'])


def test_path_resolution_globbing_star2(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('root*.txt'))
    fs_test.collect(outputs)

    assert set(resolved_paths(outputs)) == set(['root.txt', 'root2.txt'])


def test_path_resolution_globbing_question(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('root?.txt'))
    fs_test.collect(outputs)

    assert resolved_paths(outputs) == ['root2.txt']


def test_path_resolution_globbing_star_directory(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('l1/*/l2.txt'))
    fs_test.collect(outputs)

    assert resolved_paths(outputs) == ['l1/l2/l2.txt']


def test_path_resolution_recursive_star(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('**/l2.txt'))
    fs_test.collect(outputs)

    assert resolved_paths(outputs) == ['l1/l2/l2.txt']


def test_path_resolution_recursive_star_default_depth(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('**/*.txt'))
    fs_test.collect(outputs)

    # Should only go to l3 because 3 is the default depth
    assert set(resolved_paths(outputs)) == set([
        'l1/l1.txt', 'l1/l2/l2.txt', 'l1/l2/l3/l3.txt'])


def test_path_resolution_recursive_star_custom_depth(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('**4/*.txt'))
    fs_test.collect(outputs)

    # Should reach l4 because of the custom depth
    assert set(resolved_paths(outputs)) == set([
        'l1/l1.txt', 'l1/l2/l2.txt', 'l1/l2/l3/l3.txt', 'l1/l2/l3/l4/l4.txt'])


def test_path_resolution_recursive_star_root(fs_test, outputs):
    fs_test.add_pattern('TestArtifact', fp('**.txt'))
    fs_test.collect(outputs)

    # Should only go to l2 because 3 is the default depth
    assert set(resolved_paths(outputs)) == set([
        'root.txt', 'root2.txt', 'test.txt', 'l1/l1.txt', 'l1/l2/l2.txt'])


def test_is_symlink(fs_test):
    path_object = fs_test.get_fullpath(fp('root.txt'))
    assert path_object.is_symlink() is False
