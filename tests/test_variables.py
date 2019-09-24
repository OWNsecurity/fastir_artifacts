from fastir.common.variables import HostVariables


class HostVariablesForTests(HostVariables):

    def init_variables(self):
        self.add_variable('%%users.homedir%%', set([
            '%%USERDIR%%',
            '/tmp/root'
        ]))
        self.add_variable('%%USERDIR%%', '/home/user')


def test_variables():
    variables = HostVariablesForTests()

    assert variables.substitute('%%users.homedir%%/test') == set([
        '/home/user/test', '/tmp/root/test'
    ])
    assert variables.substitute('test%%USERDIR%%test') == set([
        'test/home/usertest'
    ])
    assert variables.substitute('i_dont_have_variables') == set([
        'i_dont_have_variables'
    ])
    assert variables.substitute('i_contain_%%unsupported%%_variables') == set([
        'i_contain_%%unsupported%%_variables'
    ])
