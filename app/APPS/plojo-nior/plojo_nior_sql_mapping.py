import json
import sys,pathlib
# filepath = os.path.dirname(__file__)
filepath = pathlib.Path(__file__).parent.parent.parent.parent
sys.path.append(str(filepath))
from app import db
from app.plojo_models import Plojonior_Data, Plojonior_Index
from app import create_app



def load_shelve_to_sql(filepath):
    import shelve
    with shelve.open(filepath) as hd:
        for key,item in hd['index'].items():
            if Plojonior_Index.query.get(key):
                pass
            else:
                i = Plojonior_Index(exp=key,**item)
                db.session.add(i)
            db.session.commit()
        for key, item in hd.items():
            if key!='index' and (not key.endswith('raw')):
                for er,er_item in item.items():
                    exp,index = er.split('-')
                    try:
                        if Plojonior_Data.query.get((exp,index)):
                            u = Plojonior_Data.query.get((exp, index))
                            u.meta = er_item 
                            u.raw = hd[exp+'raw'][er]
                        else:
                            new = Plojonior_Data(exp_id=exp, run=index, _meta=json.dumps(
                                er_item), _data=json.dumps(hd[exp+'raw'][er]))
                            print("added new {}-{}".format(exp,index))
                            db.session.add(new)
                        db.session.commit()
                    except:
                        print("*** failed {}".format(er))

# define raw data class and load rawdata.
class Data():
    """
    class to interact with shelve data storage.
    data stored in shelvs as follows:
    index : a dict contain experiment information; { ams5:{'name': 'experiment name','date': "20190101",'author':'jones'}, ams23:{}}
    meta information and raw data of each experiment is under: "amsXX" and "amsXXraw"
    meta information example:
            'ams39':{
            "ams39-run0": {
                "speed": 1.0,
                "date": "20190409",
                "name": "PHENORP YPEGBS3 2-5V1RXN 0-5MMBS3 35C 1UG 5-60 28M 1MM",
                "A": {
                    "y_label": "DAD signal / mA.U.",
                    "extcoef": 33.0
                },
                "B": {
                    "y_label": "Solvent B Gradient %"
                }
            },
            "ams39-run1": { }, "ams39-run2": { }}
    raw data example:
        ams39raw:{'ams39-run0':{'A':{'time':[0.0,39.99,6000]},'signal':[0,0.1,...]},'B':{'time':},'ams39-run1'}
    when load in to Data Class,
    index is loaded to data.index
    meta information is loaded to data.experiment = {'ams39':{}}
    raw data is loaded to data.experiment_raw = {'ams39':{}}  !!! caution: 'raw' tag is discarded during loading.
    add sqlalchemy supprot
    """

    def __init__(self):
        app = create_app(keeplog=False)
        app.app_context().push()
        try:
            db.session.flush()
            db.session.commit()
            print('Init database')
        except Exception as e:
            print(f'Have to Roll back: Reason{e}')
            db.session.rollback()
        self.index = { i.exp:i.jsonify for i in Plojonior_Index.query.all()}
        self.experiment = {}  # {ams0:{ams0-run1:{date: ,time: , A:{}}}}
        self.experiment_to_save = []
        self.index_to_save = []
        self.experiment_raw = {}
        self.experiment_load_hist = []
        self.max_load = 200
        self.load_experiment(self.most_recent_exp())
        

    def most_recent_exp(self,n=5):
        entry = list(self.index.keys())
        if not entry:
            entry = ['ams0']
        entry = sorted(entry, key=lambda x: int(
            x[3:]), reverse=True)[0:n]
        return entry

    def next_index(self, n):
        entry = self.most_recent_exp(n=1)[0]   
        entry_start = int(entry.split('-')[0][3:])+1
        new_entry_list = ['ams'+str(i)
                          for i in range(entry_start, entry_start+n)]
        return new_entry_list

    def next_run(self, index, n):
        entry = list(self.experiment[index].keys())
        if not entry:
            entry_start = 0
        else:
            entry = sorted(entry, key=lambda x: int(
                x.split('-')[1][3:]), reverse=True)[0]
            entry_start = int(entry.split('-')[1][3:])+1
        new_entry_list = [index+'-run'+str(i)
                          for i in range(entry_start, entry_start+n)]
        return new_entry_list

    def get_meta(self,key):
        e,r = key.split('-')
        return self.experiment.get(e,{}).get(key,{})
    def get_raw(self,key):
        e, r = key.split('-')
        return self.experiment_raw.get(e, {}).get(key, {})

    def load_experiment(self, new):
        if self.max_load < len(self.experiment.keys()):
            to_delete = []
            to_save = [i.split('-')[0] for i in self.experiment_to_save.keys()]
            for i in self.experiment_load_hist[0:100]:
                if i not in to_save:
                    del self.experiment[i]
                    del self.experiment_raw[i]
                    to_delete.append(i)
            self.experiment_load_hist = [
                i for i in self.experiment_load_hist if i not in to_delete]
        new_load = list(set(new)-self.experiment.keys())
        if new_load:
            for i in new_load:
                data=Plojonior_Data.query.filter_by(exp_id=i).all()
                self.experiment[i] = {d.index: d.meta for d in data}
                self.experiment_raw[i] = {d.index: d.raw for d in data}
                self.experiment_load_hist.append(i)

    def save_data(self):
        for k,i in self.index_to_save:
            if i == 'sync':
                Plojonior_Index.sync_obj(k,self.index[k])
            elif i == 'del':
                u=Plojonior_Index.query.get(k)
                db.session.delete(u)
                db.session.commit()
            else:
                print(k,i, "this is not found in experiment operation.")
        self.index_to_save=[]
        for key,item in self.experiment_to_save:
            if item == 'sync':
                Plojonior_Data.sync_obj(key, meta=self.get_meta(key))
            elif item == 'upload':
                Plojonior_Data.sync_obj(key, meta=self.get_meta(key),raw=self.get_raw(key))
            elif item == 'del':
                u = Plojonior_Data.query.get(key.split('-'))
                db.session.delete(u)
                db.session.commit()
            elif '-' in item:
                Plojonior_Data.sync_obj(key,newkey=item)
            else:
                print(key,item,'this is unfound in run operation.')
        self.experiment_to_save=[]

      
