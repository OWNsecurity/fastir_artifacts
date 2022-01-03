import os
import winreg

from .wmi import wmi_query
from fastir.common.variables import HostVariables


def reg(hive, key, value, alternative_value=None):
    k = winreg.OpenKey(hive, key, 0, winreg.KEY_READ|winreg.KEY_WOW64_64KEY)

    try:
        v = winreg.QueryValueEx(k, value)
    except FileNotFoundError:
        if not alternative_value:
            raise

        v = winreg.QueryValueEx(k, alternative_value)

    winreg.CloseKey(k)

    return v[0]


class WindowsHostVariables(HostVariables):

    def _get_local_users(self):
        return wmi_query('SELECT Name, SID FROM Win32_Account WHERE SidType = 1 AND LocalAccount = True')

    def _get_extra_sids(self):
        sids = set()

        k1 = winreg.HKEY_USERS

        i = 0
        while 1:
            try:
                sid = winreg.EnumKey(k1, i)

                if '_Classes' not in sid and sid != '.DEFAULT':
                    sids.add(sid)

                i += 1
            except WindowsError:
                break

        return sids

    def _get_user_profiles(self):
        profiles = set()

        k1 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList')

        i = 0
        while 1:
            try:
                sid = winreg.EnumKey(k1, i)
                k2 = winreg.OpenKey(k1, sid)
                v = winreg.QueryValueEx(k2, 'ProfileImagePath')
                winreg.CloseKey(k2)

                profiles.add(v[0])

                i += 1
            except WindowsError:
                break

        winreg.CloseKey(k1)

        return profiles

    def init_variables(self):
        systemroot = reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'Software\Microsoft\Windows NT\CurrentVersion',
            'SystemRoot')

        self.add_variable('%systemroot%', systemroot)
        self.add_variable('%%environ_systemroot%%', systemroot)
        self.add_variable('%systemdrive%', systemroot[:2])
        self.add_variable('%%environ_systemdrive%%', systemroot[:2])

        self.add_variable('%%environ_windir%%', reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'System\CurrentControlSet\Control\Session Manager\Environment',
            'windir'))

        self.add_variable('%%environ_allusersappdata%%', reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'Software\Microsoft\Windows NT\CurrentVersion\ProfileList',
            'ProgramData'))

        self.add_variable('%%environ_programfiles%%', reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'Software\Microsoft\Windows\CurrentVersion',
            'ProgramFilesDir'))

        self.add_variable('%%environ_programfiles%%', reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'Software\Microsoft\Windows\CurrentVersion',
            'ProgramFilesDir'))

        self.add_variable('%%environ_programfilesx86%%', reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'Software\Microsoft\Windows\CurrentVersion',
            'ProgramFilesDir (x86)', 'ProgramFilesDir'))

        self.add_variable('%%environ_allusersprofile%%', reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'Software\Microsoft\Windows NT\CurrentVersion\ProfileList',
            'AllUsersProfile', 'ProgramData'))

        self.add_variable('%%users.localappdata%%', reg(
            winreg.HKEY_USERS,
            r'.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders',
            'Local AppData'))

        self.add_variable('%%users.appdata%%', reg(
            winreg.HKEY_USERS,
            r'.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders',
            'AppData'))

        self.add_variable('%%users.temp%%', reg(
            winreg.HKEY_USERS,
            r'.DEFAULT\Environment',
            'TEMP'))

        self.add_variable('%%users.localappdata_low%%', os.path.join('%USERPROFILE%', reg(
            winreg.HKEY_LOCAL_MACHINE,
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions\{A520A1A4-1780-4FF6-BD18-167343C5AF16}',
            'RelativePath')))

        user_profiles = self._get_user_profiles()
        self.add_variable('%USERPROFILE%', user_profiles)
        self.add_variable('%%users.homedir%%', user_profiles)
        self.add_variable('%%users.userprofile%%', user_profiles)

        users = self._get_local_users()
        extra_sids = self._get_extra_sids()
        self.add_variable('%%users.username%%', set([user['Name'] for user in users]))
        self.add_variable('%%users.sid%%', set([user['SID'] for user in users] + [sid for sid in extra_sids]))
