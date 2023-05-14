import datetime
import win32api
import win32file

def get_external_drive():
    drives = []
    for drive in win32api.GetLogicalDriveStrings().split('\000'):
        if drive and win32file.GetDriveType(drive) == 2:
            drives.append(drive[:2])
    return drives

def big_size_truncate(size):
    if size >=2**50:
        return str(round(size/(2**50),1)) + ' PB'
    if size >=2**40:
        return str(round(size/(2**40),1)) + ' TB'
    if size >=2**30:
        return str(round(size/(2**30),1)) + ' GB'
    if size >=2**20:
        return str(round(size/(2**20),1)) + ' MB'
    return str(round(size/(2**10),1)) + ' KB'

def findCenterPoint(root, app_width, app_height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width / 2) - (app_width / 2)
    y = (screen_height / 2) - (app_height / 2)
    return x, y

def getFileName(path):
    for i in range(len(path)-1, 0-1, -1):
        if path[i] == '\\':
            return path[i+1::]
    return 0

class FileTree:
    def __init__(self, Tree):
        self.currentFolder = Tree

    def get_file(self, path):
        ls = self.path_to_list(path)
        for name in ls[:-1]:
            self.currentFolder = self.search_file(name)['lsFileFolder']

        return self.search_file(ls[-1])

    def search_file(self, filename):
        for file in self.currentFolder:
            if file["Name"] == filename:
                return file

    def path_to_list(self, path):
        i = 1
        ls = []
        for j in range(1, len(path)):
            if path[j] == '\\':
                ls.append(path[i:j])
                i = j+1
        ls.append(path[i::])
        return ls
