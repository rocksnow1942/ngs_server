import time
import os
import shutil
import json
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pptx import Presentation
from pathlib import PureWindowsPath
from comtypes import client
from ctypes import Structure, windll, c_uint, sizeof, byref
from datetime import datetime
import gc
import requests

#C:\Users\aptitude\Anaconda3\pythonw.exe "C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor.py"

source_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Projects"
target_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap"
log_file = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap\log.json"
running_log = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor\monitor_log.txt"
printscreen = False
post_url = 'http://192.168.86.200/pptmonitor_port'


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
    del powerpoint
    return None


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
    def __init__(self, source_folder="", target_foler="", log_file="", running_log=""):
        self.data = {}
        self.revisions = {}
        self.source_folder = source_folder
        self.target_foler = target_foler
        self.log_file = log_file
        self.running_log = running_log

    def write_log(self, content):
        if printscreen:
            print(content)
        with open(self.running_log, 'a') as f:
            f.write(f"{self.time} - " + content+'\n')
        return 0

    def post(self, msg):
        requests.post(url=post_url, json={'time': self.time, 'msg': msg})

    @property
    def time(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
            path = self.source_folder
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
        return 0

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
                    make_snapshot(file, self.mirror_path(file))
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
                self.write_log('Success: Delete Folder: {}'.format(
                    self.mirror_path(file)))
                self.revisions.pop(file, None)
            except FileNotFoundError as e:
                self.write_log(
                    f"Error: Delete Folder {self.mirror_path(file)}; \nReason: {e}")
        self.data = {}
        with open(self.log_file, 'wt') as f:
            json.dump(self.revisions, f, indent=2)
        with open(self.log_file+'_errors', 'rt') as f:
            unresolved.update(json.load(f))
        with open(self.log_file+'_errors', 'wt') as f:
            json.dump(unresolved, f, indent=2)
        return 0


class PPTX_Handler(PatternMatchingEventHandler):
    def __init__(self, logger):
        super().__init__(patterns=["*.pptx", ], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger

    def write_log(self, content):
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
        self.write_log(
            f"Watchdog: Rename {event.src_path} to {event.dest_path}")
        if PureWindowsPath(event.src_path).suffix == ".pptx":
            self.logger.delete(event.src_path)
        if PureWindowsPath(event.dest_path).suffix == ".pptx":
            self.logger.create(event.dest_path)


def main():
    my_observer = Observer()
    logger = FileLogger(source_folder=source_folder,
                        target_foler=target_folder, log_file=log_file, running_log=running_log)
    logger.write_log('***File Monitor Lanunch')
    logger.post("I'm running.")
    logger.init_revision()
    my_observer.schedule(PPTX_Handler(logger=logger),
                         source_folder, recursive=True)
    my_observer.start()
    logger.write_log('***File Monitor Started')
    gc.collect()
    while True:
        time.sleep(60)
        try:            
            if get_idle_duration() > 120:
                logger.sync_snap()
            logger.post("PPTmonitor is running.")  # post signal every 1minutes
        except Exception as e:
            logger.write_log(f'Logging Error: {e}')
        gc.collect()

if __name__ == '__main__':
    main()
