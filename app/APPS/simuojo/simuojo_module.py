import os,glob
from os import path
import shelve
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import HoverTool,Slider,RangeSlider
from bokeh.models.widgets import Button, TextInput,PreText,Div,TextAreaInput,Select,Dropdown
from bokeh.layouts import widgetbox,column,row
import numpy as np
from simu_utils import file_save_location,file_name
# from _structurepredict import Structure,plotbackend
import datetime

#TODO
# change parameters with curve selection.
# ability to copy and paste parameters.

cache_loc=path.join(path.dirname(__file__),'static','cache')


class Data():
    def __init__(self,data_index):
        self.index = data_index #{0-vegf:set(), 1-Ang2:set()}
        self.experiment = {} # {ams0:{},ams1:{}}
        self.experiment_to_save = {}
        self.experiment_load_hist = []
        self.exp_selection = set()
        self.max_load = 2000
    def new_index(self,name):
        entry = list(self.index.keys())
        if not entry:
            entry = ['0']
        entry = sorted(entry, key=lambda x: int(x.split('-')[0]), reverse=True)[0]
        entry_start = int(entry.split('-')[0])+1
        new_entry_list=str(entry_start)+'-'+name
        self.index.update({new_entry_list:set()})
        return new_entry_list
    def next_exp(self,n):
        entry = set()
        for key,item in self.index.items():
            entry.update(item)
        entry = list(entry)
        if not entry:
            entry_start = 0
        else:
            entry = sorted(entry, key=lambda x: int(x.split('-')[0][3:]))[-1]
            entry_start = int(entry.split('-')[0][3:])+1
        new_entry_list=['ams'+str(i) for i in range(entry_start, entry_start+n)]
        return new_entry_list
    def load_experiment(self,new):
        if self.max_load < len(self.experiment.keys()):
            to_delete =[]
            for i in self.experiment_load_hist[:-int(self.max_load*0.7)]:
                if i not in self.experiment_to_save.keys():
                    del self.experiment[i]
                    to_delete.append(i)
            self.experiment_load_hist = [i for i in self.experiment_load_hist if i not in to_delete ]
        new_load = list(set(new)-self.experiment.keys())
        if new_load:
            with shelve.open(os.path.join(file_save_location,file_name)) as hd:
                for i in new_load:
                    self.experiment[i] = hd[i]
                    self.experiment_load_hist.append(i)
    def save_experiment(self):
        with shelve.open(os.path.join(file_save_location,file_name),writeback=False) as hd:
            hd['index'] = self.index
            for key,item in self.experiment_to_save.items():
                if key == 'index':
                    pass
                elif item == 'sync':
                    hd[key]=self.experiment[key]
                elif item == 'del':
                    del hd[key]

def plojo_data_init():
    with shelve.open(path.join(file_save_location,file_name)) as f:
        plojo_data = Data(f['index'])
    return plojo_data



def find_ec_50(a,signal):

    med = (np.max(signal)+np.min(signal))/2
    closest = (np.abs(signal - med)).argmin()
    cosest =max(1,min(closest, len(a)-1))
    left,cv,right = signal[closest-1],signal[closest],signal[closest+1]

    if (left<cv)^(cv<med):
        cor = left
        cori = closest-1
    else:
        cor = right
        cori = closest+1

    if cor==cv:
        return a[closest]
    else:

        return a[closest] + (med-cv)*(a[cori]-a[closest])/(cor-cv)


class ic50_simu():
    def __init__(self):
        para_text = PreText(text='Binding Parameters')
        para_text_ = PreText(text='Binding Parameters')
        self.slider_kd_1 = Slider(title='log(Receptor-VEGF Kdr) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_kd_2 = Slider(title='log(Aptamer-VEGF Kda) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_r_0 = Slider(title='log(Receptor conc.) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_v_0 = Slider(title='log(VEGF conc.) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_Fminmax = RangeSlider(title = 'Singal Range AU', start =0, end =100000,step =1000,value =(1000,10000))
        self.name_input = TextInput(title='Create Name for the data',value='Simu_IC50')
        rand_text = PreText(text='Randomization Parameters')
        self.slider_conc_range =RangeSlider(title= 'Experiment Conc. (log nM) : ',  start = -5, end=5, step=0.01,value=(-2,2))
        self.slider_points = Slider(title='Number of concentration points: ', start = 3, end=20, step=1,value=9)
        self.slider_sets = Slider(title='Number of replicates:',start=1,end=9,step=1,value=1)
        self.slider_linear = Slider(title='Linear randomization', start = 0, end=25, step=0.1, value=0.2)
        self.slider_proportional = Slider(title='Proportional randomization', start = 0, end=25, step=0.1,value=0.2)
        self.input_kd_1 = TextInput(value="1", title="Receptor-VEGF Kdr (nM):")
        self.input_kd_2 = TextInput(value="1", title="Aptamer-VEGF Kda (nM):")
        self.input_r_0 = TextInput(value="1", title="Receptor Conc. (nM):")
        self.input_v_0 = TextInput(value="1", title="VEGF Conc. (nM):")
        self.input_ic50 = TextInput(value='2',title='Caculated IC50 (nM):')
        self.linecolors = ['green', 'red', 'blue', 'fuchsia', 'darkorange']
        self.curve = Select(title='Curve Selection', value='0', options=[(str(
            i), 'Curve {}: {}'.format(i+1, self.linecolors[i].capitalize())) for i in range(5)])

        self.copy = Button(label='Copy Curve',button_type='success')

        refresh_button = Button(label='Refresh Random',button_type='success')
        add_button = Button(label='Add data to plojo',button_type='success')
        para_slider = widgetbox(para_text,self.slider_kd_1,self.slider_r_0,self.slider_kd_2,self.slider_v_0,self.slider_Fminmax,self.curve,self.copy,self.name_input)
        para_input = widgetbox(para_text_,self.input_kd_1,self.input_r_0,self.input_kd_2,self.input_v_0,self.input_ic50)
        rand_opt = widgetbox(rand_text,self.slider_conc_range,self.slider_points,self.slider_sets,self.slider_linear,self.slider_proportional,refresh_button,add_button)
        self.raw_data = ColumnDataSource(data=self.generate_plotdata(**self.fetch_para(True)))
        self.fit_data = {"0": ColumnDataSource(
            data=self.generate_plotdata(**self.fetch_para(False)))}

        self.fit_data.update({i: ColumnDataSource(
            data=self.generate_plotdata(empty=True)) for i in "1234"})


        self.p = figure(x_axis_label='Aptamer Concentration (nM)', y_axis_label='Receptor and Aptamer Signal A.U.', x_axis_type='log')
        self.pn = figure(x_axis_label='Aptamer Concentration (nM)', y_axis_label='Normalized Receptor Aptamer Signal', x_axis_type='log',x_range=self.p.x_range)
        self.curve_para = {"0": self.fetch_para(False)}
        self.p.title.text = 'Receptor-VEGF complex / Receptor percentage'
        self.p.title_location='above'
        self.pn.title.text = 'Normalized Signal'
        self.pn.title_location = 'above'

        for curve, color in zip("01234", self.linecolors):

            p_1=self.p.line('a_0','rv_per', source=self.fit_data[curve],line_color=color,line_width=2,alpha=0.75,legend='Receptor')
            hover_tool_1 = HoverTool(renderers=[p_1], tooltips=[ ('IC50/nM',"@ic50"),
                                                                 ('Rcpt Conc / Kd', '@kdr'), ('VEGF conc / Aptamer Kd', '@kda')], )  # ('Aptamer/nM', '@a_0{0.000}'), ('Rcpt Signal', '@rv_per{0}'),mode='vline'
            self.p.add_tools(hover_tool_1)


        for curve, color in zip("01234", self.linecolors):
            p_2 = self.p.line(
                'a_0', 'av_per', source=self.fit_data[curve], line_color=color, line_width=2, line_dash='dotdash', alpha=0.5, legend='Aptamer')
            hover_tool_2 = HoverTool(renderers=[p_2],tooltips=[('Kd_app/nM',"@kdapp"),('Aptamer/nM', '@a_0{0.000}'),( 'Aptamer Signal', '@av_per{0}' )])
            self.p.add_tools(hover_tool_2)

            pn_1=self.pn.line('a_0','rv_norm', source=self.fit_data[curve],line_color=color,line_width=2,alpha=0.75,legend='Receptor')
            hover_tool_1n = HoverTool(renderers=[pn_1],tooltips=[('Aptamer/nM', '@a_0{0.00}'),( 'RV signal', '@rv_norm{0.00}' ),('Receptor Kd', '@kdr'),('Receptor Conc.' ,"@cr"),('Aptamer Kd', '@kda'),('VEGF Conc.','@cv')],)
            self.pn.add_tools(hover_tool_1n)

            pn_2 = self.pn.line(
                'a_0', 'av_norm', source=self.fit_data[curve], line_color=color, line_width=2, line_dash='dotdash', alpha=0.5, legend='Aptamer')
            hover_tool_2n = HoverTool(renderers=[pn_2],tooltips=[('Aptamer/nM', '@a_0{0.00}'),( 'AV signal', '@av_norm{0.00}' )],)
            self.pn.add_tools(hover_tool_2n)


        self.p.circle('a_0','rv_per',source=self.raw_data,color='red',line_width=3,alpha=0.75,legend='Receptor')
        self.p.circle('a_0','av_per',source=self.raw_data,color='green',line_width=3,alpha=0.5,legend='Aptamer')
        self.p.legend.click_policy = 'hide'
        self.p.legend.location = 'center_left'
        self.p.legend.border_line_alpha = 0
        self.p.legend.background_fill_alpha = 0.1
        self.p.plot_height = 400
        self.p.plot_width = 600


        self.pn.circle('a_0','rv_norm',source=self.raw_data,color='red',line_width=3,alpha=0.75,legend='Receptor')
        self.pn.circle('a_0','av_norm',source=self.raw_data,color='green',line_width=3,alpha=0.5,legend='Aptamer')
        self.pn.legend.click_policy = 'hide'
        self.pn.legend.location = 'center_left'
        self.pn.legend.border_line_alpha = 0
        self.pn.legend.background_fill_alpha = 0.1
        self.pn.plot_height = 400
        self.pn.plot_width = 600
        self.slider_kd_1.on_change('value',self.callback)
        self.slider_kd_2.on_change('value',self.callback)
        self.slider_r_0.on_change('value',self.callback)
        self.slider_v_0.on_change('value',self.callback)
        self.slider_Fminmax.on_change('value',self.callback)
        self.slider_conc_range.on_change('value',self.callback)
        self.slider_points.on_change('value',self.callback)
        self.slider_linear.on_change('value',self.callback)
        self.slider_proportional.on_change('value',self.callback)
        self.slider_sets.on_change('value',self.callback)
        self.curve.on_change('value',self.curve_cb)
        refresh_button.on_click(self.refresh_button_cb)
        add_button.on_click(self.add_button_cb)
        self.copy.on_click(self.copy_cb)
        self.layout =([self.p,self.pn],[para_input,para_slider,rand_opt])

    def copy_cb(self):
        curve = self.curve.value
        if self.copy.button_type=='success':
            self.copy.button_type='warning'
            self.copy.label= '<Curve{}:{}> Copied. Click to Paste'.format(int(curve)+1, self.linecolors[int(curve)].capitalize())
        else:
            self.copy.button_type='success'
            copyed = str(int(self.copy.label[6])-1)
            self.copy.label="Copy Curve"
            self.curve_cb(1,1,copyed)

    def curve_cb(self,attr,old,new):
        if self.curve_para.get(new,None):
            para = self.curve_para[new]
            self.slider_kd_1.value = np.log10(para['kd_1'])
            self.slider_kd_2.value = np.log10(para['kd_2'])
            self.slider_r_0.value = np.log10(para['r_0'])
            self.slider_v_0.value = np.log10(para['v_0'])
            self.slider_Fminmax.value = (para['Fmin'],para['Fmax'])
        else:
            self.curve_para[new]=self.curve_para[old]


    def rv_solver(self,a_0, r_0, v_0, kd_r, kd_a):
        a=kd_a-kd_r
        d=-v_0*kd_a*r_0**2
        b=kd_r*r_0-2*kd_a*r_0+kd_r**2-kd_r*kd_a-kd_r*a_0+kd_r*v_0-kd_a*v_0
        c=r_0**2*kd_a+kd_r*kd_a*r_0-v_0*r_0*kd_r+2*v_0*r_0*kd_a+a_0*kd_r*r_0
        if a!=0:
            b=b.astype('complex128')
            c=c.astype('complex128')
            p=(3*a*c-b**2)/(3*a**2)
            q=(27*a**2*d-9*a*b*c+2*b**3)/(27*a**3)
            middle=((q/2)**2+(p/3)**3)**(1/2)
            left=(-q/2+middle)**(1/3)
            right=(-q/2-middle)**(1/3)
            w = (3**(1/2)*1j-1)/2
            convert=b/(3*a)
            x_1=left+right-convert
            x_2=w*left+w**2*right-convert
            x_3=w**2*left+w*right-convert
        else:
            x_1=(-c+(c**2-4*b*d)**(1/2))/(2*b)
            x_2=(-c-(c**2-4*b*d)**(1/2))/(2*b)
            x_3=np.zeros(len(a_0))
        min_rv=min(r_0,v_0)
        result=np.array([])
        for root in zip(x_1,x_2,x_3):
            real_root = [i.real for i in root if 0<i.real<min_rv]
            if real_root:
                real_root = min(real_root)
            else:
                real_root=0
            result=np.append(result,real_root)
        return result


    def randomizer(self,signal,linear=0.001, proportional=0.001,seed=42):
        np.random.seed(seed)
        size = len(signal)
        max_sig = max(signal)
        return signal * np.random.normal(loc=1,scale=proportional,size=size) + max_sig*np.random.normal(loc=0,scale=linear,size=size)


    def generate_plotdata(self,empty=False,r_0=1,v_0=1,kd_1=1,kd_2=1,Fmax=10000,Fmin=1000,start=None,end=None,point=100,randomize=False,proportional=0.001,linear=0.001,sets=1,**kwargs):
        if empty:
            return {'a_0':[], 'rv_per':[], 'av_per':[],'av_norm':[],'rv_norm':[]}
        if start == None and end == None:
            ic_50 = kd_2*(1+r_0/kd_1)
            a_0 = np.geomspace(ic_50 / 10000, ic_50 * 10000, 200)
        else:
            a_0= np.geomspace(start,end,point)
        rv = self.rv_solver(a_0,r_0,v_0,kd_1,kd_2)
        av =v_0-rv-kd_1*rv/(r_0-rv)
        rv_per = rv/v_0*(Fmax-Fmin)+Fmin
        av_per = av/v_0*(Fmax-Fmin)+Fmin
        if randomize:
            rv_per = self.randomizer(np.repeat(rv_per,sets),linear=linear,proportional=proportional,**kwargs)
            av_per = self.randomizer(np.repeat(av_per,sets),linear=linear,proportional=proportional,**kwargs)
            rv_norm = (rv_per-min(rv_per))/(max(rv_per)-min(rv_per))*100
            av_norm = (av_per-min(av_per))/(max(av_per)-min(av_per))*100
            result_={'a_0':np.repeat(a_0,sets), 'rv_per':rv_per,'av_per':av_per,'av_norm':av_norm,'rv_norm':rv_norm}
        else:
            rv_norm = (rv_per-min(rv_per))/(max(rv_per)-min(rv_per))*100
            av_norm = (av_per-min(av_per))/(max(av_per)-min(av_per))*100
            ic50 = find_ec_50(a_0,rv_per)
            ec50 = find_ec_50(a_0,av_per)
            result_ = {'a_0':a_0, 'rv_per':rv_per, 'av_per':av_per,'av_norm':av_norm,'rv_norm':rv_norm,
                       'kdr': ["{:.2g} / {:.2g}".format(r_0, kd_1)]*len(a_0), 'kda': ["{:.2g} / {:.2g}".format(v_0, kd_2)]*len(a_0),
                       'ic50': ["{:.2g}".format(ic50)]*len(a_0), 'kdapp': ["{:.2g}".format(ec50)]*len(a_0), }
        return result_


    def fetch_para(self,randomize):
        kd_1 = 10 ** self.slider_kd_1.value
        kd_2 = 10 ** self.slider_kd_2.value
        r_0 = 10 ** self.slider_r_0.value
        v_0 = 10 ** self.slider_v_0.value
        sets=self.slider_sets.value
        Fmax = self.slider_Fminmax.value[1]
        Fmin = self.slider_Fminmax.value[0]
        start = 10**self.slider_conc_range.value[0]
        end = 10**self.slider_conc_range.value[1]
        points = self.slider_points.value
        linear = self.slider_linear.value/100
        proportional = self.slider_proportional.value/100
        if randomize:
            result = dict(kd_1=kd_1,kd_2=kd_2,r_0=r_0,v_0=v_0,Fmax=Fmax,Fmin=Fmin,start=start,end=end,point=points,randomize=True,linear=linear,proportional=proportional,sets=sets)
        else:
            result = dict(kd_1=kd_1,kd_2=kd_2,r_0=r_0,v_0=v_0,Fmax=Fmax,Fmin=Fmin)
        return result


    def callback(self,attr,old,new):
        kd_1 = 10 ** self.slider_kd_1.value
        kd_2 = 10 ** self.slider_kd_2.value
        r_0 = 10 ** self.slider_r_0.value
        v_0 = 10 ** self.slider_v_0.value
        self.input_kd_1.value = str(kd_1)
        self.input_kd_2.value = str(kd_2)
        self.input_r_0.value = str(r_0)
        self.input_v_0.value = str(v_0)
        self.input_ic50.value = str(kd_2*(1+r_0/kd_1))
        curve = self.curve.value
        self.curve_para[curve] = self.fetch_para(False)
        self.fit_data[curve].data = self.generate_plotdata(**self.fetch_para(False))
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True))
        self.p.title.text = self.title_generator(self.fetch_para(False))


    def refresh_button_cb(self):
        seed = np.random.randint(90000)
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True),seed=seed)
        self.p.title.text = self.title_generator(self.fetch_para(False))

    def title_generator(self,para_dict):
        kd_1 = para_dict['kd_1']
        kd_2 = para_dict['kd_2']
        a_0 = para_dict['r_0']
        v_0 = para_dict['v_0']
        Fmax = para_dict['Fmax']
        Fmin = para_dict['Fmin']
        title = 'kd_r:{:.3g}nM; kd_a:{:.3g}nM; r_0:{:.3g}; v_0:{:.3g}; Fmax:{:.3g}, Fmin:{:.3g}'.format(kd_1,kd_2, a_0,v_0,Fmax,Fmin)
        return title

    def add_button_cb(self):
        plojo_data=plojo_data_init()
        new_entry=plojo_data.next_exp(1)[0]
        new_index = False
        for key in plojo_data.index.keys():
            if 'Simuojo' in key:
                new_index = key
        if not new_index:
            new_index = plojo_data.new_index('Simuojo Data')
        concentration=list(self.raw_data.data['a_0'])
        signal=list(self.raw_data.data['rv_per'])
        name=self.name_input.value
        para = self.fetch_para(True)
        tags = 'IC50: {:.4g}nM'.format(float(self.input_ic50.value))
        notes = self.title_generator(para) + '; R_l:{:.3g}; R_p:{:.3g}'.format(self.fetch_para(True)['linear'],self.fetch_para(True)['proportional'])
        dict_tosave = dict(date='SimuDate',concentration=concentration,signal=signal,tag=tags,note=notes,fit_method='ic_50',author='simu',name=name)
        plojo_data.experiment[new_entry]=dict_tosave
        plojo_data.index[new_index].add(new_entry)
        plojo_data.experiment_to_save.update({new_entry:'sync'})
        plojo_data.save_experiment()
        self.p.title.text='Data Saved to plojo.'

class DR_5PL():
    def __init__(self):
        para_text = PreText(text='Model Parameters')
        para_text_ = PreText(text='Model Parameters')
        self.slider_ec_50 = Slider(title='Model EC50 (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_hill = Slider(title='Hill Coefficient', start=-1, end=1, step=0.01, value=0)
        self.slider_s = Slider(title='Symmetry Factor S', start=-2, end=2, step=0.01, value=0)
        self.slider_Fmax = Slider(title='Fmax value AU',start = 0, end = 10000,step = 100, value = 5000)
        self.slider_Fmin = Slider(title='Fmin value AU',start = 0, end = 10000, step = 100, value = 200)
        self.name_input = TextInput(title='Create Name for the data',value='Simu_DR_5PL')
        rand_text = PreText(text='Randomization Parameters')
        self.slider_conc_range =RangeSlider(title= 'Experiment Conc. (log nM) : ',  start = -3, end=3, step=0.01,value=(-2,2))
        self.slider_points = Slider(title='Number of concentration points: ', start = 3, end=20, step=1,value=9)
        self.slider_sets = Slider(title='Number of replicates:',start=1,end=9,step=1,value=1)
        self.slider_linear = Slider(title='Linear randomization', start = 0, end=25, step=0.1, value=0.2)
        self.slider_proportional = Slider(title='Proportional randomization', start = 0, end=25, step=0.1,value=0.2)
        self.input_ec_50 = TextInput(value="1", title="Model EC50 (nM):")
        self.input_hill = TextInput(value="1", title="Hill Coefficient:")
        self.input_s = TextInput(value="1", title="Symmetry Factor S:")
        refresh_button = Button(label='Refresh Random',button_type='success')
        add_button = Button(label='Add data to plojo',button_type='success')
        self.copy = Button(label='Copy Curve', button_type='success')
        self.linecolors = ['green', 'red', 'blue', 'fuchsia', 'darkorange']
        self.curve = Select(title='Curve Selection', value='0', options=[(str(
            i), 'Curve {}: {}'.format(i+1, self.linecolors[i].capitalize())) for i in range(5)])

        self.curve_para = {"0": self.fetch_para(False)}
        self.curve.on_change('value', self.curve_cb)
        para_slider = widgetbox(para_text,self.slider_ec_50,self.slider_hill,self.slider_s,self.slider_Fmax,self.slider_Fmin,self.curve,self.copy,self.name_input)
        para_input = widgetbox(para_text_,self.input_ec_50,self.input_hill,self.input_s)
        rand_opt = widgetbox(rand_text,self.slider_conc_range,self.slider_points,self.slider_sets,self.slider_linear,self.slider_proportional,refresh_button,add_button)
        self.fit_data = {"0": ColumnDataSource(data=self.generate_plotdata(**self.fetch_para(False)))}
        self.fit_data.update({i: ColumnDataSource(
            data=self.generate_plotdata(empty=True,**self.fetch_para(False))) for i in "1234"})
        self.raw_data = ColumnDataSource(data=self.generate_plotdata(**self.fetch_para(True)))
        self.p = figure(x_axis_label='Aptamer (nM)', y_axis_label='Signal / A.U.', x_axis_type='log')

        self.p.title.text = 'Dose Response 5 Parameter Logistic Model'
        self.p.title_location='above'
        for curve, color in zip("01234", self.linecolors):
            temp=self.p.line('a_0','signal', source=self.fit_data[curve],line_color=color,line_width=2)
            hover_tool_1 = HoverTool(renderers=[temp],tooltips=[('EC50(half max)/nM','@ec50'),( 'EC50(Model)/nM', '@ec50set' ),('Hill','@hill'),('Symmetry','@s')],)#mode='vline'
            self.p.add_tools(hover_tool_1)

        self.p.circle('a_0','signal',source=self.raw_data,color='red',line_width=3)
        self.p.plot_height = 400
        self.p.plot_width = 700
        self.slider_ec_50.on_change('value',self.callback)
        self.slider_hill.on_change('value',self.callback)
        self.slider_s.on_change('value',self.callback)
        self.slider_Fmax.on_change('value',self.callback)
        self.slider_Fmin.on_change('value',self.callback)
        self.slider_conc_range.on_change('value',self.callback)
        self.slider_points.on_change('value',self.callback)
        self.slider_linear.on_change('value',self.callback)
        self.slider_proportional.on_change('value',self.callback)
        self.slider_sets.on_change('value',self.callback)
        refresh_button.on_click(self.refresh_button_cb)
        add_button.on_click(self.add_button_cb)
        self.copy.on_click(self.copy_cb)
        self.layout =([self.p],[para_input,para_slider,rand_opt])

    def copy_cb(self):
        curve = self.curve.value
        if self.copy.button_type=='success':
            self.copy.button_type='warning'
            self.copy.label= '<Curve{}:{}> Copied. Click to Paste'.format(int(curve)+1, self.linecolors[int(curve)].capitalize())
        else:
            self.copy.button_type='success'
            copyed = str(int(self.copy.label[6])-1)
            self.copy.label="Copy Curve"
            self.curve_cb(1,1,copyed)

    def randomizer(self,signal,linear=0.001, proportional=0.001,seed=42):
        np.random.seed(seed)
        size = len(signal)
        max_sig = max(signal)
        return signal * np.random.normal(loc=1,scale=proportional,size=size) + max_sig*np.random.normal(loc=0,scale=linear,size=size)

    def refresh_button_cb(self):
        seed = np.random.randint(90000)
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True),seed=seed)
        self.p.title.text = self.title_generator(self.fetch_para(False))

    def DR_5PL(self,x,ec_50,Fmax,Fmin,Hill,S):
        """
        Five parameters logistic regression
        signal = Fmin + (Fmax-Fmin)*(X**(Hill*S))/(X**Hill + EC50**Hill*(2**(1/S)-1))**S
        """
        denominator = (x**Hill+(ec_50)**Hill*(2**(1/S)-1))**S
        signal = Fmax - (Fmax-Fmin)*(x**(Hill*S))/denominator
        return signal


    def generate_plotdata(self,empty=False,ec_50=1,Fmax=10000,Fmin=1000,hill=1,s=1,start=None,end=None,point=100,randomize=False,proportional=0.001,linear=0.001,sets=1,**kwargs):
        if empty:
            return {'a_0':[],'signal':[]}
        if start == None and end == None:
            a_0 = np.geomspace(ec_50 / 1000, ec_50 * 1000, 100)
        else:
            a_0= np.geomspace(start,end,point)
        signal = self.DR_5PL(a_0,ec_50,Fmax,Fmin,hill,s)
        if randomize:
            signal = self.randomizer(np.repeat(signal,sets),linear=linear,proportional=proportional,**kwargs)
            result_={'a_0':np.repeat(a_0,sets), 'signal':signal}
        else:
            ic50 = find_ec_50(a_0, signal)
            result_ = {'a_0': a_0, 'signal': signal, 'ec50': ["{:.2g}".format(ic50)]*len(a_0),
                       'ec50set': ["{:.2g}".format(ec_50)]*len(a_0),'hill':["{:.2g}".format(hill)]*len(a_0),
                       's':["{:.2g}".format(s)]*len(a_0)}
        return result_

    def fetch_para(self,randomize):
        ec_50 = 10 ** self.slider_ec_50.value
        hill = 10 ** self.slider_hill.value
        s = 10 ** self.slider_s.value
        Fmax = self.slider_Fmax.value
        Fmin = self.slider_Fmin.value
        sets=self.slider_sets.value
        start = 10**self.slider_conc_range.value[0]
        end = 10**self.slider_conc_range.value[1]
        points = self.slider_points.value
        linear = self.slider_linear.value/100
        proportional = self.slider_proportional.value/100
        if randomize:
            result = dict(ec_50=ec_50,hill=hill,s=s,Fmax=Fmax,Fmin=Fmin,start=start,end=end,point=points,randomize=True,linear=linear,proportional=proportional,sets=sets)
        else:
            result = dict(ec_50=ec_50,hill=hill,s=s,Fmax=Fmax,Fmin=Fmin,)
        return result

    def curve_cb(self, attr, old, new):
        if self.curve_para.get(new, None):
            para = self.curve_para[new]
            self.slider_ec_50.value = np.log10(para['ec_50'])
            self.slider_hill.value = np.log10(para['hill'])
            self.slider_s.value = np.log10(para['s'])
            self.slider_Fmax.value = (para['Fmax'])
            self.slider_Fmin.value = (para['Fmin'])
        else:
            self.curve_para[new] = self.curve_para[old]

    def callback(self,attr,old,new):
        ec_50 = 10 ** self.slider_ec_50.value
        hill = 10 ** self.slider_hill.value
        s = 10 ** self.slider_s.value
        curve=self.curve.value
        self.curve_para[curve] = self.fetch_para(False)
        self.input_ec_50.value = str(ec_50)
        self.input_hill.value = str(hill)
        self.input_s.value = str(s)
        self.fit_data[curve].data = self.generate_plotdata(**self.fetch_para(False))
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True))
        self.p.title.text = self.title_generator(self.fetch_para(False))

    def title_generator(self,para_dict):
        ec_50 = para_dict['ec_50']
        hill = para_dict['hill']
        s = para_dict['s']
        Fmax = para_dict['Fmax']
        Fmin = para_dict['Fmin']
        title = 'EC50:{:.3g}nM; Hill:{:.3g}; S:{:.3g}; Fmax:{:.3g}, Fmin:{:.3g}'.format(ec_50,hill,s,Fmax,Fmin)
        return title

    def add_button_cb(self):
        plojo_data = plojo_data_init()
        new_entry=plojo_data.next_exp(1)[0]
        new_index = False
        for key in plojo_data.index.keys():
            if 'Simuojo' in key:
                new_index = key
        if not new_index:
            new_index = plojo_data.new_index('Simuojo Data')
        concentration=list(self.raw_data.data['a_0'])
        signal=list(self.raw_data.data['signal'])
        name=self.name_input.value
        para = self.fetch_para(True)
        tags = self.title_generator(para)
        notes = self.title_generator(para) + '; R_l:{:.3g}; R_p:{:.3g}'.format(self.fetch_para(True)['linear'],self.fetch_para(True)['proportional'])
        dict_tosave = dict(date='SimuDate',concentration=concentration,signal=signal,tag=tags,note=notes,fit_method='DR_4PL',author='simu',name=name)
        plojo_data.experiment[new_entry]=dict_tosave
        plojo_data.index[new_index].add(new_entry)
        plojo_data.experiment_to_save.update({new_entry:'sync'})
        plojo_data.save_experiment()
        self.p.title.text='Data Saved to plojo.'

class Kd_simu():

    def __init__(self):
        para_text = PreText(text='Binding Parameters')
        self.slider_kd = Slider(title='log(Kd) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_conc = Slider(title='log(S_0) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_ns = Slider(title='Non Specific Binding (AU/nM)', start=0, end=20, step=0.01, value=0)
        self.slider_Fminmax = RangeSlider(title = 'Singal Range AU', start =0, end =100000,step =1000,value =(1000,10000))
        para_text_ = PreText(text='Binding Parameters')
        self.input_kd = TextInput(title='Binding Kd (nM)',value='1')
        self.input_conc = TextInput(title='Fixed Component Conc. (nM)',value='1')
        self.input_ns = TextInput(title='Non Specific Binding (AU/nM)',value='1')
        rand_text = PreText(text='Randomization Parameters')
        self.slider_conc_range =RangeSlider(title= 'Experiment Conc. (log nM) : ',  start = -3, end=3, step=0.01,value=(-2,2))
        self.slider_points = Slider(title='Number of concentration points: ', start = 3, end=20, step=1,value=9)
        self.slider_sets = Slider(title='Number of replicates:',start=1,end=9,step=1,value=1)
        self.slider_linear = Slider(title='Linear randomization', start = 0, end=25, step=0.1, value=0.2)
        self.slider_proportional = Slider(title='Proportional randomization', start = 0, end=25, step=0.1,value=0.2)
        self.refresh_button = Button(label='Refresh random data',button_type='success')
        self.add_button = Button(label='Add data to plojo',button_type='success')
        self.name_input = TextInput(title='Create Name for the data',value='Simu_Kd')
        initial_para = self.fetch_para(False)
        self.linecolors = ['green', 'red', 'blue', 'fuchsia', 'darkorange']
        self.curve=Select(title='Curve Selection', value='0', options=[(str(i),'Curve {}: {}'.format(i+1,self.linecolors[i].capitalize())) for i in range(5)  ])
        self.raw_data = ColumnDataSource(
            data=self.generate_data(**self.fetch_para(True)))
        self.fit_data = {"0": ColumnDataSource(
            data=self.generate_data(**self.fetch_para(False)))}
        self.fit_data.update({i: ColumnDataSource(
            data=self.generate_data(empty=True, **self.fetch_para(False))) for i in "1234"})
        self.copy = Button(label='Copy Curve',button_type='success')
        tools_list = "pan,ywheel_zoom,xwheel_zoom,save,reset"
        self.curve_para = {"0": self.fetch_para(False)}
        self.curve.on_change('value', self.curve_cb)

        self.p = figure(x_axis_label='Concentration (nM)', y_axis_label='Signal A.U.', x_axis_type='log',tools=tools_list)
        self.p.title.text = 'Binding Kd = {:.3g} nM; Fixed S_0 = {:.3g} nM'.format(initial_para['kd'],initial_para['s_0'])
        self.p.title_location='above'

        for curve, color in zip("01234", self.linecolors):
            temp=self.p.line('x','y', source=self.fit_data[curve],line_color=color,line_width=2) #legend='Binding Curve')
            hover_tool_1 = HoverTool(renderers=[temp],
                tooltips=[('Aptamer/nM', '@x{0.00}'), ('Signal', '@y{0}'), ('S0 / Kd (nM)',"@kd"),('NS',"@ns"),],)#mode='vline'
            self.p.add_tools(hover_tool_1)

        self.p.circle('x','y',source=self.raw_data,color='red',line_width=3)
        self.p.plot_height = 400
        self.p.plot_width = 700
        opt_input = widgetbox(para_text_,self.input_kd,self.input_conc,self.input_ns)
        options = widgetbox(para_text, self.slider_kd, self.slider_conc,
                            self.slider_ns, self.slider_Fminmax, self.curve,self.copy, self.name_input)
        rand_opt = widgetbox(rand_text,self.slider_conc_range,self.slider_points,self.slider_sets,self.slider_linear,self.slider_proportional,self.refresh_button,self.add_button)
        self.slider_kd.on_change('value',self.callback)
        self.slider_conc.on_change('value',self.callback)
        self.slider_ns.on_change('value',self.callback)
        self.slider_Fminmax.on_change('value',self.callback)
        self.slider_conc_range.on_change('value',self.callback)
        self.slider_points.on_change('value',self.callback)
        self.slider_linear.on_change('value',self.callback)
        self.slider_proportional.on_change('value',self.callback)
        self.slider_sets.on_change('value',self.callback)
        self.refresh_button.on_click(self.refresh_button_cb)
        self.add_button.on_click(self.add_button_cb)
        self.copy.on_click(self.copy_cb)
        self.layout = ([self.p],[opt_input,options,rand_opt])

    def copy_cb(self):
        curve = self.curve.value
        if self.copy.button_type=='success':
            self.copy.button_type='warning'
            self.copy.label= '<Curve{}:{}> Copied. Click to Paste'.format(int(curve)+1, self.linecolors[int(curve)].capitalize())
        else:
            self.copy.button_type='success'
            copyed = str(int(self.copy.label[6])-1)
            self.copy.label="Copy Curve"
            self.curve_cb(1,1,copyed)

    def callback(self,attr,old,new):
        curve = self.curve.value
        self.curve_para[curve] = self.fetch_para(False)
        self.fit_data[curve].data = self.generate_data(**self.fetch_para(False))
        self.raw_data.data = self.generate_data(**self.fetch_para(True))
        para = self.fetch_para(True)
        Fmax = self.slider_Fminmax.value[1]
        kd = 10 ** self.slider_kd.value
        self.input_conc.value = str(10 ** self.slider_conc.value)
        self.input_kd.value = str(kd)
        self.input_ns.value = str(self.slider_ns.value * Fmax/(kd*5000))
        self.p.title.text = self.title_generator(para)

    def generate_data(self,empty=False,kd=1,s_0=1,ns=0,Fmax=10000,Fmin=1000,start=None,end=None,point=100,randomize =False,linear=0.001,proportional=0.001,sets=1,**kwargs):
        if empty:
            return {'x':[],'y':[]}
        if start == None and end == None:
            i_0 = np.geomspace(kd / 1000, kd * 1000, 100)
        else:
            i_0= np.geomspace(start,end,point)
        if randomize:
            dict_ = {'x':np.repeat(i_0,sets), 'y':self.randomizer(self.solve_binding(np.repeat(i_0,sets), kd, s_0,ns,Fmax,Fmin),linear=linear,proportional=proportional,**kwargs)}
        else:
            dict_ = {'x':i_0, 'y':self.solve_binding(i_0, kd, s_0,ns,Fmax,Fmin),
                     'kd': ["{:.2g} / {:.2g}".format(s_0,kd)]*len(i_0), 'ns': ["{:.2g}".format(ns)]*len(i_0) }
        return dict_

    def fetch_para(self,randomize):
        kd = 10 ** self.slider_kd.value
        s_0 = 10 ** self.slider_conc.value
        sets=self.slider_sets.value
        Fmax = self.slider_Fminmax.value[1]
        ns = self.slider_ns.value * Fmax/(kd*5000)
        Fmin = self.slider_Fminmax.value[0]
        start = 10**self.slider_conc_range.value[0]
        end = 10**self.slider_conc_range.value[1]
        points = self.slider_points.value
        linear = self.slider_linear.value/100
        proportional = self.slider_proportional.value/100
        if randomize:
            result = dict(kd=kd,s_0=s_0,ns=ns,Fmax=Fmax,Fmin=Fmin,start=start,end=end,point=points,randomize=True,linear=linear,proportional=proportional,sets=sets)
        else:
            result = dict(kd=kd,s_0=s_0,ns=ns,Fmax=Fmax,Fmin=Fmin)
        return result

    def curve_cb(self,attr,old,new):
        if self.curve_para.get(new,None):
            para = self.curve_para[new]
            self.slider_kd.value = np.log10(para['kd'])
            self.slider_conc.value = np.log10(para['s_0'])
            self.slider_ns.value = para['ns']*para['kd']*5000/para['Fmax']
            self.slider_Fminmax.value = (para['Fmin'],para['Fmax'])
        else:
            self.curve_para[new]=self.curve_para[old]



    def solve_binding(self,i_0, kd_func, s_0func,ns=0,Fmax=10000,Fmin=1000): # i_0 is np array,
        s_free =((s_0func-kd_func-i_0)+np.sqrt((kd_func+i_0)**2+s_0func**2+2*kd_func*s_0func-2*i_0*s_0func))*0.5
        si = s_0func-s_free
        signal = (Fmax-Fmin)*si/s_0func + Fmin + ns*i_0
        return signal

    def randomizer(self,signal,linear=0.001, proportional=0.001,seed=42):
        np.random.seed(seed)
        size = len(signal)
        max_sig = max(signal)
        return signal * np.random.normal(loc=1,scale=proportional,size=size) + max_sig*np.random.normal(loc=0,scale=linear,size=size)

    def title_generator(self,para_dict):
        kd = para_dict['kd']
        s_0 = para_dict['s_0']
        ns = para_dict['ns']
        Fmax = para_dict['Fmax']
        Fmin = para_dict['Fmin']
        title = 'Kd:{:.3g}nM; S_0:{:.3g}nM; NS:{:.3g}AU/nM; Fmax:{:.3g}, Fmin:{:.3g}'.format(kd, s_0,ns,Fmax,Fmin)
        return title

    def refresh_button_cb(self):
        seed = np.random.randint(90000)
        self.raw_data.data = self.generate_data(**self.fetch_para(True),seed=seed)

    def add_button_cb(self):
        plojo_data = plojo_data_init()
        new_entry=plojo_data.next_exp(1)[0]
        new_index = False
        for key in plojo_data.index.keys():
            if 'Simuojo' in key:
                new_index = key
        if not new_index:
            new_index = plojo_data.new_index('Simuojo Data')
        concentration=list(self.raw_data.data['x'])
        signal=list(self.raw_data.data['y'])
        name=self.name_input.value
        para = self.fetch_para(True)
        tags = self.title_generator(para)
        notes = self.title_generator(para) + '; R_l:{:.3g}; R_p:{:.3g}'.format(self.fetch_para(True)['linear'],self.fetch_para(True)['proportional'])
        dict_tosave = dict(date='SimuDate',concentration=concentration,signal=signal,tag=tags,note=notes,fit_method='kd',author='simu',name=name)
        plojo_data.experiment[new_entry]=dict_tosave
        plojo_data.index[new_index].add(new_entry)
        plojo_data.experiment_to_save.update({new_entry:'sync'})
        plojo_data.save_experiment()
        self.p.title.text='Data Saved to plojo.'

class ric50_simu():
    """
    R + V = RV kd_1
    V + A = AV kd_2
    RV is signal
    change A conc.
    r_0, v_0, a_0, kd_1, kd_2 = initial_condition
    r,v,a,rv,av = input_value
    """
    def __init__(self):

        para_text = PreText(text='Binding Parameters')
        para_text_ = PreText(text='Binding Parameters')
        self.slider_kd_1 = Slider(title='log(Receptor-VEGF Kdr) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_kd_2 = Slider(title='log(Aptamer-VEGF Kda) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_r_0 = Slider(title='log(Receptor conc.) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_v_0 = Slider(title='log(VEGF conc.) (nM)', start=-3, end=3, step=0.01, value=0)
        self.slider_Fminmax = RangeSlider(title = 'Singal Range AU', start =0, end =100000,step =1000,value =(1000,10000))
        self.name_input = TextInput(title='Create Name for the data',value='Simu_RIC50')
        rand_text = PreText(text='Randomization Parameters')
        self.slider_conc_range =RangeSlider(title= 'Experiment Conc. (log nM) : ',  start = -5, end=5, step=0.01,value=(-2,2))
        self.slider_points = Slider(title='Number of concentration points: ', start = 3, end=20, step=1,value=9)
        self.slider_sets = Slider(title='Number of replicates:',start=1,end=9,step=1,value=1)
        self.slider_linear = Slider(title='Linear randomization', start = 0, end=25, step=0.1, value=0.2)
        self.slider_proportional = Slider(title='Proportional randomization', start = 0, end=25, step=0.1,value=0.2)
        self.input_kd_1 = TextInput(value="1", title="Receptor-VEGF Kdr (nM):")
        self.input_kd_2 = TextInput(value="1", title="Aptamer-VEGF Kda (nM):")
        self.input_r_0 = TextInput(value="1", title="Receptor Conc. (nM):")
        self.input_v_0 = TextInput(value="1", title="VEGF Conc. (nM):")
        refresh_button = Button(label='Refresh Random',button_type='success')
        add_button = Button(label='Add data to plojo',button_type='success')
        self.copy = Button(label='Copy Curve',button_type='success')
        self.linecolors = ['green', 'red', 'blue', 'fuchsia', 'darkorange']
        self.curve=Select(title='Curve Selection', value='0', options=[(str(i),'Curve {}: {}'.format(i+1,self.linecolors[i].capitalize())) for i in range(5)  ])
        para_slider = widgetbox(para_text,self.slider_kd_1,self.slider_r_0,self.slider_kd_2,self.slider_v_0,self.slider_Fminmax,self.curve,self.copy,self.name_input)
        para_input = widgetbox(para_text_,self.input_kd_1,self.input_r_0,self.input_kd_2,self.input_v_0)
        rand_opt = widgetbox(rand_text,self.slider_conc_range,self.slider_points,self.slider_sets,self.slider_linear,self.slider_proportional,refresh_button,add_button)

        self.curve_para = {"0": self.fetch_para(False)}
        self.curve.on_change('value', self.curve_cb)
        self.fit_data = {"0": ColumnDataSource(data=self.generate_plotdata(**self.fetch_para(False)))}
        self.fit_data.update({i: ColumnDataSource(
            data=self.generate_plotdata(empty=True,**self.fetch_para(False))) for i in "1234"})

        self.raw_data = ColumnDataSource(data=self.generate_plotdata(**self.fetch_para(True)))
        self.p = figure(x_axis_label='Aptamer (nM)', y_axis_label='Receptor-VEGF %Signal/A.U.', x_axis_type='log')

        self.p.title.text = 'Receptor-VEGF complex / Receptor percentage'
        self.p.title_location='above'
        for curve,color in zip("01234",self.linecolors):
            temp=self.p.line('a_0','rv_per', source=self.fit_data[curve],line_color=color,line_width=2)
            hover_tool_1 = HoverTool(renderers=[temp],tooltips=[('IC50/nM','@ic50'),
                ('Rcpt Conc / Kd', '@kdr'),('VEGF conc / Aptamer Kd', '@kda')],) #mode='vline'
            self.p.add_tools(hover_tool_1)
        self.p.circle('a_0','rv_per',source=self.raw_data,color='red',line_width=3)
        self.p.plot_height = 400
        self.p.plot_width = 700

        self.slider_kd_1.on_change('value',self.callback)
        self.slider_kd_2.on_change('value',self.callback)
        self.slider_r_0.on_change('value',self.callback)
        self.slider_v_0.on_change('value',self.callback)
        self.slider_Fminmax.on_change('value',self.callback)
        self.slider_conc_range.on_change('value',self.callback)
        self.slider_points.on_change('value',self.callback)
        self.slider_linear.on_change('value',self.callback)
        self.slider_proportional.on_change('value',self.callback)
        self.slider_sets.on_change('value',self.callback)
        refresh_button.on_click(self.refresh_button_cb)
        add_button.on_click(self.add_button_cb)
        self.copy.on_click(self.copy_cb)
        self.layout =([self.p],[para_input,para_slider,rand_opt])

    def rv_solver(self,a_0, r_0, v_0, kd_r, kd_a):
        a=kd_a-kd_r
        d=-v_0*kd_a*r_0**2
        b=kd_r*r_0-2*kd_a*r_0+kd_r**2-kd_r*kd_a-kd_r*a_0+kd_r*v_0-kd_a*v_0
        c=r_0**2*kd_a+kd_r*kd_a*r_0-v_0*r_0*kd_r+2*v_0*r_0*kd_a+a_0*kd_r*r_0
        if a!=0:
            b=b.astype('complex128')
            c=c.astype('complex128')
            p=(3*a*c-b**2)/(3*a**2)
            q=(27*a**2*d-9*a*b*c+2*b**3)/(27*a**3)
            middle=((q/2)**2+(p/3)**3)**(1/2)
            left=(-q/2+middle)**(1/3)
            right=(-q/2-middle)**(1/3)
            w = (3**(1/2)*1j-1)/2
            convert=b/(3*a)
            x_1=left+right-convert
            x_2=w*left+w**2*right-convert
            x_3=w**2*left+w*right-convert
        else:
            x_1=(-c+(c**2-4*b*d)**(1/2))/(2*b)
            x_2=(-c-(c**2-4*b*d)**(1/2))/(2*b)
            x_3=np.zeros(len(a_0))
        min_rv=min(r_0,v_0)
        result=np.array([])
        for root in zip(x_1,x_2,x_3):
            real_root = [i.real for i in root if 0<i.real<min_rv]
            if real_root:
                real_root = min(real_root)
            else:
                real_root=0
            result=np.append(result,real_root)
        return result

    def copy_cb(self):
        curve = self.curve.value
        if self.copy.button_type=='success':
            self.copy.button_type='warning'
            self.copy.label= '<Curve{}:{}> Copied. Click to Paste'.format(int(curve)+1, self.linecolors[int(curve)].capitalize())
        else:
            self.copy.button_type='success'
            copyed = str(int(self.copy.label[6])-1)
            self.copy.label="Copy Curve"
            self.curve_cb(1,1,copyed)

    def randomizer(self,signal,linear=0.001, proportional=0.001,seed=42):
        np.random.seed(seed)
        size = len(signal)
        max_sig = max(signal)
        return signal * np.random.normal(loc=1,scale=proportional,size=size) + max_sig*np.random.normal(loc=0,scale=linear,size=size)

    def generate_plotdata(self,empty=False,r_0=1,v_0=1,kd_1=1,kd_2=1,Fmax=10000,Fmin=1000,start=None,end=None,point=100,randomize=False,proportional=0.001,linear=0.001,sets=1,**kwargs):
        if empty:
            return {'a_0': [], 'rv_per': []}
        if start == None and end == None:
            a_0 = np.geomspace(kd_2 / 10000, kd_2 * 10000, 100)
        else:
            a_0= np.geomspace(start,end,point)
        rv = self.rv_solver(a_0,r_0,v_0,kd_1,kd_2)
        rv_per = rv/r_0*(Fmax-Fmin)+Fmin
        if randomize:
            rv_per = self.randomizer(np.repeat(rv_per,sets),linear=linear,proportional=proportional,**kwargs)
            result_={'a_0':np.repeat(a_0,sets), 'rv_per':rv_per}
        else:
            ic50=find_ec_50(a_0,rv_per)
            result_ = {'a_0': a_0, 'rv_per': rv_per, 'ic50': ["{:.2g}".format(ic50)]*len(a_0),
                       'kdr': ["{:.2g} / {:.2g}".format(r_0, kd_1)]*len(a_0), 'kda': ["{:.2g} / {:.2g}".format(v_0,kd_2)]*len(a_0),
                       }
        return result_

    def fetch_para(self,randomize):
        kd_1 = 10 ** self.slider_kd_1.value
        kd_2 = 10 ** self.slider_kd_2.value
        r_0 = 10 ** self.slider_r_0.value
        v_0 = 10 ** self.slider_v_0.value
        sets=self.slider_sets.value
        Fmax = self.slider_Fminmax.value[1]
        Fmin = self.slider_Fminmax.value[0]
        start = 10**self.slider_conc_range.value[0]
        end = 10**self.slider_conc_range.value[1]
        points = self.slider_points.value
        linear = self.slider_linear.value/100
        proportional = self.slider_proportional.value/100
        if randomize:
            result = dict(kd_1=kd_1,kd_2=kd_2,r_0=r_0,v_0=v_0,Fmax=Fmax,Fmin=Fmin,start=start,end=end,point=points,randomize=True,linear=linear,proportional=proportional,sets=sets)
        else:
            result = dict(kd_1=kd_1, kd_2=kd_2,
                          r_0=r_0, v_0=v_0, Fmax=Fmax, Fmin=Fmin)
        return result

    def curve_cb(self, attr, old, new):
        if self.curve_para.get(new, None):
            para = self.curve_para[new]
            self.slider_kd_1.value = np.log10(para['kd_1'])
            self.slider_kd_2.value = np.log10(para['kd_2'])
            self.slider_r_0.value = np.log10(para['r_0'])
            self.slider_v_0.value = np.log10(para['v_0'])
            self.slider_Fminmax.value = (para['Fmin'], para['Fmax'])
        else:
            self.curve_para[new] = self.curve_para[old]


    def callback(self,attr,old,new):
        kd_1 = 10 ** self.slider_kd_1.value
        kd_2 = 10 ** self.slider_kd_2.value
        r_0 = 10 ** self.slider_r_0.value
        v_0 = 10 ** self.slider_v_0.value
        self.input_kd_1.value = str(kd_1)
        self.input_kd_2.value = str(kd_2)
        self.input_r_0.value = str(r_0)
        self.input_v_0.value = str(v_0)
        curve = self.curve.value
        self.curve_para[curve] = self.fetch_para(False)
        self.fit_data[curve].data = self.generate_plotdata(
            **self.fetch_para(False))
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True))
        self.p.title.text = self.title_generator(self.fetch_para(False))

    def refresh_button_cb(self):
        seed = np.random.randint(90000)
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True),seed=seed)
        self.p.title.text = self.title_generator(self.fetch_para(False))

    def title_generator(self,para_dict):
        kd_1 = para_dict['kd_1']
        kd_2 = para_dict['kd_2']
        a_0 = para_dict['r_0']
        v_0 = para_dict['v_0']
        Fmax = para_dict['Fmax']
        Fmin = para_dict['Fmin']
        title = 'kd_r:{:.3g}nM; kd_a:{:.3g}nM; r_0:{:.3g}; v_0:{:.3g}; Fmax:{:.3g}, Fmin:{:.3g}'.format(kd_1,kd_2, a_0,v_0,Fmax,Fmin)
        return title

    def add_button_cb(self):
        plojo_data=plojo_data_init()
        new_entry=plojo_data.next_exp(1)[0]
        new_index = False
        for key in plojo_data.index.keys():
            if 'Simuojo' in key:
                new_index = key
        if not new_index:
            new_index = plojo_data.new_index('Simuojo Data')
        concentration=list(self.raw_data.data['a_0'])
        signal=list(self.raw_data.data['rv_per'])
        name=self.name_input.value
        para = self.fetch_para(True)
        tags = self.title_generator(para)
        notes = self.title_generator(para) + '; R_l:{:.3g}; R_p:{:.3g}'.format(self.fetch_para(True)['linear'],self.fetch_para(True)['proportional'])
        dict_tosave = dict(date='SimuDate',concentration=concentration,signal=signal,tag=tags,note=notes,fit_method='ric_50',author='simu',name=name)
        plojo_data.experiment[new_entry]=dict_tosave
        plojo_data.index[new_index].add(new_entry)
        plojo_data.experiment_to_save.update({new_entry:'sync'})
        plojo_data.save_experiment()
        self.p.title.text='Data Saved to plojo.'

class ri50_coop_simu():
    def __init__(self):
        para_text = PreText(text='Binding Parameters')
        para_text_ = PreText(text='Binding Parameters')
        self.pretext=para_text
        self.v0 = Slider(title='VEGF concentration (nM)', start=-3, end=3, step=0.01, value=0)
        self.ka1 = Slider(title='Aptamer+VEGF  Kd1 (nM)', start=-3, end=3, step=0.01, value=0)
        self.ka2 = Slider(title='Aptamer+VEGF  Kd2 (nM)', start=-3, end=3, step=0.01, value=0)
        self.kr1 = Slider(title='Receptor+VEGF Kd1 (nM)', start=-3, end=3, step=0.01, value=0)
        self.kr2 = Slider(title='Receptor+VA   Kd2 (nM)', start=-3, end=3, step=0.01, value=0)
        self.kr3 = Slider(title='Receptor+VA2  Kd3 (nM)', start=-3, end=3, step=0.01, value=0)
        self.c1 = Slider(title='Receptor-VA Signal %', start=0, end=1, step=0.01, value=0.2)
        self.c2 = Slider(title='Receptor-VA2 Signal %', start=0, end=1, step=0.01, value=0.1)
        self.FminFmax = RangeSlider(title = 'Signal Range AU', start =0, end =100000,step =1000,value =(1000,10000))

        self.name_input = TextInput(title='Create Name for the data',value='Simu_RIC50_Coop')

        self.input_v0  = TextInput(value="1",title="VEGF concentration (nM)")
        self.input_ka1 = TextInput(value="1",title="Aptamer+VEGF  Kd1 (nM)")
        self.input_ka2 = TextInput(value="1",title='Aptamer+VEGF  Kd2 (nM)')
        self.input_kr1 = TextInput(value="1",title="Receptor+VEGF Kd1 (nM)")
        self.input_kr2 = TextInput(value="1",title="Receptor+VA   Kd2 (nM)")
        self.input_kr3 = TextInput(value="1",title="Receptor+VA2  Kd3 (nM)")


        rand_text = PreText(text='Randomization Parameters')
        self.slider_conc_range =RangeSlider(title= 'Experiment Conc. (log nM) : ',  start = -5, end=5, step=0.01,value=(-2,2))
        self.slider_points = Slider(title='Number of concentration points: ', start = 3, end=20, step=1,value=9)
        self.slider_sets = Slider(title='Number of replicates:',start=1,end=9,step=1,value=1)
        self.slider_linear = Slider(title='Linear randomization', start = 0, end=25, step=0.1, value=0.2)
        self.slider_proportional = Slider(title='Proportional randomization', start = 0, end=25, step=0.1,value=0.2)

        self.input = {'v0':self.input_v0,'ka1':self.input_ka1,'ka2':self.input_ka2,'kr1':self.input_kr1,'kr2':self.input_kr2,'kr3':self.input_kr3}
        self.slidername = ['v0','ka1','ka2','kr1','kr2','kr3','c1','c2','points','sets','linear','proportional']
        self.sliders =[self.v0,self.ka1,self.ka2,self.kr1,self.kr2,self.kr3,self.c1,self.c2,self.slider_points,self.slider_sets,self.slider_linear,self.slider_proportional]
        self.slidersdict = dict(zip(self.slidername,self.sliders))
        self.linecolors = ['green', 'red', 'blue', 'fuchsia', 'darkorange']
        self.curve=Select(title='Curve Selection', value='0', options=[(str(i),'Curve {}: {}'.format(i+1,self.linecolors[i].capitalize())) for i in range(5)  ])
        self.copy = Button(label='Copy Curve',button_type='success')

        self.curve_para = {"0": self.fetch_para(False)}
        self.curve.on_change('value', self.curve_cb)
        refresh_button = Button(label='Refresh Random',button_type='success')
        add_button = Button(label='Add data to plojo',button_type='success')
        para_slider = widgetbox(para_text,self.v0,self.ka1,self.ka2,self.kr1,self.kr2,self.kr3,self.c1 ,self.c2, self.FminFmax)
        para_input = widgetbox(para_text_,self.input_v0,self.input_ka1,self.input_ka2,self.input_kr1,self.input_kr2,self.input_kr3)
        rand_opt = widgetbox(rand_text,self.slider_conc_range,self.slider_points,self.slider_sets,self.slider_linear,self.slider_proportional,self.curve,self.copy,self.name_input,refresh_button,add_button)

        self.fit_data = {"0": ColumnDataSource(
            data=self.generate_plotdata(**self.fetch_para(False)))}
        self.fit_data.update({i: ColumnDataSource(
            data=self.generate_plotdata(empty=True, **self.fetch_para(False))) for i in "1234"})


        self.raw_data = ColumnDataSource(data=self.generate_plotdata(**self.fetch_para(True)))
        self.p = figure(x_axis_label='Aptamer (nM)', y_axis_label='Receptor-VEGF Signal/A.U.', x_axis_type='log')
        self.p.title.text = 'Receptor-VEGF RIC50 with Cooperativity'
        self.p.title_location='above'

        for curve, color in zip("01234", self.linecolors):
            p_1=self.p.line('a0','signal', source=self.fit_data[curve],line_color=color,line_width=2,legend='Signal_All')
            hover_tool_1 = HoverTool(renderers=[p_1], tooltips=[('IC50/nM', '@ec50'), ('VEGF conc/nM', '@v_0'),('Aptamer Kd/nM', '@kda'),
            ( 'Receptor Kd/nM', '@kdr' ),( 'RV Signal %', '@receptorsiganl' )],)#mode='vline'
            self.p.add_tools(hover_tool_1)

        p_2 = self.p.line('a0','signal_v', source=self.fit_data['0'],line_color='deepskyblue',line_width=1,line_dash='dotdash',legend='Signal_V')
        hover_tool_2 = HoverTool(renderers=[p_2],tooltips=[('Aptamer/nM', '@a0{0.00}'),( 'Signal_V', '@signal_v{0.00}' )],)
        self.p.add_tools(hover_tool_2)
        p_3 = self.p.line('a0','signal_va', source=self.fit_data['0'],line_color='lime',line_width=1,line_dash='dotdash',legend='Signal_VA')
        hover_tool_3 = HoverTool(renderers=[p_3],tooltips=[('Aptamer/nM', '@a0{0.00}'),( 'Signal_VA', '@signal_va{0.00}' )],)
        self.p.add_tools(hover_tool_3)
        p_4 = self.p.line(
            'a0', 'signal_va2', source=self.fit_data['0'], line_color='deeppink', line_width=1, line_dash='dotdash', legend='Signal_VA2')
        hover_tool_4 = HoverTool(renderers=[p_4], tooltips=[(
            'Aptamer/nM', '@a0{0.00}'), ('Signal_VA2', '@signal_va2{0.00}')],)
        self.p.add_tools(hover_tool_4)
        self.p.circle('a0','signal',source=self.raw_data,color='red',line_width=3,legend='Signal_All')
        self.p.plot_height = 400
        self.p.plot_width = 600
        self.p.legend.click_policy = 'hide'
        self.p.legend.location = 'top_right'
        self.p.legend.border_line_alpha = 0
        self.p.legend.background_fill_alpha = 0.1
        self.pn=figure(x_axis_label='Aptamer (nM)', y_axis_label='Solution VEGF-Aptamer Complex %', x_axis_type='log')
        self.pn.title.text = 'VEGF-Aptamer Complex / [VEGF]_0 percent in Solution'
        self.pn.title_location='above'
        p_5=self.pn.line('a0','v', source=self.fit_data['0'],line_color='deepskyblue',line_dash='dotdash',line_width=2,legend='VEGF')
        hover_tool_5 = HoverTool(renderers=[p_5],tooltips=[('Aptamer/nM', '@a0{0.00}'),( 'VEGF/%', '@v{0.0}' )],mode='vline')
        self.pn.add_tools(hover_tool_5)
        p_6=self.pn.line('a0','va', source=self.fit_data['0'],line_color='lime',line_width=2,line_dash='dotdash',legend='VA')
        hover_tool_6 = HoverTool(renderers=[p_6],tooltips=[( 'VA/%', '@va{0.0}' )],mode='vline')
        self.pn.add_tools(hover_tool_6)
        p_7 = self.pn.line(
            'a0', 'va2', source=self.fit_data['0'], line_color='deeppink', line_width=2, line_dash='dotdash', legend='VA2')
        hover_tool_7 = HoverTool(renderers=[p_7],tooltips=[( 'VA2/%', '@va2{0.0}' )],mode='vline')
        self.pn.add_tools(hover_tool_7)
        self.pn.plot_height = 400
        self.pn.plot_width = 600
        self.pn.legend.click_policy = 'hide'
        self.pn.legend.location = 'top_right'
        self.pn.legend.border_line_alpha = 0
        self.pn.legend.background_fill_alpha = 0.1
        # add callbacks
        for i in self.sliders:
            i.on_change('value',self.callback)

        self.FminFmax.on_change('value',self.callback)
        # self.FminFmax.on_change('value',self.test_cb)

        self.slider_conc_range.on_change('value',self.callback)
        refresh_button.on_click(self.refresh_button_cb)
        add_button.on_click(self.add_button_cb)
        self.copy.on_click(self.copy_cb)
        self.layout =([self.p,self.pn],[para_input,para_slider,rand_opt])

    def copy_cb(self):
        curve = self.curve.value
        if self.copy.button_type=='success':
            self.copy.button_type='warning'
            self.copy.label= '<Curve{}:{}> Copied. Click to Paste'.format(int(curve)+1, self.linecolors[int(curve)].capitalize())
        else:
            self.copy.button_type='success'
            copyed = str(int(self.copy.label[6])-1)
            self.copy.label="Copy Curve"
            self.curve_cb(1,1,copyed)

    def signal_solver(self,a0,v0,ka1,ka2,kr1,kr2,kr3,c1,c2,Fmin,Fmax,**kwargs):
        def root(a0):
            roots=np.roots([1/ka1/ka2,(2/ka1+2*v0/ka1/ka2-a0/ka1/ka2),(1+2*v0/ka1-2*a0/ka1),-a0])
            roots=[k.real for k in roots if k.imag==0 and 0<k.real<a0]
            return roots[0]
        a = np.fromiter(map(root,a0),dtype=float)
        v=v0/(1+2*a/ka1+a**2/ka1/ka2)
        va = 2*v*a/ka1
        va2= va*a/2/ka2
        r_r0=1/(1+v/kr1+va/kr2+va2/kr3)
        signal_v= (Fmax-Fmin)*(v*r_r0/kr1) + Fmin/3
        signal_va = (Fmax-Fmin)*(c1*va*r_r0/kr2) + Fmin/3
        signal_va2=(Fmax-Fmin)*(c2*va2*r_r0/kr3) + Fmin/3
        signal = signal_v+signal_va+signal_va2
        return signal,signal_v,signal_va,signal_va2,100*v/v0,100*va/v0,100*va2/v0

    def randomizer(self,signal,linear=0.001, proportional=0.001,seed=42,**kwargs):
        np.random.seed(seed)
        size = len(signal)
        max_sig = max(signal)
        return signal * np.random.normal(loc=1,scale=proportional,size=size) + max_sig*np.random.normal(loc=0,scale=linear,size=size)

    def generate_plotdata(self,empty=False,start=None,end=None,randomize=False,**kwargs):
        if empty:
            return {'a0':[], 'signal':[],'signal_v':[],'signal_va':[],'signal_va2':[],'v':[],'va':[],'va2':[]}
        if start == None and end == None:
            a_0 = np.geomspace(kwargs['ka1'] / 10000, kwargs['ka1'] * 10000, 100)
        else:
            a_0= np.geomspace(start,end,kwargs['points'])
        signal,signal_v,signal_va,signal_va2,v,va,va2 = self.signal_solver(a0=a_0,**kwargs)
        if randomize:
            signal = self.randomizer(np.repeat(signal,kwargs['sets']),**kwargs)
            result_={'a0':np.repeat(a_0,kwargs['sets']), 'signal':signal}
        else:
            ec50 = find_ec_50(a_0,signal)
            result_ = {'a0':a_0, 'signal':signal,'signal_v':signal_v,'signal_va':signal_va,'signal_va2':signal_va2,'v':v,'va':va,'va2':va2,
                       'ec50': ["{:.2g}".format(ec50)]*len(a_0), 'kda': ["{:.2g}/{:.2g}".format(kwargs['ka1'], kwargs['ka2'])]*len(a_0),
                       'kdr': ["{:.2g}/{:.2g}/{:.2g}".format(kwargs['kr1'], kwargs['kr2'], kwargs['kr3'])]*len(a_0),
                       'receptorsiganl': ["{:.0%}/{:.0%}".format(kwargs['c1'], kwargs['c2'])]*len(a_0), 'v_0': ["{:.2g}".format(kwargs['v0'])]*len(a_0)}
        return result_

    def fetch_para(self,randomize):
        result={}
        for k,i in self.slidersdict.items():
            if k.startswith(('v','a','k')):
                result.update({k:10**i.value})
            elif k=='linear' or k=='proportional':
                result.update({k:i.value/100})
            else:result.update({k:i.value})

        result.update(Fmax= self.FminFmax.value[1])
        result.update( Fmin=self.FminFmax.value[0])
        if randomize:
            result.update(start = 10**self.slider_conc_range.value[0])
            result.update(end = 10**self.slider_conc_range.value[1],randomize=True)
        return result

    def curve_cb(self, attr, old, new):
        if self.curve_para.get(new, None):
            para = self.curve_para[new]
            for k,i in self.slidersdict.items():
                if k.startswith(('v','k')):
                    i.value=np.log10(para[k])
                elif k.startswith('c'):
                    i.value=para[k]
            self.FminFmax.value = (para['Fmin'], para['Fmax'])
        else:
            self.curve_para[new] = self.curve_para[old]


    def callback(self,attr,old,new):
        for k,i in self.input.items():
            i.value=str(10**self.slidersdict[k].value)
        curve=self.curve.value
        self.p.title.text='Receptor-VEGF RIC50 with Cooperativity'
        self.curve_para[curve] = self.fetch_para(False)
        self.fit_data[curve].data = self.generate_plotdata(**self.fetch_para(False))
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True))

    def refresh_button_cb(self):
        seed = np.random.randint(90000)
        self.raw_data.data = self.generate_plotdata(**self.fetch_para(True),seed=seed)
        # self.p.title.text = self.title_generator(self.fetch_para(False))

    def title_generator(self,para_dict):
        title=""
        for k,i in para_dict.items():
            title+="{}:{:.3g}; ".format(k,i)
        return title

    def add_button_cb(self):
        plojo_data=plojo_data_init()
        new_entry=plojo_data.next_exp(1)[0]
        new_index = False
        for key in plojo_data.index.keys():
            if 'Simuojo' in key:
                new_index = key
        if not new_index:
            new_index = plojo_data.new_index('Simuojo Data')
        concentration=list(self.raw_data.data['a0'])
        signal=list(self.raw_data.data['signal'])
        name=self.name_input.value
        para = self.fetch_para(True)
        tags = "Simu RIC50 Coop Data"
        notes = self.title_generator(para)
        dict_tosave = dict(date='SimuDate',concentration=concentration,signal=signal,tag=tags,note=notes,fit_method='ic_50',author='simu',name=name)
        plojo_data.experiment[new_entry]=dict_tosave
        plojo_data.index[new_index].add(new_entry)
        plojo_data.experiment_to_save.update({new_entry:'sync'})
        plojo_data.save_experiment()
        self.p.title.text='Data Saved to plojo.'
