from fnmatch import fnmatch


class PathObject:
    def __init__(self, filesystem, name, path, obj=None):
        self.filesystem = filesystem
        self.name = name
        self.obj = obj
        self.path = path

    def is_directory(self):
        return self.filesystem.is_directory(self)

    def is_file(self):
        return self.filesystem.is_file(self)

    def is_symlink(self):
        return self.filesystem.is_symlink(self)

    def list_directory(self):
        return self.filesystem.list_directory(self)

    def get_path(self, path):
        return self.filesystem.get_path(self, path)

    def read_chunks(self):
        return self.filesystem.read_chunks(self)

    def get_size(self):
        return self.filesystem.get_size(self)


class PathComponent:
    def __init__(self, directory):
        self._directory = directory
        self._generator = None

    def get_generator(self, generator):
        self._generator = generator
        return self._generate

    def _generate(self):
        raise NotImplementedError


class RecursionPathComponent(PathComponent):
    def __init__(self, directory, max_depth=None):
        super().__init__(directory)

        self.max_depth = max_depth or 3

    def _generate(self):
        for parent in self._generator():
            yield from self._recurse_from_dir(parent, depth=0)

    def _recurse_from_dir(self, parent, depth):
        if depth < self.max_depth:
            for path in parent.list_directory():
                if path.is_directory():
                    yield from self._recurse_from_dir(path, depth + 1)

                    # Special case when the file is considered to be both a dir and a file
                    # This only happens with registry keys
                    if self._directory or path.is_file():
                        yield path
                elif not self._directory:
                    yield path


class GlobPathComponent(PathComponent):
    def __init__(self, directory, path):
        super().__init__(directory)

        self._path = path

    def _generate(self):
        for parent in self._generator():
            for path in parent.list_directory():
                if fnmatch(path.name, self._path):
                    if self._directory and path.is_directory():
                        yield path
                    elif not self._directory and path.is_file():
                        yield path


class RegularPathComponent(PathComponent):
    def __init__(self, directory, path):
        super().__init__(directory)

        self._path = path

    def _generate(self):
        for parent in self._generator():
            path = parent.get_path(self._path)

            if path:
                if self._directory and path.is_directory():
                    yield path
                elif not self._directory and path.is_file():
                    yield path
