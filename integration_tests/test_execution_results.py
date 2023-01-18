import os
import sys
import glob
import json
import zipfile
import subprocess
from shutil import rmtree
from tempfile import mkdtemp

import pytest


FASTIR_ROOT = os.path.dirname(os.path.dirname(__file__))
TEST_ARTIFACTS = [
    # UNIX Artifacts
    'UnixPasswd',

    # Linux Artifacts
    'IPTablesRules',
    'LinuxPasswdFile',
    'LinuxProcMounts',

    # MacOS Artifacts
    'MacOSLoadedKexts',

    # Windows Artifacts
    'WindowsFirewallEnabledRules',
    'NTFSMFTFiles',
    'WindowsHostsFiles',
    'WMIDrivers',
]


@pytest.fixture(scope='session')
def temp_dir():
    dirpath = mkdtemp()

    yield dirpath

    rmtree(dirpath)


@pytest.fixture(scope='session')
def fastir_command(temp_dir):
    if sys.platform == 'darwin' or sys.platform == 'linux':
        command = os.path.join(FASTIR_ROOT, 'dist', 'fastir_artifacts', 'fastir_artifacts')
        command = ['sudo', command]
    elif sys.platform == 'win32':
        command = [os.path.join('dist', 'fastir_artifacts', 'fastir_artifacts.exe')]
    else:
        raise ValueError(f'Unknown platform {sys.platform}')

    return command + ['-o', temp_dir, '-i', ','.join(TEST_ARTIFACTS)]


@pytest.fixture(scope='session')
def fastir_output(fastir_command):
    try:
        command_output = subprocess.check_output(fastir_command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(str(e.output, 'utf-8'))
        raise

    return command_output

@pytest.fixture(scope='session')
def fastir_results(fastir_output, temp_dir):
    dirname = os.listdir(temp_dir)[0]
    results_path = os.path.join(temp_dir, dirname)

    # Fix ownership
    if sys.platform == 'darwin' or sys.platform == 'linux':
        command = ['sudo', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', results_path]
        subprocess.check_output(command)

    return results_path


@pytest.fixture(scope='session')
def command_results_file(fastir_results):
    return glob.glob(os.path.join(fastir_results, '*-commands.json'))[0]


@pytest.fixture(scope='session')
def command_results(command_results_file):
    with open(command_results_file, 'r') as f:
        yield json.load(f)


@pytest.fixture(scope='session')
def files_results_file(fastir_results):
    return glob.glob(os.path.join(fastir_results, '*-files.zip'))[0]


@pytest.fixture(scope='session')
def files_results(files_results_file):
    with zipfile.ZipFile(files_results_file) as zf:
        yield zf


@pytest.fixture(scope='session')
def files_results_names(files_results):
    return files_results.namelist()


@pytest.fixture(scope='session')
def logs_results_file(fastir_results):
    return glob.glob(os.path.join(fastir_results, '*-logs.txt'))[0]


@pytest.fixture(scope='session')
def logs_results(logs_results_file):
    with open(logs_results_file, 'r') as f:
        yield f.read()


def test_collection_successful(fastir_output):
    assert b'Finished collecting artifacts' in fastir_output


def test_output_directory_exists(fastir_results):
    assert os.path.isdir(fastir_results)


def test_command_results_exists(command_results_file):
    assert os.path.isfile(command_results_file)


def test_file_results_exists(files_results_file):
    assert os.path.isfile(files_results_file)


def test_logs(logs_results_file, logs_results):
    assert os.path.isfile(logs_results_file)
    assert 'Loading artifacts' in logs_results
    assert 'Collecting artifacts from' in logs_results
    assert 'Collecting file' in logs_results
    assert 'Collecting command' in logs_results
    assert 'Finished collecting artifacts' in logs_results


#####################
## Linux Tests
#####################
@pytest.mark.linux
def test_command_iptables(command_results):
    assert 'IPTablesRules' in command_results

    for command, output in command_results['IPTablesRules'].items():
        assert 'iptables' in command
        assert 'Chain INPUT' in output


@pytest.mark.linux
@pytest.mark.darwin
def test_file_passwd(files_results_names, files_results):
    assert '/etc/passwd' in files_results_names
    with files_results.open('/etc/passwd') as f:
        assert b'root' in f.read()


@pytest.mark.linux
def test_file_mounts(files_results_names, files_results):
    assert '/proc/mounts' in files_results_names
    with files_results.open('/proc/mounts') as f:
        assert b' / ' in f.read()


#####################
## macOS Tests
#####################
@pytest.mark.darwin
def test_command_kexts(command_results):
    assert 'MacOSLoadedKexts' in command_results

    for command, output in command_results['MacOSLoadedKexts'].items():
        assert 'kextstat' in command
        assert 'Name' in output


#####################
## Windows Tests
#####################
@pytest.fixture(scope='session')
def wmi_results_file(fastir_results):
    return glob.glob(os.path.join(fastir_results, '*-wmi.json'))[0]


@pytest.fixture(scope='session')
def wmi_results(wmi_results_file):
    with open(wmi_results_file, 'r') as f:
        yield json.load(f)


@pytest.mark.win32
def test_command_windows_firewall(command_results):
    assert 'WindowsFirewallEnabledRules' in command_results

    for command, output in command_results['WindowsFirewallEnabledRules'].items():
        assert 'netsh.exe' in command
        assert 'Windows Defender Firewall Rules:' in output


@pytest.mark.win32
def test_file_mft(files_results_names, files_results):
    assert 'C/$MFT' in files_results_names
    with files_results.open('C/$MFT') as f:
        assert b'FILE0' in f.read()


@pytest.mark.win32
def test_file_hosts(files_results_names, files_results):
    assert 'C/Windows/System32/drivers/etc/hosts' in files_results_names
    with files_results.open('C/Windows/System32/drivers/etc/hosts') as f:
        assert b'This is a sample HOSTS file used by Microsoft TCP/IP for Windows.' in f.read()


@pytest.mark.win32
def test_wmi_results_exists(wmi_results_file):
    assert os.path.isfile(wmi_results_file)


@pytest.mark.win32
def test_wmi_drivers(wmi_results):
    assert 'WMIDrivers' in wmi_results
    assert len(wmi_results['WMIDrivers']) > 0

    for query, output in wmi_results['WMIDrivers'].items():
        assert 'SELECT' in query
        assert len(output) > 0
        assert 'Description' in output[0]
        assert 'DisplayName' in output[0]
