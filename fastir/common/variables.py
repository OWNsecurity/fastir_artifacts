import re

from .logging import logger


class HostVariables:
    def __init__(self):
        self._variables = []

        self.init_variables()
        self.resolve_variables()

    def init_variables(self):
        raise NotImplementedError

    def resolve_variables(self):
        for variable in self._variables:
            values = variable['value']

            if not isinstance(variable['value'], set):
                values = set([values])

            resolved_values = set()

            for value in values:
                resolved_values.update(self.substitute(value))

            variable['value'] = resolved_values

    def add_variable(self, name, value):
        self._variables.append({
            'name': name,
            're': re.compile(re.escape(name), re.IGNORECASE),
            'value': value
        })

    def _substitute_value(self, original_value, variable_re, variable_value):
        new_value, subs = variable_re.subn(variable_value.replace('\\', r'\\'), original_value)

        if subs:
            return self.substitute(new_value)
        else:
            return set()

    def substitute(self, value):
        values = set()

        if value.count('%') < 2:
            values.add(value)
        else:
            for variable in self._variables:
                if isinstance(variable['value'], set):
                    for variable_value in variable['value']:
                        values.update(self._substitute_value(value, variable['re'], variable_value))
                else:
                    values.update(self._substitute_value(value, variable['re'], variable['value']))

            if not values:
                logger.warning(f"Value '{value}' contains unsupported variables")
                # values.add(value)

        return values
