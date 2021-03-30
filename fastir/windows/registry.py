import os
import json
import winreg

import artifacts

from fastir.common.filesystem import FileSystem
from fastir.common.path_components import PathObject
from fastir.common.collector import AbstractCollector


class RegistryReader(FileSystem):
    def __init__(self, hive, pattern):
        self._hive = hive
        self._pattern = pattern

        self._keys = {}

    def _key(self, path_object, parent):
        if path_object.path not in self._keys:
            self._keys[path_object.path] = winreg.OpenKey(parent.obj, path_object.name, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY)

        path_object.obj = self._keys[path_object.path]

        return path_object

    def _base_generator(self):
        yield PathObject(self, self._hive, self._hive, getattr(winreg, self._hive))

    def keys_to_collect(self):
        path_components = self._parse(self._pattern)

        generator = self._base_generator
        for component in path_components:
            generator = component.get_generator(generator)

        for path in generator():
            yield path

    def list_directory(self, path_object):
        try:
            index = 0
            while True:
                name = winreg.EnumKey(path_object.obj, index)
                index += 1

                try:
                    keypath = os.path.join(path_object.path, name)
                    yield self._key(
                        PathObject(self, name.lower(), keypath),
                        path_object)
                except OSError:
                    pass
        except OSError:
            pass

    def get_path(self, parent, name):
        try:
            return self._key(
                PathObject(self, name, os.path.join(parent.path, name)),
                parent)
        except OSError:
            return None

    def is_directory(self, path_object):
        try:
            winreg.EnumKey(path_object.obj, 0)
            return True
        except OSError:
            return False

    def is_file(self, path_object):
        return True

    def close(self):
        for _, handle in self._keys.items():
            winreg.CloseKey(handle)

    def get_key_values(self, key_to_collect):
        try:
            index = 0

            while True:
                name, value, type_ = winreg.EnumValue(key_to_collect.obj, index)
                yield name, self.normalize_value(value), type_
                index += 1
        except OSError:
            pass

    def get_key_value(self, key, value):
        try:
            value, type_ = winreg.QueryValueEx(key.obj, value)

            return {
                "value": self.normalize_value(value),
                "type": type_
            }
        except FileNotFoundError:
            return None

    @staticmethod
    def normalize_value(value):
        try:
            json.dumps(value)
            return value
        except TypeError:
            return repr(value)


class RegistryCollector(AbstractCollector):
    def __init__(self):
        self._keys = []
        self._values = []

    def add_key(self, artifact, key):
        key_parts = key.split('\\')

        self._keys.append({
            'artifact': artifact,
            'hive': key_parts[0],
            'key': '/'.join(key_parts[1:])
        })

    def add_value(self, artifact, key, value):
        key_parts = key.split('\\')

        self._values.append({
            'artifact': artifact,
            'hive': key_parts[0],
            'key': '/'.join(key_parts[1:]),
            'value': value
        })

    def collect(self, output):
        for key in self._keys:
            reader = RegistryReader(key['hive'], key['key'].lower())

            for key_to_collect in reader.keys_to_collect():
                for name, value, type_ in reader.get_key_values(key_to_collect):
                    output.add_collected_registry_value(
                        key['artifact'], key_to_collect.path, name, value, type_)

            reader.close()

        for key_value in self._values:
            reader = RegistryReader(key_value['hive'], key_value['key'].lower())

            for key_to_collect in reader.keys_to_collect():
                value = reader.get_key_value(key_to_collect, key_value['value'])

                if value:
                    output.add_collected_registry_value(
                        key_value['artifact'], key_to_collect.path, key_value['value'], value['value'], value['type'])

            reader.close()

    def register_source(self, artifact_definition, artifact_source, variables):
        supported = False

        if artifact_source.type_indicator == artifacts.definitions.TYPE_INDICATOR_WINDOWS_REGISTRY_KEY:
            supported = True

            for pattern in artifact_source.keys:
                for key in variables.substitute(pattern):
                    self.add_key(artifact_definition.name, key)

        elif artifact_source.type_indicator == artifacts.definitions.TYPE_INDICATOR_WINDOWS_REGISTRY_VALUE:
            supported = True

            for key_value in artifact_source.key_value_pairs:
                for key in variables.substitute(key_value['key']):
                    self.add_value(artifact_definition.name, key, key_value['value'])

        return supported
