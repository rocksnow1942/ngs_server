import time,os,shutil,json
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pptx import Presentation
from pathlib import PureWindowsPath
from comtypes import client
from ctypes import Structure, windll, c_uint, sizeof, byref
import threading


source_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Projects"
target_folder =  r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap"
log_file =  r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap\log.json"

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



def write_file_log(filename,content,writemode='a'):
    with open(filename,writemode) as f:
        f.write(content)


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
        ppt=Presentation(file)
        revision = ppt.core_properties.revision
        result.append(revision)
    return result


logfile = '/Users/hui/Desktop/test/filelog.txt'

class FileLogger():
    def __init__(self,source_folder="",target_foler="",log_file=""):
        self.data = {}
        self.revisions = {}
        self.source_folder=source_folder
        self.target_foler=target_foler
        self.log_file=log_file
        self.init_revision(self.source_folder)

    def mirror_path(self,path):
        sf = PureWindowsPath(self.source_folder)
        tf = PureWindowsPath(self.target_foler)
        rf = PureWindowsPath(path).relative_to(sf)
        return str(tf/(rf.parent/rf.stem)).strip()

    def __repr__(self):
        result = ""
        for k,i in self.data.items():
            result+=(f"{k}=>{i}\n")
        return f"<FileLogger>\n{result}"

    def init_revision(self,path):
        files = glob_pptx(path)
        revisions = get_revision(*files)
        new=dict(zip(files,revisions))
        with open(self.log_file,'rt') as f:
            self.revisions = json.load(f)
        for k,i in new.items():
            if self.revisions.get(k,None)!=i:
                self.data[k]='create'
        for k in self.revisions.keys()-new.keys():
            self.data[k]='delete'
        print('init reveison done.')

    def create(self,file):
        self.data[file]='create'
    def delete(self,file):
        self.data[file]='delete'
    def move(self,src,dst):
        self.data[src]='delete'
        self.data[dst]='create'
    def status(self,file):
        return self.data.get(file,None)
    @property
    def files(self):
        yield from self.data.items()
    @property
    def deleted(self):
        for k,i in self.data.items():
            if i == 'delete':
                yield k
    @property
    def created(self):
        for k,i in self.data.items():
            if i == 'create':
                yield k

    def sync_snap(self):
        unresolved = {}
        for file in self.created:
            c_rev=get_revision(file)[0]
            if c_rev!=self.revisions.get(file,None):
                try:
                    make_snapshot(file,self.mirror_path(file))
                    self.revisions[file]=c_rev
                    print('{} Making snapshot: {}'.format(threading.get_ident() ,self.mirror_path(file)))
                except Exception as e:
                    print('Failed Making Snapshot {} reason: {}'.format(self.mirror_path(file),e))
                    unresolved[file]=str(e)

        for file in self.deleted:
            try:
                shutil.rmtree(self.mirror_path(file))
                print('{} Delete Folder: {}'.format(threading.get_ident() ,self.mirror_path(file)))
                self.revisions.pop(file,None)
            except FileNotFoundError as e:
                print(e)

        self.data = {}
        with open(self.log_file,'wt') as f:
            json.dump(self.revisions,f,indent=2)
        with open(self.log_file+'_errors','rt') as f:
            unresolved.update(json.load(f))
        with open(self.log_file+'_errors','wt') as f:
            json.dump(unresolved,f,indent=2)



class PPTX_Handler(PatternMatchingEventHandler):
    def __init__(self,logger):
        super().__init__(patterns=["*.pptx",],ignore_patterns=["*~$*","*Conflict*"],
        ignore_directories=False,case_sensitive=True)
        self.logger=logger

    def on_created(self,event):
        print(f"Create {event.src_path}")
        self.logger.create(event.src_path)



    def on_deleted(self,event):
        print(f"Delete {event.src_path}")
        self.logger.delete(event.src_path)

    def on_modified(self,event):
        print(f"Modify {event.src_path}")
        self.logger.create(event.src_path)

    def on_moved(self,event):
        print(f"Rename {event.src_path} to {event.dest_path}")
        if PureWindowsPath(event.src_path).suffix == ".pptx":
            self.logger.delete(event.src_path)
        if PureWindowsPath(event.dest_path).suffix == ".pptx":
            self.logger.create(event.dest_path)



my_observer = Observer()
logger = FileLogger(source_folder=source_folder,target_foler=target_folder,log_file=log_file)
my_observer.schedule(PPTX_Handler(logger=logger), source_folder, recursive=True)
my_observer.start()
print('monitor started.')
try:
    while True:
        time.sleep(60)
        if get_idle_duration()>300:
            logger.sync_snap()

except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()
