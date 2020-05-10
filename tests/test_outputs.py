import io
import os
import glob
import json
import pytest
import platform
from zipfile import ZipFile

from jsonlines import Reader

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


@pytest.fixture
def test_file(temp_dir):
    test_file = os.path.join(temp_dir, 'test_file.txt')

    with open(test_file, 'w') as f:
        f.write('MZtest content')

    yield test_file


@pytest.fixture
def test_pe_file():
    DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))

    return OSFileSystem('/').get_fullpath(os.path.join(DATA_ROOT, 'MSVCR71.dll'))


def test_collect_file_info(temp_dir, test_file):
    output = Outputs(temp_dir, None, False)
    output.add_collected_file_info('TestArtifact', OSFileSystem('/').get_fullpath(test_file))
    output.close()

    with Reader(output_file_content(temp_dir, '*-file_info.jsonl').splitlines()) as jsonl:
        record = jsonl.read()

        assert '@timestamp' in record
        assert record['file']['path'].endswith('test_file.txt')
        assert record['file']['size'] == 14
        assert record['file']['mime_type'] == "application/x-msdownload"
        assert record['file']['hash']['md5'] == "10dbf3e392abcc57f8fae061c7c0aeec"
        assert record['file']['hash']['sha1'] == "7ef0fe6c3855fbac1884e95622d9e45ce1d4ae9b"
        assert record['file']['hash']['sha256'] == "cfb91ddbf08c52ff294fdf1657081a98c090d270dbb412a91ace815b3df947b6"


def test_collect_pe_file_info(temp_dir, test_pe_file):
    output = Outputs(temp_dir, None, False)
    output.add_collected_file_info('TestArtifact', test_pe_file)
    output.close()

    with Reader(output_file_content(temp_dir, '*-file_info.jsonl').splitlines()) as jsonl:
        record = jsonl.read()

        assert '@timestamp' in record
        assert record['file']['path'].endswith('MSVCR71.dll')
        assert record['file']['size'] == 348160
        assert record['file']['mime_type'] == "application/x-msdownload"
        assert record['file']['hash']['md5'] == "86f1895ae8c5e8b17d99ece768a70732"
        assert record['file']['hash']['sha1'] == "d5502a1d00787d68f548ddeebbde1eca5e2b38ca"
        assert record['file']['hash']['sha256'] == "8094af5ee310714caebccaeee7769ffb08048503ba478b879edfef5f1a24fefe"
        assert record['file']['pe']['company'] == "Microsoft Corporation"
        assert record['file']['pe']['description'] == "Microsoft® C Runtime Library"
        assert record['file']['pe']['file_version'] == "7.10.3052.4"
        assert record['file']['pe']['original_file_name'] == "MSVCR71.DLL"
        assert record['file']['pe']['product'] == "Microsoft® Visual Studio .NET"
        assert record['file']['pe']['imphash'] == "7acc8c379c768a1ecd81ec502ff5f33e"


def test_collect_file(temp_dir, test_file):
    output = Outputs(temp_dir, None, False)
    output.add_collected_file('TestArtifact', OSFileSystem('/').get_fullpath(test_file))
    output.close()

    zip_content = io.BytesIO(output_file_content(temp_dir, '*-files.zip'))
    zipfile = ZipFile(zip_content)
    zipped_file = zipfile.namelist()[0]

    assert zipped_file.endswith('test_file.txt')


def test_collect_file_size_filter(temp_dir, test_file):
    # Create a file that should be ignored due to its size
    test_big_file = os.path.join(temp_dir, 'test_big_file.txt')

    with open(test_big_file, 'w') as f:
        f.write('some bigger content')

    output = Outputs(temp_dir, '15', False)  # Set maximum size to 10 bytes
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
