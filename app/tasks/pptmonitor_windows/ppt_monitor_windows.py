import time
import os
import shutil
import json
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pptx import Presentation
from pathlib import PureWindowsPath
from comtypes import client
from datetime import datetime
import gc
import requests
import logging
from logging.handlers import RotatingFileHandler
import win32api
import psutil
#C:\Users\aptitude\Anaconda3\pythonw.exe "C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor.py"

source_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Projects"
target_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap"
log_file = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap\log.json"
running_log = r"C:\Users\aptitude\Desktop\monitorlogs\monitor_log.txt"

post_url = 'http://192.168.86.200/pptmonitor_port'


class LASTINPUTINFO():
    def __init__(self):
        self.update()

    def update(self):
        self.lastinput = win32api.GetLastInputInfo()
        self.time = time.time()

    def __call__(self, *args, **kwargs):
        recentinput = win32api.GetLastInputInfo()
        if recentinput == self.lastinput:
            dt = time.time()-self.time
        else:
            dt = (recentinput - self.lastinput) / 1000
            dt = time.time()-self.time - dt
            self.update()
        return dt


get_idle_duration = LASTINPUTINFO()


def delete_folder_content(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def make_snapshot(source, target):
    powerpoint = client.CreateObject('Powerpoint.Application')
    powerpoint.Presentations.Open(source)
    powerpoint.WindowState = 2
    if not os.path.isdir(target.strip()):
        os.makedirs(target.strip())
    delete_folder_content(target.strip())
    powerpoint.ActivePresentation.Export(target.strip()+'.pptx', 'PNG')
    powerpoint.ActivePresentation.Close()
    powerpoint.Quit()
    return None


def checkIfProcessRunning(processName):
    '''
    Check if there is any running process that contains the given name processName.
    '''
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def close_office(logger):
    try:
        if checkIfProcessRunning('WINWORD.exe'):
            os.system("TASKKILL /F /IM WINWORD.exe")
            logger.debug("close word attempted.")
        if checkIfProcessRunning('EXCEL.exe'):
            os.system("TASKKILL /F /IM EXCEL.exe")
            logger.debug("close excel attempted.")
        if checkIfProcessRunning("chrome.exe"):
            os.system("TASKKILL /F /IM chrome.exe")
            logger.debug("close chrome attempted.")

    except Exception as e:
        logger.error("close_office ERROR: "+str(e))


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
    def __init__(self, source_folder="", target_foler="", log_file="", running_log="", loglevel='INFO'):
        self.data = {}
        self.revisions = {}
        self.source_folder = source_folder
        self.target_foler = target_foler
        self.log_file = log_file
        # self.running_log = running_log
        # define rotating file handler
        level = getattr(logging, loglevel.upper(), 20)
        logger = logging.getLogger('Monitor')
        logger.setLevel(level)
        fh = RotatingFileHandler(running_log, maxBytes=102400, backupCount=2)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y/%m/%d %I:%M:%S %p'
        ))
        logger.addHandler(fh)
        self.logger = logger

        for i in ['debug', 'info', 'warning', 'error', 'critical']:
            setattr(self, i, getattr(self.logger, i))

    def post(self, msg):
        try:
            a = requests.post(url=post_url, json={
                'time': self.time, 'msg': msg}, timeout=(10, 30))
            self.debug(f'Post answer is : {a.text}')
        except Exception as e:
            self.debug(f'Post failed: {e}')

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
            self.info('Success: Init Revision Done.')
        except Exception as e:
            self.error(f'Error: {e}')
        return

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
                    self.info('Making snapshot {}'.format(file))
                except Exception as e:
                    self.error('Making Snapshot {} Reason: {}'.format(
                        file, e))
                    unresolved[file] = str(e)

        for file in self.deleted:
            try:
                shutil.rmtree(self.mirror_path(file))
                self.info('Delete Folder: {}'.format(file))
                self.revisions.pop(file, None)
            except FileNotFoundError as e:
                self.revisions.pop(file, None)
                self.error(
                    f"Delete Folder <{file}> Reason: {e}")
        self.data = {}
        with open(self.log_file, 'wt') as f:
            json.dump(self.revisions, f, indent=2)
        with open(self.log_file+'_errors', 'rt') as f:
            unresolved.update(json.load(f))
        with open(self.log_file+'_errors', 'wt') as f:
            json.dump(unresolved, f, indent=2)
        return


class PPTX_Handler(PatternMatchingEventHandler):
    def __init__(self, logger):
        super().__init__(patterns=["*.pptx", ], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger
        self.info = logger.info

    def on_created(self, event):
        self.info(f"Watchdog: Create {event.src_path}")
        self.logger.create(event.src_path)

    def on_deleted(self, event):
        self.info(f"Watchdog: Delete {event.src_path}")
        self.logger.delete(event.src_path)

    def on_modified(self, event):
        self.info(f"Watchdog: Modify {event.src_path}")
        self.logger.create(event.src_path)

    def on_moved(self, event):
        self.info(
            f"Watchdog: Rename {event.src_path} to {event.dest_path}")
        if PureWindowsPath(event.src_path).suffix == ".pptx":
            self.logger.delete(event.src_path)
        if PureWindowsPath(event.dest_path).suffix == ".pptx":
            self.logger.create(event.dest_path)


def main(loglevel='INFO'):
    my_observer = Observer()
    logger = FileLogger(source_folder=source_folder,
                        target_foler=target_folder, log_file=log_file, running_log=running_log, loglevel=loglevel)
    logger.info('File Monitor Lanunch')
    logger.post("PPTmonitor is running.")
    logger.init_revision()
    my_observer.schedule(PPTX_Handler(logger=logger),
                         source_folder, recursive=True)
    my_observer.start()
    logger.info('File Monitor Started')
    gc.collect()
    while True:
        try:
            time.sleep(90)
            try:
                logger.debug('Idle duration {}'.format(get_idle_duration()))
                if get_idle_duration() > 120:
                    logger.sync_snap()
                    logger.debug('Sync attempt.')
                # post signal every 1 minutes
                if get_idle_duration() > 900:
                    close_office(logger)
                logger.post("PPTmonitor is running.")
            except Exception as e:
                logger.error(f'PPTmonitor make snap shot loop: {e}')
            gc.collect()
        except Exception as e:
            logger.critical(f'PPTmonitor Loop Break: {e}')
            time.sleep(160)


if __name__ == '__main__':
    main(loglevel='INFO')
