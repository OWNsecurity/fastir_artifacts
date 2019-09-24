import os
import hashlib
import json
import logging
import zipfile
import platform
from datetime import datetime
from collections import defaultdict

from .logging import logger, PROGRESS


def parse_human_size(size):
    units = {
        'B': 1,
        'K': 1024,
        'M': 1024 * 1024,
        'G': 1024 * 1024 * 1024
    }

    if size:
        unit = size[-1]

        if unit in units:
            return int(size[:-1]) * units[unit]
        else:
            return int(size)


def normalize_filepath(filepath):
    # On Windows, make sure we remove the ':' behind the drive letter
    if filepath.index(os.path.sep) > 0:
        filepath = filepath.replace(':', '', 1)

    return filepath.encode('utf-8', 'backslashreplace').decode('utf-8')


class Outputs:
    def __init__(self, dirpath, maxsize, sha256):
        self._dirpath = dirpath

        self._zip = None
        self._maxsize = parse_human_size(maxsize)
        self._sha256 = sha256

        self._commands = defaultdict(dict)
        self._wmi = defaultdict(dict)
        self._registry = defaultdict(lambda: defaultdict(dict))

        self._init_output_()

    def _init_output_(self):
        os.umask(0o077)
        now = datetime.now().strftime(r'%Y%m%d%H%M%S')

        self._hostname = platform.node()
        self._dirpath = os.path.join(self._dirpath, f"{now}-{self._hostname}")

        # Create the directory
        os.makedirs(self._dirpath)

        self._setup_logging()

    def _setup_logging(self):
        logfile = os.path.join(self._dirpath, f'{self._hostname}-logs.txt')

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_output = logging.FileHandler(logfile, 'w', 'utf-8')
        file_output.setLevel(logging.INFO)
        file_output.setFormatter(formatter)

        console_output = logging.StreamHandler()
        console_output.setLevel(PROGRESS)
        console_output.setFormatter(formatter)

        logger.addHandler(file_output)
        logger.addHandler(console_output)

    def add_collected_file(self, artifact, path_object):
        logger.info(f"Collecting file '{path_object.path}' for artifact '{artifact}'")

        # Make sure to create the file if it do not exists
        if self._zip is None:
            self._zip = zipfile.ZipFile(
                os.path.join(self._dirpath, f'{self._hostname}-files.zip'), 'w', zipfile.ZIP_DEFLATED)

        if not self._maxsize or path_object.get_size() <= self._maxsize:
            # Write file content to zipfile
            filename = normalize_filepath(path_object.path)

            if filename not in self._zip.namelist():
                zinfo = zipfile.ZipInfo(filename=filename)
                zinfo.compress_type = zipfile.ZIP_DEFLATED

                # Read/write by chunks to reduce memory footprint
                if self._sha256:
                    h = hashlib.sha256()
                with self._zip._lock:
                    with self._zip.open(zinfo, mode='w', force_zip64=True) as dest:
                        for chunk in path_object.read_chunks():
                            dest.write(chunk)
                            if self._sha256:
                                h.update(chunk)
                if self._sha256:
                    logger.info(f"File '{path_object.path}' has SHA-256 '{h.hexdigest()}'")
        else:
            logger.warning(f"Ignoring file '{path_object.path}' because of its size")

    def add_collected_command(self, artifact, command, output):
        logger.info(f"Collecting command '{command}' for artifact '{artifact}'")
        self._commands[artifact][command] = output.decode('utf-8', errors='replace')

    def add_collected_wmi(self, artifact, query, output):
        logger.info(f"Collecting WMI query '{query}' for artifact '{artifact}'")
        self._wmi[artifact][query] = output

    def add_collected_registry_value(self, artifact, key, name, value, type_):
        logger.info(f"Collecting Reg value '{name}' from '{key}' for artifact '{artifact}'")
        self._registry[artifact][key][name] = {
            'value': value,
            'type': type_
        }

    def close(self):
        if self._zip:
            self._zip.close()

        if self._commands:
            with open(os.path.join(self._dirpath, f'{self._hostname}-commands.json'), 'w') as out:
                json.dump(self._commands, out, indent=2)

        if self._wmi:
            with open(os.path.join(self._dirpath, f'{self._hostname}-wmi.json'), 'w') as out:
                json.dump(self._wmi, out, indent=2)

        if self._registry:
            with open(os.path.join(self._dirpath, f'{self._hostname}-registry.json'), 'w') as out:
                json.dump(self._registry, out, indent=2)

        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
