import hashlib
import sys
from pathlib import PurePath, Path
import os,time
from datetime import datetime
# filepath = os.path.dirname(__file__)
filepath = PurePath(__file__).parent.parent.parent
sys.path.append(str(filepath))
from dateutil import parser
from app import db
from app import create_app
import json
from itertools import islice
from app.utils.ngs_util import create_folder_if_not_exist,lev_distance

from pptx import Presentation
import shutil
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pptx import Presentation
from app.models import Slide, PPT, Project


def glob_pptx(path):
    result = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".pptx") and ('conflict' not in file.lower()) and (not file.startswith('~$')):
                  result.append(os.path.join(root, file))
    return result

class PPT_Indexer():
    def __init__(self, log_file=""):
        app = create_app(keeplog=False)
        app.app_context().push()
        source_folder = app.config['PPT_SOURCE_FOLDER']
        target_folder = app.config['PPT_TARGET_FOLDER']
        self.app=app
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.log_file = log_file

    def write_log(self,content):
        with open(self.log_file,'a') as f:
            f.write(content+'\n')

    def mirror_path(self, path):
        sf = PurePath(self.source_folder)
        # tf = PurePath(self.target_folder)
        rf = PurePath(path).relative_to(sf)
        return str(rf.parent/rf.stem).strip()

    def get_project_name(self,filepath):
        return PurePath(filepath).relative_to(self.source_folder).parts[0]

    def get_PPT_name(self,filepath):
        return PurePath(filepath).stem.strip()

    @staticmethod
    def get_md5(file):
        with open(file, 'rb') as afile:
            hasher = hashlib.md5()
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest()

    @staticmethod
    def get_revision(file):
        ppt = Presentation(file)
        return ppt.core_properties.revision
    @property
    def time(self):
        return datetime.now().strftime('%y/%m/%d %H:%M:%S')

    def create(self, file):
        with self.app.app_context():
            if self.create_by_path(file):
                self.write_log(f"{self.time} Update by path {file}")
                return None
            elif self.create_by_md5((file)):
                self.write_log(f"{self.time} Update by md5 {file}")
                return None
            else:
                self.create_new(file)
                self.write_log(f"{self.time} Create new {file}")

    def create_by_path(self,file):
        path = self.mirror_path(file)
        ppt = PPT.query.filter_by(path=path).first()
        if ppt and (ppt.project_id == None):
            project = self.create_project(file)
            ppt.project = project
            ppt.md5=self.get_md5(file)
            ppt.revision = self.get_revision(file)
            ppt=self.sync_slides(ppt,file)
            ppt.date = datetime.now()
            db.session.commit()
            return True
        return False

    def parse_ppt(self,file):
        ppt=Presentation(file)
        slides = []
        for page, slide in enumerate(ppt.slides):
            temp = []
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    temp.append((shape.text, shape.top))
            if not temp:
                temp.append(("No Title", 0))
            temp.sort(key=lambda x: x[1])
            title = temp[0][0]
            date = self.parse_date(title)
            if date==None:
                date = slides[-1]['date'] if slides else datetime(2011,1,1,1,1)
            slides.append(dict(page=page+1,
                               title=title, date=date, body="\n".join(i[0] for i in temp[1:]) ))
        return slides

    def parse_date(self,title):
        date = ''
        for l in title:
            if l.isalpha():
                break
            else:
                date += l
        date=date.strip()
        for i in range(len(date),3,-1):
            totry = date[:i]
            try:
                _date = parser.parse(totry)
                return _date
            except:
                continue
        return None

    def sync_slides(self,ppt,file):
        slides = self.parse_ppt(file)
        oldslides=ppt.slides
        cur_slides = []
        for s in slides:
            slide_collection = Slide.query.filter_by(ppt_id=ppt.id,title=s['title'],body=s['body']).order_by(Slide.page).all()
            found = False
            if slide_collection: 
                for slide in slide_collection:
                    if slide not in cur_slides:
                        slide.ppt=ppt
                        slide.page = s['page']
                        slide.date=s['date']
                        found = True
                        break
            if not found:
                slide = Slide(ppt_id=ppt.id, **s)
                db.session.add(slide)
            cur_slides.append(slide)
        for slide in (set(oldslides)-set(cur_slides)):
            if slide.note or slide.tag:
                slide.ppt_id=None
            else:
                db.session.delete(slide)
        db.session.commit()
        return ppt

    def create_new(self,file):
        name = self.get_PPT_name(file)
        path = self.mirror_path(file)
        md5 = self.get_md5(file)
        project = self.create_project(file)
        revision = self.get_revision(file)      
        try:
            ppt = PPT(name=name,path=path,project_id=project.id,md5=md5,revision=revision)
            db.session.add(ppt)
            db.session.commit()
            self.sync_slides(ppt,file)
            db.session.commit()
        except Exception as e:
            self.write_log(f"{self.time} - Create New error:{e}")

    def create_project(self,file):
        projectname = self.get_project_name(file)
        project = Project.query.filter_by(name=projectname).first()
        if not project:
            project=Project(name=projectname)
            db.session.add(project)
        project.date=datetime.now()
        db.session.commit()
        return project

    def create_by_md5(self,file):
        md5 = self.get_md5(file)
        ppt = PPT.query.filter_by(md5=md5).first()
        if ppt and (ppt.project_id==None):
            project = self.create_project(file)
            ppt.project=project
            ppt.name=self.get_PPT_name(file)
            ppt.path = self.mirror_path(file)
            ppt.date = datetime.now()
            db.session.commit()
            return True
        return False

    def delete(self, file):
        with self.app.app_context():
            projectname = self.get_project_name(file)
            filepath = self.mirror_path(file)
            ppt = PPT.query.filter_by(path=filepath).first()
            if ppt:
                ppt.project_id=None
                db.session.commit()
                self.write_log(
                    f"{self.time} Delete PPT {file}")
            projects = Project.query.filter_by(name=projectname).all()
            for p in projects:
                if not p.ppts:
                    db.session.delete(p)
                    db.session.commit()
                    self.write_log(
                        f"{self.time} Delete Project {file}")

    def move(self, src, dst):
        self.write_log(f"{self.time} move {src} => {dst}")



class PPTX_Handler(PatternMatchingEventHandler):
    def __init__(self, logger):
        super().__init__(patterns=["*.pptx", ], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger

    def on_created(self, event):
        t1=time.time()
        self.logger.create(event.src_path)
        t2=time.time()
        print("Create {} Done in {:.1f}".format(event.src_path,t2-t1))


    def on_deleted(self, event):
        t1 = time.time()
        self.logger.delete(event.src_path)
        t2 = time.time()
        print("Delete {} Done in {:.1f}".format(event.src_path, t2-t1))


    def on_modified(self, event):
        print(f"Modify {event.src_path}")

    def on_moved(self, event):
        print(f"Rename {event.src_path} to {event.dest_path}")


def StartWatch(source_folder, log_file):
    my_observer = Observer()
    logger = PPT_Indexer(log_file=log_file)

    my_observer.schedule(PPTX_Handler(logger=logger),
                         source_folder, recursive=True)
    my_observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()


def index_path(path,log_file):
    logger = PPT_Indexer(log_file=log_file)
    pptxs=glob_pptx(path)
    for i in pptxs:
        logger.delete(i)
        logger.create(i)


if __name__ == "__main__":
    app = create_app(keeplog=False)
    app.app_context().push()
    source_folder = app.config['PPT_SOURCE_FOLDER']  
    log_file = "/Users/hui/Documents/Scripts/ngs_server/app/tasks/ppt_log.txt"
    print(f'start watching {source_folder}')
    index_path(
        '/Users/hui/Cloudstation/R&D/Projects/VEGF/VEGF Aptamer Characterization',log_file=log_file)

    StartWatch(source_folder, log_file)

# Create / Users/hui/Cloudstation/R &D/Projects/VEGF/Stemloop PD copy.pptx
# Delete / Users/hui/Cloudstation/R & D/Projects/VEGF/Stemloop PD copy.pptx
# Create / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides.pptx
# Delete / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides.pptx
# Create / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides for ppt.pptx
# Delete / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides for ppt.pptx
# Create / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides for ppt.pptx
# Delete / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides for ppt.pptx
# Create / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides for ppt.pptx
# Delete / Users/hui/Cloudstation/R & D/Projects/VEGF/test slides for ppt.pptx
# Create / Users/hui/Cloudstation/R & D/Projects/VEGF/Test folder/test slides for ppt.pptx
