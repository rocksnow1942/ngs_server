from app import db
from app import create_app
import json
from itertools import islice
from app.utils.ngs_util import create_folder_if_not_exist,lev_distance

from app.utils.analysis import DataReader

from pptx import Presentation
import os,time
import shutil
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pptx import Presentation
from pathlib import PurePath
import threading


source_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Projects"
target_folder = r"C:\Users\aptitude\Aptitude-Cloud\R&D Backup\Plojo backup\Project_Slide_snap"


app = create_app()
app.app_context().push()


class PPTX_Handler(PatternMatchingEventHandler):
    def __init__(self, logger):
        super().__init__(patterns=["*.pptx", ], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger

    def on_created(self, event):
        print(f"Create {event.src_path}")
        
    def on_deleted(self, event):
        print(f"Delete {event.src_path}")
       

    def on_modified(self, event):
        print(f"Modify {event.src_path}")
       
    def on_moved(self, event):
        print(f"Rename {event.src_path} to {event.dest_path}")
       


if __name__ == "__main__":

    my_observer = Observer()
    
    my_observer.schedule(PPTX_Handler(logger=None),
                        source_folder, recursive=True)
    my_observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()
