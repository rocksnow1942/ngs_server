import sys,pathlib
filepath = pathlib.Path(__file__).parent.parent.parent.parent
sys.path.append(str(filepath))

from app import db
from app.plojo_models import Plojo_Data, Plojo_Project
from app import create_app


app = create_app(keeplog=False)
app.app_context().push()

def load_shelve_to_sql(filepath):
    import shelve
    with shelve.open(filepath) as hd:
        for key,item in hd['index'].items():
            if Plojo_Project.query.get(key):
                pass
            else:
                i = Plojo_Project(index=key)
                i.data = list(item)
                db.session.add(i)
            db.session.commit()
        for key, item in hd.items():
            if key!='index':
                u=Plojo_Data.query.get(key)
                if u:
                    pass
                else:
                    new = Plojo_Data(index=key)
                    new.data=item
                    db.session.add(new)
                    db.session.commit()
                    print('added-{}'.format(key))


class Data():
    def __init__(self):
        # {0-vegf:set(), 1-Ang2:set()}
        self.index = {i.index:set(i.data) for i in Plojo_Project.query.all()}
        self.experiment = {}  # {ams0:{},ams1:{}}
        self.experiment_to_save = {}
        self.index_to_save={}
        self.experiment_load_hist = []
        self.exp_selection = set()
        self.max_load = 2000
    
    @staticmethod
    def all_experiment_index():
        return [i[0] for i in db.session.query(Plojo_Data.index).all()]


    def new_index(self, name):
        entry = list(self.index.keys())
        if not entry:
            entry = ['0']
        entry = sorted(entry, key=lambda x: int(
            x.split('-')[0]), reverse=True)[0]
        entry_start = int(entry.split('-')[0])+1
        new_entry_list = str(entry_start)+'-'+name
        self.index.update({new_entry_list: set()})
        return new_entry_list

    def next_exp(self, n):
        entry = set()
        for key, item in self.index.items():
            entry.update(item)
        entry = list(entry)
        if not entry:
            entry_start = 0
        else:
            entry = sorted(entry, key=lambda x: int(x.split('-')[0][3:]))[-1]
            entry_start = int(entry.split('-')[0][3:])+1
        new_entry_list = ['ams'+str(i)
                          for i in range(entry_start, entry_start+n)]
        return new_entry_list

    def load_experiment(self, new):
        if self.max_load < len(self.experiment.keys()):
            to_delete = []
            for i in self.experiment_load_hist[:-int(self.max_load*0.7)]:
                if i not in self.experiment_to_save.keys():
                    del self.experiment[i]
                    to_delete.append(i)
            self.experiment_load_hist = [
                i for i in self.experiment_load_hist if i not in to_delete]
        new_load = list(set(new)-self.experiment.keys())
        if new_load:
            for i in new_load:
                self.experiment[i]=Plojo_Data.query.get(i).data
                self.experiment_load_hist.append(i)
            
    def save_data(self):
       
        for k, i in self.index_to_save.items():
            print('index saves <{}> <{}>'.format(k,i))
            if i == 'sync':
                Plojo_Project.sync_obj(k, data=list(self.index[k]))
            elif i == 'del':
                u = Plojo_Project.query.get(k)
                db.session.delete(u)
                db.session.commit()
            elif '-' in i:
                Plojo_Project.sync_obj(k,newkey=i)
            else:
                print(k, i, "this is not found in experiment operation.")
        self.index_to_save = {}
        for key, item in self.experiment_to_save.items():
            print('Experiment saves <{}> <{}>'.format(key, item))
            if item == 'sync':
                Plojo_Data.sync_obj(key, data=self.experiment[key])
            elif item == 'del':
                u = Plojo_Data.query.get(key)
                db.session.delete(u)
                db.session.commit()
            else:
                print(key, item, 'this is unfound in run operation.')
        self.experiment_to_save = {}


# class Data():
#     def __init__(self,data_index):
#         self.index = data_index #{0-vegf:set(), 1-Ang2:set()}
#         self.experiment = {} # {ams0:{},ams1:{}}
#         self.experiment_to_save = {}
#         self.experiment_load_hist = []
#         self.exp_selection = set()
#         self.max_load = 2000
#     def new_index(self,name):
#         entry = list(self.index.keys())
#         if not entry:
#             entry = ['0']
#         entry = sorted(entry, key=lambda x: int(x.split('-')[0]), reverse=True)[0]
#         entry_start = int(entry.split('-')[0])+1
#         new_entry_list=str(entry_start)+'-'+name
#         self.index.update({new_entry_list:set()})
#         return new_entry_list
#     def next_exp(self,n):
#         entry = set()
#         for key,item in self.index.items():
#             entry.update(item)
#         entry = list(entry)
#         if not entry:
#             entry_start = 0
#         else:
#             entry = sorted(entry, key=lambda x: int(x.split('-')[0][3:]))[-1]
#             entry_start = int(entry.split('-')[0][3:])+1
#         new_entry_list=['ams'+str(i) for i in range(entry_start, entry_start+n)]
#         return new_entry_list
#     def load_experiment(self,new):
#         if self.max_load < len(self.experiment.keys()):
#             to_delete =[]
#             for i in self.experiment_load_hist[:-int(self.max_load*0.7)]:
#                 if i not in self.experiment_to_save.keys():
#                     del self.experiment[i]
#                     to_delete.append(i)
#             self.experiment_load_hist = [i for i in self.experiment_load_hist if i not in to_delete ]
#         new_load = list(set(new)-raw_data.experiment.keys())
#         if new_load:
#             with shelve.open(os.path.join(file_save_location,file_name)) as hd:
#                 for i in new_load:
#                     raw_data.experiment[i] = hd[i]
#                     self.experiment_load_hist.append(i)
