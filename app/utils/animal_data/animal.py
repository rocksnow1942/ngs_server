import os,re,json,pathlib


def create_folder_structure(path, days=[]):
    """
    create folder structure for holding animal test data.
    Experiment Name/DXX/FP,OCT/files
    """
    if not os.path.isdir(path):
        os.mkdir(path)
    for d in days:
        df = os.path.join(path, f'D{d}')
        os.mkdir(df)
        os.mkdir(os.path.join(df, 'FP'))
        os.mkdir(os.path.join(df, 'OCT'))


def rename_monkey(path, pattern='1934(?P<animal>8[0-9][0-9])'):
    """
    rename the FP/OCT subfolders with proper name.
    rename folder under FP/OCT with regex pattern <animal>
    """
    p = re.compile(pattern)
    for root, folder, file in os.walk(path):
        if root.endswith('FP') or root.endswith('OCT'):
            for f in folder:
                new = p.search(f)
                if new:
                    os.rename(os.path.join(root, f), os.path.join(root, new.groupdict()['animal']))

class Experiment(object):
    """
    init the class with folder path to experiment results 
    folder structure needs to be:
    -Experiment name 
     |-D5
       |-FP
       |- Monkey 
          |- XXXXXXX-L.jpg
          |- XXXXXXX-R.jpg
       |-OCT
       |- Monkey 
          |-OD 
            |- XXXXXX.jpg
    """
    def __init__(self, path):
        """
        init the instance and save json file automatically.
        """
        self.path = path
        pa = pathlib.Path(path)
        
        self.note = ""
        self.data = {}
        self.init_data()
        self.save_json()

    def save_json(self):
        with open(self.path+'.json', 'wt') as f:
            json.dump(self.__dict__, f, separators=(',', ':'))

    @classmethod
    def load_json(cls, file):
        with open(file, 'rt') as f:
            data = json.load(f)
        new = cls.__new__(cls)
        new.__dict__ = data
        # each time loading, set the file and folder path again; incase file is being loaded on different systems. 
        pa = pathlib.Path(file)
        new.path=str(pa.parent/pa.stem)
        new.name = pa.stem 
        return new

    def update(self):
        needupdate = self.init_data(update=True) 
        needupdate = self.remove_dead_files() or needupdate
        if needupdate:
            self.remove_empty_data()
            self.save_json()
        
    def remove_dead_files(self):
        needupdate = False 
        todelete = []
        for l1,monkey in self.data.items():
            for l2,eye in monkey.items():
                for l3,measure in eye.items():
                    if l3 in ('FP','OCT'):
                        for l4,days in measure.items():
                            newdays = [i for i in days if os.path.isfile(os.path.join(self.path, i))]
                            if newdays != days:
                                needupdate=True
                                self.data[l1][l2][l3][l4]=newdays
        return needupdate

    def remove_empty_data(self): 
        """
        remove empty monkey or eye or measure or day dictionary
        avoids dead link options. 
        """
        days = [i for i in self.day_iterator() if not self.get_item(*i)]
        for d in days:
            self.get_item(*d[:-1]).pop(d[-1])
            
        measures = [i for i in self.measure_iterator() if not self.get_item(*i)]
        for m in measures:
            self.get_item(*m[:-1]).pop(m[-1])
        eyes = [i for i in self.eye_iterator() if (
            ('FP' not in self.get_item(*i).keys()) and ('OCT' not in self.get_item(*i).keys()))]
        for e in eyes:
            self.get_item(*e[:-1]).pop(e[-1])
        monkeys = [i for i in self.monkey_iterator() if not self.get_item(i)]
        for m in monkeys:
            self.data.pop(m)

    def get_item(self,*args):
        result=self.data 
        for i in args:
            result=result.get(i)
        return result 

    def day_iterator(self):
        for l1, monkey in self.data.items():
            for l2, eye in monkey.items():
                for l3, measure in eye.items():
                    if l3 in ('FP', 'OCT'):
                        for l4, days in measure.items():
                            yield l1,l2,l3,l4

    def measure_iterator(self):
        for l1, monkey in self.data.items():
            for l2, eye in monkey.items():
                for l3, measure in eye.items():
                    if l3 in ('FP', 'OCT'):
                        yield l1,l2,l3

    def eye_iterator(self):
        for l1, monkey in self.data.items():
            for l2, eye in monkey.items():
                yield l1,l2 
    
    def monkey_iterator(self):
        yield from self.data.keys()

    def getitem(self,*args):
        result=self.data
        for i in args:
            result = result.get(i)
        return result
                     
    def update_entry(self, monkey, eye, measure, day, data):
        need_update=True
        if self.data.get(monkey, None) is None:
            self.data[monkey] = {}    
        if self.data[monkey].get(eye, None) is None:
            self.data[monkey][eye] = {'note': ""}    
        if self.data[monkey][eye].get(measure, None) is None:
            self.data[monkey][eye][measure] = {}
        if self.data[monkey][eye][measure].get(day,None) is None:
            self.data[monkey][eye][measure][day] = data # create new data     
        else:
            if set(data) == set(self.data[monkey][eye][measure][day]):
                need_update = False
            else:
                self.data[monkey][eye][measure][day] = data # if day is already there, decide if need to update. 
        return need_update 

    def create_entry(self, monkey, eye, measure, day, data):
        if self.data.get(monkey, None) is None:
            self.data[monkey] = {}
        if self.data[monkey].get(eye, None) is None:
            self.data[monkey][eye] = {'note': "", 'FP': {}, 'OCT': {}}
        
        self.data[monkey][eye][measure][day] = data

    def init_data(self,update=False):
        homedir = pathlib.Path(self.path)
        need_update=not update
        for root, folder, files in os.walk(self.path):
            pa = pathlib.Path(root)
            pa_parts = pa.parts
            if pa_parts[-2] == 'FP':
                monkey = pa_parts[-1]
                day = pa_parts[-3]
                L = [i for i in files if i.endswith('L.jpg')]
                R = [i for i in files if i.endswith('R.jpg')]
                L.sort(), R.sort()
                relative = pa.relative_to(homedir)
                L = [os.path.join(relative, i) for i in L]
                R = [os.path.join(relative, i) for i in R]
                if update:
                    need_update = self.update_entry(monkey, 'L', 'FP', day, L)
                    need_update = self.update_entry(monkey, 'R', 'FP', day, R)
                else:
                    self.create_entry(monkey, 'L', 'FP', day, L)
                    self.create_entry(monkey, 'R', 'FP', day, R)
                
            elif pa_parts[-3] == 'OCT':
                monkey = pa_parts[-2]
                day = pa_parts[-4]
                eye = pa_parts[-1]
                relative = pa.relative_to(homedir)
                eye = {'OD': 'R', 'OS': 'L'}[eye]
                data = [i for i in files if i.endswith('.jpg')]
                data.sort()
                data = [os.path.join(relative, i) for i in data]
                if update:
                    need_update = self.update_entry(monkey, eye, 'OCT', day, data)
                else:
                    self.create_entry(monkey, eye, 'OCT', day, data)
        return need_update          

    def list_animal(self):
        return list(self.data.keys())

    def render_form_kw(self,data):
        exp = data.get('exp','')
        exp_animal = sorted(list(self.data.keys()))
        animal = data.get('animal', exp_animal[0])
        exp_eye = sorted([i for i in self.data.get(animal, {}).keys()])
        eye = data.get('eye', exp_eye[0])
        exp_measure = sorted([i for i in self.data.get(animal,{}).get(eye,{}).keys() if i!='note'])
        exp_note = self.data.get(animal,{}).get(eye,{}).get('note','')
        measure = data.get('measure',exp_measure[0])
        exp_day =sorted([i for i in self.data.get(animal,{}).get(eye,{}).get(measure,{}).keys() ])
        day = data.get('day', exp_day and exp_day[0])
        return dict(exp_animal=exp_animal,exp_eye=exp_eye,exp_measure=exp_measure,exp_note=exp_note,exp_day=exp_day,
                exp=exp,animal=animal,eye=eye,measure=measure,day=day)
       

    def render_figure_kw(self,data):
        exp = data.get('exp')
        animal = data.get('animal',)
        eye = data.get('eye', )
        measure = data.get('measure', )      
        day = data.get('day', )
        return [os.path.join(exp,i) for i in self.data[animal][eye][measure][day]]

    def edit_data(self,data,order):
        exp = data.get('exp')
        animal = data.get('animal',)
        eye = data.get('eye', )
        measure = data.get('measure', )
        day = data.get('day', )
        self.data.get(animal, {}).get(eye, {})['note'] = data.get('note')
        old = self.data[animal][eye][measure][day]
        if len(order)==len(old):
            self.data[animal][eye][measure][day] = [old[i] for i in order]
        return f"{exp}-{animal}-{eye}"
