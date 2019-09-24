import re
import os

import pytsk3
import psutil
import artifacts

from fastir.common.logging import logger
from fastir.common.collector import AbstractCollector
from fastir.common.path_components import RecursionPathComponent, GlobPathComponent, RegularPathComponent, PathObject

CHUNK_SIZE = 5 * 1024 * 1024
PATH_RECURSION_REGEX = re.compile(r"\*\*(?P<max_depth>\d*)")
PATH_GLOB_REGEX = re.compile(r"\*|\?|\[.+\]")

TSK_FILESYSTEMS = ['NTFS', 'ext3', 'ext4']


class FileSystem:
    def __init__(self):
        self._patterns = []

    def add_pattern(self, artifact, pattern):
        self._patterns.append({
            'artifact': artifact,
            'pattern': pattern
        })

    def _relative_path(self, filepath):
        raise NotImplementedError

    def _parse(self, pattern):
        components = []

        items = pattern.split('/')
        for i, item in enumerate(items):
            # Search for '**' glob recursion
            recursion = PATH_RECURSION_REGEX.search(item)
            if recursion:
                max_depth = None

                if recursion.group('max_depth'):
                    max_depth = int(recursion.group('max_depth'))

                components.append(RecursionPathComponent(i < (len(items) - 1), max_depth))
            else:
                glob = PATH_GLOB_REGEX.search(item)
                if glob:
                    components.append(GlobPathComponent(i < (len(items) - 1), item))
                else:
                    components.append(RegularPathComponent(i < (len(items) - 1), item))

        return components

    def _base_generator(self):
        raise NotImplementedError

    def collect(self, output):
        for pattern in self._patterns:
            logger.debug("Collecting pattern '{}' for artifact '{}'".format(pattern['pattern'], pattern['artifact']))

            # Normalize the pattern, relative to the mountpoint
            relative_pattern = self._relative_path(pattern['pattern'])
            path_components = self._parse(relative_pattern)

            generator = self._base_generator
            for component in path_components:
                generator = component.get_generator(generator)

            for path in generator():
                try:
                    output.add_collected_file(pattern['artifact'], path)
                except Exception as e:
                    logger.error(f"Error collecting file '{path.path}': {str(e)}")


class TSKFileSystem(FileSystem):
    def __init__(self, manager, device, path):
        self._manager = manager
        self._path = path
        self._root = None

        # Unix Device
        if self._path.startswith('/'):
            self._device = device
        else:
            # On Windows, we need a specific format '\\.\<DRIVE_LETTER>:'
            self._device = r"\\.\{}:".format(device[0])

        # Cache parsed entries for better performances
        self._entries_cache = {}
        self._entries_cache_last = []

        super().__init__()

    def _relative_path(self, filepath):
        normalized_path = filepath.replace(os.path.sep, '/')
        return normalized_path[len(self._path):].lstrip('/')

    def _base_generator(self):
        if not self._root:
            img_info = pytsk3.Img_Info(self._device)
            self._fs_info = pytsk3.FS_Info(img_info)
            self._root = self._fs_info.open_dir('')

        yield PathObject(self, os.path.basename(self._path), self._path, self._root)

    def is_allocated(self, tsk_entry):
        return (int(tsk_entry.info.name.flags) & pytsk3.TSK_FS_NAME_FLAG_ALLOC != 0 and
                int(tsk_entry.info.meta.flags) & pytsk3.TSK_FS_META_FLAG_ALLOC != 0)

    def is_directory(self, path_object):
        return path_object.obj.info.meta.type in [pytsk3.TSK_FS_META_TYPE_DIR, pytsk3.TSK_FS_META_TYPE_VIRT_DIR]

    def is_file(self, path_object):
        return path_object.obj.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG

    def is_symlink(self, path_object):
        return path_object.obj.info.meta.type == pytsk3.TSK_FS_META_TYPE_LNK

    def _follow_symlink(self, parent, path_object):
        # TODO: attempt to follow symlinks with TSK
        #
        # As a temporary fix, downgrade all links to OSFileSystem so that
        # they are still collected
        return OSFileSystem('/').get_fullpath(path_object.path)

    def list_directory(self, path_object):
        if path_object.path in self._entries_cache:
            return self._entries_cache[path_object.path]
        else:
            # Make sure we do not keep more than 10 000 entries in the cache
            if len(self._entries_cache_last) >= 10000:
                first = self._entries_cache_last.popleft()
                del self._entries_cache[first]

            entries = []
            directory = path_object.obj

            if not isinstance(directory, pytsk3.Directory):
                if not self.is_directory(path_object):
                    return

                directory = path_object.obj.as_directory()

            for entry in directory:
                if (
                    not hasattr(entry, 'info') or
                    not hasattr(entry.info, 'name') or
                    not hasattr(entry.info.name, 'name') or
                    entry.info.name.name in [b'.', b'..'] or
                    not hasattr(entry.info, 'meta') or
                    not hasattr(entry.info.meta, 'size') or
                    not hasattr(entry.info.meta, 'type') or
                    not self.is_allocated(entry)
                ):
                    continue

                name = entry.info.name.name.decode('utf-8', errors='replace')
                filepath = os.path.join(path_object.path, name)
                entry_path_object = PathObject(self, name, filepath, entry)

                if entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_LNK:
                    symlink_object = self._follow_symlink(path_object, entry_path_object)

                    if symlink_object:
                        entries.append(symlink_object)
                else:
                    entries.append(entry_path_object)

            self._entries_cache[path_object.path] = entries
            self._entries_cache_last.append(entries)

            return entries

    def get_path(self, parent, name):
        for path_object in self.list_directory(parent):
            if os.path.normcase(name) == os.path.normcase(path_object.name):
                return path_object

    def get_fullpath(self, filepath):
        relative_path = self._relative_path(filepath)
        path_object = next(self._base_generator())

        for part in relative_path.split('/'):
            path_object = self.get_path(path_object, part)

        return path_object

    def read_chunks(self, path_object):
        size = path_object.obj.info.meta.size
        offset = 0

        while offset < size:
            chunk_size = min(CHUNK_SIZE, size - offset)
            chunk = path_object.obj.read_random(offset, chunk_size)

            if chunk:
                offset += chunk_size
                yield chunk
            else:
                break

    def get_size(self, path_object):
        return path_object.obj.info.meta.size


class OSFileSystem(FileSystem):
    def __init__(self, path):
        self._path = path

        super().__init__()

    def _relative_path(self, filepath):
        normalized_path = filepath.replace(os.path.sep, '/')
        return normalized_path[len(self._path):].lstrip('/')

    def _base_generator(self):
        yield PathObject(self, os.path.basename(self._path), self._path)

    def is_directory(self, path):
        return os.path.isdir(path.path)

    def is_file(self, path):
        return os.path.isfile(path.path)

    def is_symlink(self, path):
        # When using syscalls, symlinks are automatically followed
        return False

    def list_directory(self, path):
        try:
            for name in os.listdir(path.path):
                yield PathObject(self, name, os.path.join(path.path, name))
        except Exception as e:
            logger.error(f"Error analyzing directory '{path.path}': {str(e)}")

    def get_path(self, parent, name):
        return PathObject(self, name, os.path.join(parent.path, name))

    def get_fullpath(self, fullpath):
        return PathObject(self, os.path.basename(fullpath), fullpath)

    def read_chunks(self, path_object):
        with open(path_object.path, 'rb') as f:
            chunk = f.read(CHUNK_SIZE)

            if chunk:
                yield chunk

    def get_size(self, path_object):
        stats = os.lstat(path_object.path)

        return stats.st_size


class FileSystemManager(AbstractCollector):
    def __init__(self):
        self._filesystems = {}
        self._mount_points = psutil.disk_partitions(True)

    def _get_mountpoint(self, filepath):
        best_mountpoint = None
        best_mountpoint_length = 0

        for mountpoint in self._mount_points:
            if filepath.startswith(mountpoint.mountpoint):
                if len(mountpoint.mountpoint) > best_mountpoint_length:
                    best_mountpoint = mountpoint
                    best_mountpoint_length = len(mountpoint.mountpoint)

        if best_mountpoint is None:
            raise IndexError(f'Could not find a mountpoint for path {filepath}')

        return best_mountpoint

    def _get_filesystem(self, filepath):
        # Fetch the mountpoint for this particular path
        mountpoint = self._get_mountpoint(filepath)

        # Fetch or create the matching filesystem
        if mountpoint.mountpoint not in self._filesystems:
            if mountpoint.fstype in TSK_FILESYSTEMS:
                self._filesystems[mountpoint.mountpoint] = TSKFileSystem(
                    self, mountpoint.device, mountpoint.mountpoint)
            else:
                self._filesystems[mountpoint.mountpoint] = OSFileSystem(mountpoint.mountpoint)

        return self._filesystems[mountpoint.mountpoint]

    def get_path_object(self, filepath):
        filesystem = self._get_filesystem(filepath)
        return filesystem.get_fullpath(filepath)

    def add_pattern(self, artifact, pattern):
        pattern = os.path.normpath(pattern)

        # If the pattern starts with '\', it should be applied to all drives
        if pattern.startswith('\\'):
            for mountpoint in self._mount_points:
                if mountpoint.fstype in TSK_FILESYSTEMS:
                    extended_pattern = os.path.join(mountpoint.mountpoint, pattern[1:])
                    filesystem = self._get_filesystem(extended_pattern)
                    filesystem.add_pattern(artifact, extended_pattern)

        else:
            filesystem = self._get_filesystem(pattern)
            filesystem.add_pattern(artifact, pattern)

    def collect(self, output):
        for path in list(self._filesystems):
            logger.debug(f"Start collection for '{path}'")
            self._filesystems[path].collect(output)

    def register_source(self, artifact_definition, artifact_source, variables):
        supported = False

        if artifact_source.type_indicator == artifacts.definitions.TYPE_INDICATOR_FILE:
            supported = True

            for p in artifact_source.paths:
                for sp in variables.substitute(p):
                    self.add_pattern(artifact_definition.name, sp)

        return supported
