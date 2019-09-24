import io
import os
import glob
import json
import pytest
import platform
from zipfile import ZipFile

from fastir.common.logging import logger
from fastir.common.filesystem import OSFileSystem
from fastir.common.output import parse_human_size, normalize_filepath, Outputs


def output_file_content(dirpath, pattern):
    """Read the content of an output file with specified pattern."""
    outdir = glob.glob(os.path.join(dirpath, f'*-{platform.node()}'))[0]
    filepath = glob.glob(os.path.join(outdir, pattern))[0]

    with open(filepath, 'rb') as f:
        return f.read()


def test_parse_human_size():
    assert parse_human_size('1') == 1
    assert parse_human_size('2B') == 2
    assert parse_human_size('3K') == 3072
    assert parse_human_size('4M') == 4194304
    assert parse_human_size('5G') == 5368709120

    with pytest.raises(ValueError):
        parse_human_size('124XS')


def test_normalize_filepath():
    assert normalize_filepath('C:/test'.replace('/', os.path.sep)) == os.path.join('C', 'test')
    assert normalize_filepath(os.path.join('', 'usr', 'share')) == os.path.join('', 'usr', 'share')


def test_logging(temp_dir):
    # Create an Outputs instance and log a message
    output = Outputs(temp_dir, None, False)
    logger.info('test log message')
    output.close()

    # Make sure the log message appears in the output directory
    logs = output_file_content(temp_dir, '*-logs.txt')
    assert b'test log message' in logs


def test_collect_file(temp_dir):
    test_file = os.path.join(temp_dir, 'test_file.txt')

    with open(test_file, 'w') as f:
        f.write('test content')

    output = Outputs(temp_dir, None, False)
    output.add_collected_file('TestArtifact', OSFileSystem('/').get_fullpath(test_file))
    output.close()

    zip_content = io.BytesIO(output_file_content(temp_dir, '*-files.zip'))
    zipfile = ZipFile(zip_content)
    zipped_file = zipfile.namelist()[0]

    assert zipped_file.endswith('test_file.txt')


def test_collect_file_size_filter(temp_dir):
    # Create a file that should be collected
    test_file = os.path.join(temp_dir, 'test_file.txt')

    with open(test_file, 'w') as f:
        f.write('content')

    # Create a file that should be ignored due to its size
    test_big_file = os.path.join(temp_dir, 'test_big_file.txt')

    with open(test_big_file, 'w') as f:
        f.write('some bigger content')

    output = Outputs(temp_dir, '10', False)  # Set maximum size to 10 bytes
    output.add_collected_file('TestArtifact', OSFileSystem('/').get_fullpath(test_file))
    output.add_collected_file('TestArtifact', OSFileSystem('/').get_fullpath(test_big_file))
    output.close()

    zip_content = io.BytesIO(output_file_content(temp_dir, '*-files.zip'))
    zipfile = ZipFile(zip_content)
    zipped_files = zipfile.namelist()

    assert len(zipped_files) == 1
    assert zipped_files[0].endswith('test_file.txt')

    logs = output_file_content(temp_dir, '*-logs.txt')
    assert b"test_big_file.txt' because of its size" in logs


def test_collect_command(temp_dir):
    output = Outputs(temp_dir, None, False)
    output.add_collected_command('TestArtifact', 'command', b'output')
    output.close()

    commands = json.loads(output_file_content(temp_dir, '*-commands.json'))
    assert commands == {
        'TestArtifact': {
            'command': 'output'
        }
    }


def test_collect_wmi(temp_dir):
    output = Outputs(temp_dir, None, False)
    output.add_collected_wmi('TestArtifact', 'query', 'output')
    output.close()

    wmi = json.loads(output_file_content(temp_dir, '*-wmi.json'))
    assert wmi == {
        'TestArtifact': {
            'query': 'output'
        }
    }


def test_collect_registry(temp_dir):
    output = Outputs(temp_dir, None, False)
    output.add_collected_registry_value('TestArtifact', 'key', 'name', 'value', 'type')
    output.close()

    registry = json.loads(output_file_content(temp_dir, '*-registry.json'))
    assert registry == {
        'TestArtifact': {
            'key': {
                'name': {
                    'value': 'value',
                    'type': 'type'
                }
            }
        }
    }
