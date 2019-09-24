import pwd


from fastir.common.variables import HostVariables


class UnixHostVariables(HostVariables):

    def init_variables(self):
        userprofiles = set()

        for pwdent in pwd.getpwall():
            userprofiles.add(pwdent.pw_dir)

        self.add_variable('%%users.homedir%%', userprofiles)
