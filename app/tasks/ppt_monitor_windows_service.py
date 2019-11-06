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
import psutil
import subprocess

# 
r"""
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
"""
running_log = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap\windows_ppt_watcher_service.txt" 
monitor_script = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor.py"


class FileLogger():
    def __init__(self, running_log=""):
        self.running_log = running_log

    @property
    def time(self):
        return datetime.now().strftime('%y/%m/%d %H:%M:%S')

    def write_log(self, content):
        with open(self.running_log, 'a') as f:
            f.write(f"{self.time} - " + content+'\n')

class PPTmonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PPTmonitorService"
    _svc_display_name_ = "PPTmonitorService"
    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.stop_event = win32event.CreateEvent(None,0,0,None)
       
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
    
    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_,'')
        )
        self.main()

    def start_script(self):
        result = subprocess.Popen(
            [sys.executable, monitor_script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return result.pid


    def main(self):
        rc = None
        logger = FileLogger(running_log=running_log)
        logger.write_log('Monitor Service Started.')
        monitorpid = self.start_script()
        logger.write_log(f'Started ppt monitor script PID= [{monitorpid}].')
        while rc != win32event.WAIT_OBJECT_0:
            pids = [p.pid for p in psutil.process_iter()]
            if monitorpid not in pids: 
                logger.write_log(f'Detected PPT monitor script stopped.')
                monitorpid = None
                try:
                    monitorpid = self.start_script()
                    logger.write_log(f'Re-Started ppt monitor PID= [{monitorpid}].')
                except Exception as e:
                    logger.write_log(f'Start ppt monitor failed. Reason: {e}')
            time.sleep(30) # check every 30 seconds if the monitor service is running.
            rc = win32event.WaitForSingleObject(self.stop_event, (1 * 10 * 1000))
        logger.write_log('Monitor Service Stopped.')

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
