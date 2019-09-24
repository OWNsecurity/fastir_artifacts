import artifacts
import pywintypes
import win32com.client

from fastir.common.logging import logger
from fastir.common.collector import AbstractCollector


def wmi_query(query, base_object=None):
    if base_object is None:
        base_object = r'winmgmts:\root\cimv2'

    try:
        wmi = win32com.client.GetObject(base_object)
        results = wmi.ExecQuery(query)

        objs = []
        for result in results:
            obj = {}

            for p in result.Properties_:
                if isinstance(p.Value, win32com.client.CDispatch):
                    continue
                if isinstance(p.Value, tuple) and len(p.Value) > 0 and isinstance(p.Value[0], win32com.client.CDispatch):
                    continue

                obj[p.Name] = p.Value

            objs.append(obj)

        return objs
    except pywintypes.com_error:
        logger.error(f"Error while retrieving results for WMI Query '{query}'")


class WMIExecutor(AbstractCollector):
    def __init__(self):
        self._queries = []

    def add_query(self, artifact, query, base_object):
        self._queries.append({
            'artifact': artifact,
            'query': query,
            'base_object': base_object
        })

    def collect(self, output):
        for query in self._queries:
            result = wmi_query(query['query'], query['base_object'])
            output.add_collected_wmi(query['artifact'], query['query'], result)

    def register_source(self, artifact_definition, artifact_source, variables):
        if artifact_source.type_indicator == artifacts.definitions.TYPE_INDICATOR_WMI_QUERY:
            for query in variables.substitute(artifact_source.query):
                self.add_query(artifact_definition.name, query, artifact_source.base_object)

            return True

        return False
