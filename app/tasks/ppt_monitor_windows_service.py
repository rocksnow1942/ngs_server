import time,os,shutil,json
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pptx import Presentation
from pathlib import PureWindowsPath
from comtypes import client
from ctypes import Structure, windll, c_uint, sizeof, byref
from datetime import datetime
import sys
# python path on windows: C:\Users\aptitude\Anaconda3\python.exe

import win32serviceutil
import win32service
import win32event
import servicemanager
import configparser
import inspect

# import logging

# location :
# C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor_service.py
# To install service, run python  <file.py> install / update / start / stop / remove.
# problem with the current script is that th windows machine memory too small, and cause a "memory not enough error"
#


# The service didn't start run on local machine due to an import DLL error;
# added all the following path form user path to System path.
# C:\Users\aptitude\Anaconda3\Scripts
# C:\Users\aptitude\Anaconda3\DLLs
# C:\Users\aptitude\Anaconda3\Lib\site-packages
# C:\Users\aptitude\Anaconda3\bin
# C:\Users\aptitude\Anaconda3\Library\bin
# C:\Users\aptitude\Anaconda3\Library\usr\bin
# C:\Users\aptitude\Anaconda3\Library\mingw-w64\bin
# C:\Windows\system32
# C:\Windows\System32\Wbem
# C:\Windows\System32\OpenSSH\
# C:\Windows\System32\WindowsPowerShell\v1.0\
# C:\Users\aptitude\AppData\Local\Microsoft\WindowsApps


source_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Projects"
target_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap"
log_file = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap\log.json"
running_log = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap\windows_ppt_watcher_log.txt"
printscreen = False


class LASTINPUTINFO(Structure):
    _fields_ = [
        ('cbSize', c_uint),
        ('dwTime', c_uint),
    ]

def get_idle_duration():
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0

def make_snapshot(source, target):
    powerpoint = client.CreateObject('Powerpoint.Application')
    powerpoint.Presentations.Open(source)
    powerpoint.WindowState = 2
    if not os.path.isdir(target):
        os.makedirs(target.strip())
    powerpoint.ActivePresentation.Export(target.strip()+'.pptx', 'PNG')
    powerpoint.ActivePresentation.Close()
    powerpoint.Quit()

def glob_pptx(path):
    result = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".pptx") and ('conflict' not in file.lower()) and (not file.startswith('~$')):
                  result.append(os.path.join(root, file))
    return result


def get_revision(*files):
    result = []
    for file in files:
        try:
            ppt = Presentation(file)
            revision = ppt.core_properties.revision
        except:
            revision = 0
        result.append(revision)
    return result

class FileLogger():
    def __init__(self, source_folder="", target_foler="", log_file="",running_log=""):
        self.data = {}
        self.revisions = {}
        self.source_folder = source_folder
        self.target_foler = target_foler
        self.log_file = log_file
        self.running_log = running_log

    def write_log(self,content):
        if printscreen:
            print(content)
        with open(self.running_log,'a') as f:
            f.write(f"{self.time} - " +content+'\n')

    @property
    def time(self):
        return datetime.now().strftime('%y/%m/%d %H:%M:%S')

    def mirror_path(self, path):
        sf = PureWindowsPath(self.source_folder)
        tf = PureWindowsPath(self.target_foler)
        rf = PureWindowsPath(path).relative_to(sf)
        return str(tf/(rf.parent/rf.stem)).strip()

    def __repr__(self):
        result = ""
        for k, i in self.data.items():
            result += (f"{k}=>{i}\n")
        return f"<FileLogger>\n{result}"

    def init_revision(self):
        try:
            path=self.source_folder
            files = glob_pptx(path)
            revisions = get_revision(*files)
            new = dict(zip(files, revisions))
            with open(self.log_file, 'rt') as f:
                self.revisions = json.load(f)
            for k, i in new.items():
                if self.revisions.get(k, None) != i:
                    self.data[k] = 'create'
            for k in self.revisions.keys()-new.keys():
                self.data[k] = 'delete'
            self.write_log('Success: Init Revision Done.')
        except Exception as e:
            self.write_log(f'Error: Init Error \nReason:{e}')

    def create(self, file):
        self.data[file] = 'create'

    def delete(self, file):
        self.data[file] = 'delete'

    def move(self, src, dst):
        self.data[src] = 'delete'
        self.data[dst] = 'create'

    def status(self, file):
        return self.data.get(file, None)

    @property
    def files(self):
        yield from self.data.items()

    @property
    def deleted(self):
        for k, i in self.data.items():
            if i == 'delete':
                yield k

    @property
    def created(self):
        for k, i in self.data.items():
            if i == 'create':
                yield k

    def sync_snap(self):
        unresolved = {}
        for file in self.created:
            c_rev = get_revision(file)[0]
            if c_rev != self.revisions.get(file, None):
                try:
                    # make_snapshot(file, self.mirror_path(file))

                    source, target = file, self.mirror_path(file)
                    powerpoint = client.CreateObject('Powerpoint.Application')
                    self.write_log('Success: create powerpoint')
                    powerpoint.Presentations.Open(source)
                    self.write_log('Success: open powerpoint')
                    powerpoint.WindowState = 2
                    if not os.path.isdir(target):
                        os.makedirs(target.strip())
                    powerpoint.ActivePresentation.Export(target.strip()+'.pptx', 'PNG')
                    powerpoint.ActivePresentation.Close()
                    powerpoint.Quit()


                    self.revisions[file] = c_rev
                    self.write_log('Success: Making snapshot {}'.format(
                         self.mirror_path(file)))
                except Exception as e:
                    self.write_log('Error: Making Snapshot {}; \nReason: {}'.format(
                        self.mirror_path(file), e))
                    unresolved[file] = str(e)

        for file in self.deleted:
            try:
                shutil.rmtree(self.mirror_path(file))
                self.write_log('Success: Delete Folder: {}'.format(self.mirror_path(file)))
                self.revisions.pop(file, None)
            except FileNotFoundError as e:
                self.write_log(f"Error: Delete Folder {self.mirror_path(file)}; \nReason: {e}")
        self.data = {}
        with open(self.log_file, 'wt') as f:
            json.dump(self.revisions, f, indent=2)
        with open(self.log_file+'_errors', 'rt') as f:
            unresolved.update(json.load(f))
        with open(self.log_file+'_errors', 'wt') as f:
            json.dump(unresolved, f, indent=2)


class PPTX_Handler(PatternMatchingEventHandler):
    def __init__(self, logger):
        super().__init__(patterns=["*.pptx", ], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger

    def write_log(self,content):
        self.logger.write_log(content)

    def on_created(self, event):
        self.write_log(f"Watchdog: Create {event.src_path}")
        self.logger.create(event.src_path)

    def on_deleted(self, event):
        self.write_log(f"Watchdog: Delete {event.src_path}")
        self.logger.delete(event.src_path)

    def on_modified(self, event):
        self.write_log(f"Watchdog: Modify {event.src_path}")
        self.logger.create(event.src_path)

    def on_moved(self, event):
        self.write_log(f"Watchdog: Rename {event.src_path} to {event.dest_path}")
        if PureWindowsPath(event.src_path).suffix == ".pptx":
            self.logger.delete(event.src_path)
        if PureWindowsPath(event.dest_path).suffix == ".pptx":
            self.logger.create(event.dest_path)



#
# logging.basicConfig(
#     filename = r'C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\windows_ppt_monitor.log',
#     level = logging.DEBUG,
#     format = '[PPTmonitorService] %(levelname)-7.7s %(message)s'
# )


class PPTmonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PPTmonitorService"
    _svc_display_name_ = "PPTmonitorService"
    # _config = configparser.ConfigParser()
    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.stop_event = win32event.CreateEvent(None,0,0,None)
        # socket.setdefaulttimeout(60)
        # self.stop_requested = False



    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        # logging.info('Stopping service ...')
        # self.stop_requested = True

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_,'')
        )
        # logging.info('Service starting service ...')
        self.main()

    def main(self):
        # logging.info(' service main() Starting Service ppt monitor ')
        my_observer = Observer()
        logger = FileLogger(source_folder=source_folder,
                            target_foler=target_folder, log_file=log_file,running_log=running_log)
        logger.write_log('***File Monitor Lanunch')
        logger.init_revision()
        my_observer.schedule(PPTX_Handler(logger=logger),
                             source_folder, recursive=True)
        my_observer.start()
        logger.write_log('***File Monitor Started')
        rc = None
        while rc != win32event.WAIT_OBJECT_0:
            time.sleep(10)
            # if get_idle_duration() > 120:
            logger.sync_snap()
            logger.write_log('syncing done')
            # hang for 1 minute or until service is stopped - whichever comes first
            rc = win32event.WaitForSingleObject(self.stop_event, (1 * 10 * 1000))




if __name__ == '__main__':
    # if len(sys.argv) == 1:
    #     servicemanager.Initialize()
    #     servicemanager.PrepareToHostSingle(PPTmonitorService)
    #     servicemanager.StartServiceCtrlDispatcher()
    # else:
    win32serviceutil.HandleCommandLine(PPTmonitorService)

#
# def _main():
#
#     _configure_logging()
#
#     if len(sys.argv) == 1 and \
#             sys.argv[0].endswith('.exe') and \
#             not sys.argv[0].endswith(r'win32\PythonService.exe'):
#         # invoked as non-pywin32-PythonService.exe executable without
#         # arguments
#
#         # We assume here that we were invoked by the Windows Service
#         # Control Manager (SCM) as a PyInstaller executable in order to
#         # start our service.
#
#         # Initialize the service manager and start our service.
#         servicemanager.Initialize()
#         servicemanager.PrepareToHostSingle(ExampleService)
#         servicemanager.StartServiceCtrlDispatcher()
#
#     else:
#         # invoked with arguments, or without arguments as a regular
#         # Python script
#
#         # We support a "help" command that isn't supported by
#         # `win32serviceutil.HandleCommandLine` so there's a way for
#         # users who run this script from a PyInstaller executable to see
#         # help. `win32serviceutil.HandleCommandLine` shows help when
#         # invoked with no arguments, but without the following that would
#         # never happen when this script is run from a PyInstaller
#         # executable since for that case no-argument invocation is handled
#         # by the `if` block above.
#         if len(sys.argv) == 2 and sys.argv[1] == 'help':
#             sys.argv = sys.argv[:1]
#
#         win32serviceutil.HandleCommandLine(ExampleService)

#
# if __name__ == '__main__':
#     _main()
