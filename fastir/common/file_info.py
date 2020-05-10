import hashlib
import filetype
from datetime import datetime

from pefile import PE

MAX_PE_SIZE = 50 * 1024 * 1024


class FileInfo:
    def __init__(self, path_object):
        self._path_object = path_object
        self.size = path_object.get_size()

        self._info = {}
        self._content = b""

    def compute(self):
        self.md5 = hashlib.md5()
        self.sha1 = hashlib.sha1()
        self.sha256 = hashlib.sha256()
        self.mime_type = None

        for i, chunk in enumerate(self._path_object.read_chunks()):
            self.md5.update(chunk)
            self.sha1.update(chunk)
            self.sha256.update(chunk)

            if i == 0:
                file_type = filetype.guess(chunk)
                if file_type:
                    self.mime_type = file_type.mime

            if self.mime_type == "application/x-msdownload" and self.size < MAX_PE_SIZE:
                self._content += chunk

        return self._get_results()

    def _get_results(self):
        self._info = {
            '@timestamp': datetime.utcnow().isoformat(),
            'file': {
                'size': self.size,
                'path': self._path_object.path,
                'hash': {
                    'md5': self.md5.hexdigest(),
                    'sha1': self.sha1.hexdigest(),
                    'sha256': self.sha256.hexdigest()
                }
            }
        }

        if self.mime_type:
            self._info['file']['mime_type'] = self.mime_type

        if len(self._content) > 0:
            try:
                self._add_pe_info()
            except Exception:
                pass

        return self._info

    def _add_file_property(self, category, field, value):
        self._info['file'].setdefault(category, {})
        self._info['file'][category][field] = value

    def _add_vs_info(self, parsed_pe):
        VS_INFO_FIELDS = {
            b'CompanyName': 'company',
            b'FileDescription': 'description',
            b'FileVersion': 'file_version',
            b'InternalName': 'original_file_name',
            b'ProductName': 'product'
        }

        if hasattr(parsed_pe, "VS_VERSIONINFO"):
            if hasattr(parsed_pe, "FileInfo"):
                for finfo in parsed_pe.FileInfo:
                    for entry in finfo:
                        if hasattr(entry, 'StringTable'):
                            for st_entry in entry.StringTable:
                                for str_entry in st_entry.entries.items():
                                    if str_entry[0] in VS_INFO_FIELDS and str_entry[1]:
                                        self._add_file_property(
                                            'pe',
                                            VS_INFO_FIELDS[str_entry[0]],
                                            str_entry[1].decode('utf-8', 'replace'))

    def _add_pe_info(self):
        parsed_pe = PE(data=self._content)

        self._add_vs_info(parsed_pe)
        self._add_file_property('pe', 'imphash', parsed_pe.get_imphash())
