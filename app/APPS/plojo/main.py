from bokeh.plotting import figure, ColumnDataSource
from bokeh.io import curdoc
from bokeh.models import HoverTool, Plot,CustomJS,Band
from bokeh.models.glyphs import Text
from bokeh.models.widgets import Div,Panel, Tabs, Button, TextInput, Select, MultiSelect, RadioButtonGroup, PreText, DataTable, TableColumn, TextAreaInput,Dropdown
from bokeh.layouts import widgetbox, row, column, layout
from bokeh.palettes import Category10
import numpy as np
import fit_binding as fb
import datetime,time
from os import path
import os,copy
import glob
import base64
import shelve
from dotenv import load_dotenv
from plojo_sql import Data

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

load_dotenv(os.path.join(basedir, '.env'))

# to start server:
#
#@echo off
#set root=C:\Users\aptitude\Anaconda3
#call %root%\Scripts\activate.bat %root%
#bokeh serve --allow-websocket-origin 192.168.86.29:5006 "C:\Users\aptitude\CloudStation\R&D\Projects\Hui Kang\Scripts\plojo\plojo.py"

# common variables:
global bounds_temp_saver,copyed_items,info_change_keep, raw_data, current_time, info_deque_holder,plot_scale,plot_format,temp_data_to_save
plot_scale = 'log'
plot_CI = 'hide'
copyed_items = {}
bounds_temp_saver = {}
plot_format = 'canvas'
info_deque_holder = ['Welcome!']*3
info_change_keep = dict.fromkeys(
    ['name','author', 'date','tag', 'note', 'fit_method', 'assay_type','flag'], False)
current_time = datetime.datetime.now()
upload_file_source = ColumnDataSource({'file_contents':[],'file_name':[]})

raw_data=Data()


assay_type_options = ['beads-kd', 'beads-ic_50', 'beads-ric_50','assay-linear','N/A']
search_field_options = [('name','Experiment Name'),('date', 'Experiment Date'), ('tag', 'Experiment Tag'),('flag','Flag'), ('note', 'Note'), ('author', 'Author'),
                        ('fit_method', 'Fit Method')]
dropdown_opt_menu = [('Mark Outlier','outlier'),None,('Show 95% CI','show'),('Hide 95% CI','hide'),None,('X-axis Linear scale','linear'),('X-axis Log scale','log'),None,('Plot in SVG format','svg'),('Plot in PNG format','canvas')]
# help_button_menu=[('Simuojo','http://localhost:5001/simuojo'),None,('Plojo/Simuojo Help Doc','http://localhost:5006/plojo_help')]
plot_ = figure(plot_width=600, plot_height=400)
plot_.annulus(x=[1, 2, 3], y=[1, 2, 3], alpha=0.5,color="hotpink",
              inner_radius=0.2, outer_radius=0.5)
#update note
updatenote = ColumnDataSource(dict(x=[1],y=[2],text=['Update:\n1. Check out plojo help document for more information.']))
update_ = Text(x='x', y='y', text='text',text_font_size='12pt',text_font='helvetica')
plot_.add_glyph(updatenote,update_)
norm_plot = figure(plot_width=600, plot_height=400)
norm_plot.annulus(x=[1, 2, 3], y=[1, 2, 3], color="orangered",
              inner_radius=0.2, outer_radius=0.5)

# functions
def project_menu_generator():
    menu = [(i,i) for i in raw_data.index.keys()]
    menu = sorted(menu, key = lambda x:int(x[0].split('-')[0]))
    result = [('recent','Recent Upload')]
    result.extend(menu)
    return result

def project_list_cb(attr,old,new):
    selection = set()
    for j in new:
        if j == 'recent':
            all_entry = set()
            for i,j in raw_data.index.items():
                all_entry.update(j)
            all_entry=list(all_entry)
            all_entry=sorted(all_entry,key=lambda x:int(x.split('-')[0][3:]))
            selection.update(all_entry[-50:])
        else:
            selection.update(raw_data.index[j])
    raw_data.load_experiment(selection)
    raw_data.exp_selection = selection
    cf_select_data.options = menu_generator(selection)
    cf_select_data.title='Select Experiment Data To View ( ' + str(len(cf_select_data.options)) + ' items)'
    cf_select_data.value = []

def info_deque(text):
    global info_deque_holder
    j = len(info_deque_holder)
    info_deque_holder.append(str(j)+'>>'+text)
    result = '\n'.join(info_deque_holder[-3:])
    return result

def plot_generator(source=[],**kwargs):
    global raw_data,plot_scale,plot_format,plot_CI
    color_ = Category10[10]
    tools_list = "pan,ywheel_zoom,xwheel_zoom,box_zoom,save,reset"
    p = figure(x_axis_type=plot_scale, tools=tools_list)
    p.xaxis.axis_label = 'Concentration /nM'
    p.yaxis.axis_label = 'Raw Signal A.U.'
    p.title.text = 'Raw Data'
    p.title_location = 'above'
    pn = figure(x_axis_type=plot_scale, x_range=p.x_range, tools=tools_list)
    p.output_backend=plot_format
    pn.output_backend=plot_format
    pn.xaxis.axis_label = 'Concentration /nM'
    pn.yaxis.axis_label = 'Normalized Signal A.U.'
    pn.title.text = 'Normalized Data '
    pn.title_location = 'above'
    fit_method_count=[0,0]
    need_save_ = any([not raw_data.experiment[i].get('fit_para',False) for i in source])
    if len(source)>10:
        info_box.text = info_deque('Only first 10 selections will be plotted.')
    if len(source) == 1:
        alpha = 1
    else:
        alpha = 0.5
    for i, j in zip(source, color_):
        data = raw_data.experiment[i]
        name=raw_data.experiment[i].get('name','No_Name')
        fit_result = fb.generate_cds(data, **kwargs)
        signal_min = data['signal'][data['concentration'].index(min(data['concentration']))]
        signal_max = data['signal'][data['concentration'].index(max(data['concentration']))]
        if signal_min<signal_max:
            fit_method_count[0] +=1
        else:
            fit_method_count[1] +=1
        if raw_data.experiment[i].get('fit_para',{}) != fit_result['fit_para'] or raw_data.experiment[i].get('fit_para_CI',{}) != fit_result['fit_para_CI'] or raw_data.experiment[i].get('r_squared',False) != fit_result['r_squared']:
            raw_data.experiment[i].update({'fit_para': fit_result['fit_para']})
            raw_data.experiment[i].update({'fit_para_CI': fit_result['fit_para_CI']})
            raw_data.experiment[i].update({'r_squared': fit_result['r_squared']})
            raw_data.experiment_to_save.update({i:'sync'})
        if plot_CI =='show':
            p_band = Band(base='x', lower='lower', upper='upper', source=fit_result['fit_data'], level='underlay',
                fill_alpha=alpha*0.3, fill_color=j) #line_width=0, line_color=j
            p.add_layout(p_band)
            pn_band = Band(base='x', lower='lower_n', upper='upper_n', source=fit_result['fit_data'], level='underlay',
                fill_alpha=alpha*0.3, fill_color=j) #line_width=0, line_color=j
            pn.add_layout(pn_band)
        p.cross('concentration', 'signal',
                source=fit_result['outlier'], angle=80, size=20, line_width=2, color='red',alpha=alpha)
        p.circle(
            'x', 'y', source=fit_result['raw_data'], color=j, line_width=2, legend=name,alpha=alpha)
        p_data_hover = HoverTool(
            tooltips=[('x: ', '@x{0.00}'), ('y: ', '@y{0,0.00}')])
        p.add_tools(p_data_hover)
        p_temp = p.line(
            'x', 'y', source=fit_result['fit_data'], color=j, line_width=2, legend=name,alpha=alpha)
        p_hover = HoverTool(renderers=[p_temp], tooltips=fit_result['tooltip'])
        p.add_tools(p_hover)
        pn.circle(
            'x', 'yn', source=fit_result['raw_data'], color=j, line_width=2, legend=name,alpha=alpha)
        pn_temp = pn.line(
            'x', 'yn', source=fit_result['fit_data'], color=j, line_width=2, legend=name,alpha=alpha)
        pn_hover = HoverTool(
            renderers=[pn_temp], tooltips=fit_result['tooltip'])
        pn_data_hover = HoverTool(renderers=[pn_temp],
            tooltips=[('x: ', '@x{0.00}'), ('y: ', '@yn{0,0}')])
        pn.add_tools(pn_data_hover)
        pn.add_tools(pn_hover)
    if kwargs.get('mark_outlier', False):
        p.cross('x', 'y', source=kwargs['mark_outlier'],
                angle=80, size=20, line_width=2, color='red')
    if fit_method_count[0]==0:
        p.legend.location = 'top_right'
        pn.legend.location = 'top_right'
    elif fit_method_count[1]==0:
        p.legend.location = 'top_left'
        pn.legend.location = 'top_left'
    elif fit_method_count[0]>fit_method_count[1]:
        p.legend.location = 'center_left'
        pn.legend.location = 'center_left'
    else:
        p.legend.location = 'center_right'
        pn.legend.location = 'center_right'
    p.legend.click_policy = 'hide'
    p.legend.border_line_alpha = 0
    p.legend.background_fill_alpha = 0.1
    p.plot_height = 400
    p.plot_width = 600
    pn.legend.click_policy = 'hide'
    pn.legend.border_line_alpha = 0
    pn.legend.background_fill_alpha = 0.1
    pn.plot_height = 400
    pn.plot_width = 600
    if need_save_:
        save_data()
    return p, pn

# fitting related functions
def fit_method_para_reader(fit_method, selected_items=[]):
    if fit_method == 'kd':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_kd_bound, cf_Fmax_bound, cf_Fmin_bound]
        cf_fit_method.value = 'kd'
        cf_kd_bound.value, cf_Fmax_bound.value, cf_Fmin_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'DR_4PL':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_ec_50_bound, cf_Fmax_bound, cf_Fmin_bound,cf_Hill_bound]
        cf_fit_method.value = 'DR_4PL'
        cf_ec_50_bound.value, cf_Fmax_bound.value, cf_Fmin_bound.value,cf_Hill_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'DR_5PL':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_ec_50_bound, cf_Fmax_bound, cf_Fmin_bound,cf_Hill_bound,cf_S_bound]
        cf_fit_method.value = 'DR_5PL'
        cf_ec_50_bound.value, cf_Fmax_bound.value, cf_Fmin_bound.value,cf_Hill_bound.value,cf_S_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'linear':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_slope_bound, cf_b_bound]
        cf_fit_method.value = 'linear'
        cf_slope_bound.value,cf_b_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'ic_50':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_ic_50_bound, cf_Fmax_bound, cf_Fmin_bound]
        cf_fit_method.value = 'ic_50'
        cf_ic_50_bound.value, cf_Fmax_bound.value, cf_Fmin_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'ric_50':
        cf_fit_bound.children = [cf_fit_method, cf_r0_bound, cf_v0_bound,
                                 cf_kd_r_bound, cf_kd_a_bound, cf_Fmax_bound, cf_Fmin_bound]
        cf_fit_method.value = 'ric_50'
        cf_r0_bound.value, cf_v0_bound.value, cf_kd_r_bound.value, cf_kd_a_bound.value, cf_Fmax_bound.value, cf_Fmin_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'kd_with_depletion':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_kd_bound,cf_a_0_bound, cf_Fmax_bound, cf_Fmin_bound]
        cf_fit_method.value = 'kd_with_depletion'
        cf_kd_bound.value, cf_a_0_bound.value,cf_Fmax_bound.value, cf_Fmin_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'kd_ns':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_kd_bound,cf_ns_bound, cf_Fmax_bound, cf_Fmin_bound]
        cf_fit_method.value = 'kd_ns'
        cf_kd_bound.value, cf_ns_bound.value,cf_Fmax_bound.value, cf_Fmin_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'kd_ns_w_depletion':
        cf_fit_bound.children = [cf_fit_method,
                                 cf_kd_bound,cf_ns_bound,cf_a_0_bound,cf_Fmax_bound, cf_Fmin_bound]
        cf_fit_method.value = 'kd_ns_w_depletion'
        cf_kd_bound.value, cf_ns_bound.value,cf_a_0_bound.value,cf_Fmax_bound.value, cf_Fmin_bound.value = bounds_formatter(
            selected_items, fit_method)
    elif fit_method == 'hplc':
        cf_fit_method.value = 'hplc'
        cf_fit_bound.children = [cf_fit_method]
    else:
        cf_fit_bound.children = [cf_fit_method]
        cf_fit_method.value = 'various'

def bounds_formatter(sele, fit_method):
    """
    format bounds of a selection of raw data to string foramt.
    """

    if len(set([raw_data.experiment[i].get('fit_method', 'kd') for i in sele])) > 1:
        info_box.text = info_deque('Selection not unique.')
    bounds = [raw_data.experiment[i].get('bounds', {}) for i in sele]

    def list_formatter(bounds, tag):
        r = ','.join([str(i.get(tag)[0])+'-'+str(i.get(tag)[1]) if i.get(tag,
                                                                         'default') != 'default' else 'default' for i in bounds])
        return r
    kd = list_formatter(bounds, 'kd')
    a_0 = list_formatter(bounds,'a_0')
    Fmax = list_formatter(bounds, 'Fmax')
    Fmin = list_formatter(bounds, 'Fmin')
    ns = list_formatter(bounds,'ns')
    ic_50 = list_formatter(bounds, 'ic_50')
    r_0 = list_formatter(bounds, 'r_0')
    v_0 = list_formatter(bounds, 'v_0')
    kd_r = list_formatter(bounds, 'kd_r')
    kd_a = list_formatter(bounds, 'kd_a')
    ec_50 = list_formatter(bounds,'ec_50')
    Hill = list_formatter(bounds,'Hill')
    S = list_formatter(bounds,'S')
    slope = list_formatter(bounds,'slope')
    b = list_formatter(bounds,'b')
    if fit_method == 'kd':
        result = (kd, Fmax, Fmin)
    elif fit_method == 'ic_50':
        result = (ic_50, Fmax, Fmin)
    elif fit_method == 'ric_50':
        result = (r_0, v_0, kd_r, kd_a, Fmax, Fmin)
    elif fit_method == 'kd_with_depletion':
        result = (kd,a_0,Fmax,Fmin)
    elif fit_method == 'kd_ns':
        result = (kd,ns,Fmax,Fmin)
    elif fit_method == 'kd_ns_w_depletion':
        result = (kd,ns,a_0,Fmax,Fmin)
    elif fit_method == 'DR_4PL':
        result = (ec_50,Fmax,Fmin,Hill)
    elif fit_method == 'DR_5PL':
        result = (ec_50,Fmax,Fmin,Hill,S)
    elif fit_method == 'linear':
        result = (slope,b)
    else:
        pass
    return result

def parser(string):
    list_string = string.split(',')
    for idx, text in enumerate(list_string):
        if ':' in text:
            try:
                list_string[idx] = [float(i) if i != '' else [
                                          0, np.inf][j] for j, i in enumerate(text.split(':'))]
                assert len(list_string[idx]) == 2
            except:
                info_box.text = info_deque(
                    'Bound is not a range, use default instead.')
                raise NameError('no valid input')
        elif '-' in text:
            try:
                list_string[idx] = [float(i) if i != '' else [
                                          0, np.inf][j] for j, i in enumerate(text.split('-'))]
                assert len(list_string[idx]) == 2
            except:
                info_box.text = info_deque(
                    'Bound is not a range, use default instead.')
                raise NameError('no valid input')
        elif text == 'default' or text == '':
            list_string[idx] = 'default'
        else:
            info_box.text = info_deque('Bound is not a range,try again.')
            raise NameError('not valid input')
    return list_string

def dict_getter(sele_list, valuelist, namelist):
    sele_length = len(sele_list)
    for idx,i in enumerate(valuelist):
        if len(i)==sele_length:
            pass
        elif len(i)<sele_length:
            info_box.text = info_deque('bounds too short, fill with last element.')
            valuelist[idx].extend([i[-1] for j in range(sele_length-len(i))])
        else:
            info_box.text = info_deque('bounds too long,omit rest.')
            valuelist[idx]=valuelist[idx][0:sele_length]
    a = [dict(zip(namelist, [j[i_]for j in valuelist]))
         for i_ in range(sele_length)]
    return dict(zip(sele_list, a))

def bounds_generator():
    selected_items = cf_focused_select_data.value
    fit_method = cf_fit_method.value
    kd = parser(cf_kd_bound.value)
    ic_50 = parser(cf_ic_50_bound.value)
    r0 = parser(cf_r0_bound.value)
    a_0 = parser(cf_a_0_bound.value)
    v0 = parser(cf_v0_bound.value)
    ns = parser(cf_ns_bound.value)
    kdr = parser(cf_kd_r_bound.value)
    kda = parser(cf_kd_a_bound.value)
    Fmax = parser(cf_Fmax_bound.value)
    Fmin = parser(cf_Fmin_bound.value)
    ec_50 = parser(cf_ec_50_bound.value)
    Hill = parser(cf_Hill_bound.value)
    S = parser(cf_S_bound.value)
    slope = parser(cf_slope_bound.value)
    b = parser(cf_b_bound.value)
    if fit_method == 'kd':
        dict_of_bounds = dict_getter(
            selected_items, [kd, Fmax, Fmin], ['kd', 'Fmax', 'Fmin'])
    elif fit_method == 'ic_50':
        dict_of_bounds = dict_getter(selected_items, [ic_50, Fmax, Fmin], [
                                     'ic_50', 'Fmax', 'Fmin'])
    elif fit_method == 'ric_50':
        dict_of_bounds = dict_getter(selected_items, [r0, v0, kdr, kda, Fmax, Fmin], [
                                     'r_0', 'v_0', 'kd_r', 'kd_a', 'Fmax', 'Fmin'])
    elif fit_method == 'kd_with_depletion':
        dict_of_bounds = dict_getter(
            selected_items, [kd, a_0,Fmax, Fmin], ['kd', 'a_0','Fmax', 'Fmin'])
    elif fit_method == 'kd_ns':
        dict_of_bounds = dict_getter(
            selected_items, [kd, ns, Fmax, Fmin], ['kd', 'ns','Fmax', 'Fmin'])
    elif fit_method == 'kd_ns_w_depletion':
        dict_of_bounds = dict_getter(
            selected_items, [kd, ns, a_0,Fmax, Fmin], ['kd', 'ns','a_0','Fmax', 'Fmin'])
    elif fit_method == 'DR_4PL':
        dict_of_bounds = dict_getter(
            selected_items, [ec_50,Fmax,Fmin,Hill], ['ec_50','Fmax', 'Fmin','Hill'])
    elif fit_method == 'DR_5PL':
        dict_of_bounds = dict_getter(
            selected_items, [ec_50,Fmax,Fmin,Hill,S], ['ec_50','Fmax', 'Fmin','Hill','S'])
    elif fit_method == 'linear':
        dict_of_bounds = dict_getter(
            selected_items, [slope,b], ['slope','b'])
    elif fit_method == 'hplc':
        dict_of_bounds = {}
    else:
        pass
    return dict_of_bounds

def outlier_generator():
    """
    read the value of selected points on plot, return dict.
    """
    outlier = cf_outlier.value
    outlier_dict = {}
    if 'none' in outlier:
        outlier_dict[cf_focused_select_data.value[0]] = {'concentration':[],'signal':[]}
    else:
        conc = [float(i.split('->')[0]) for i in outlier]
        sig = [float(i.split('->')[1]) for i in outlier]
        outlier_dict[cf_focused_select_data.value[0]] = {
        'concentration': conc, 'signal': sig}
    return outlier_dict

def menu_generator(items):
    menu = []
    for i in items:
        date_ = raw_data.experiment[i].get('date', '00000000')[4:]
        name_ = raw_data.experiment[i].get('name', 'No_Name')
        tag_ =  raw_data.experiment[i].get('tag', 'No_Tag')
        gap =' '+chr(9608)+' '
        menu.append( gap.join([i+'-'+date_, name_, tag_,raw_data.experiment[i].get('assay_type', 'N/A'),]))
    result = list(zip(items, menu))
    result = sorted(result, key=lambda x: int(
        x[0].split('-')[0][3:]), reverse=True)
    return result

# utility functions
def save_data():
    global raw_data
    saves = len(raw_data.experiment_to_save.keys()) + len(raw_data.index_to_save.keys())
    raw_data.save_data()
    info_box.text = info_deque('{} changes have been saved'.format(saves))
   

def load_data(reload_menu=True,reload_data=True):
    info_box.text = info_deque('Start Loading data...')
    global raw_data
   
    if reload_data:
        raw_data = Data()
    else:
        raw_data.index = Data().index
    if reload_menu:
        project_list.options = project_menu_generator()
        project_list.value = []
        info_box.text = info_deque('Data re-Loaded.')

def sync_vd_info_widgets(selected_items):
    vd_author.value = str([raw_data.experiment[i].get('author', 'No_Author')
                           for i in selected_items]).strip('\'[]')
    vd_date.value = str([raw_data.experiment[i].get('date', 'No_Date')
                         for i in selected_items]).strip('\'[]')
    vd_name.value = str([raw_data.experiment[i].get('name', 'No_Name')
                           for i in selected_items]).strip('\'[]')
    vd_tag.value = str([raw_data.experiment[i].get('tag', 'No_Tag') for i in selected_items]).strip('\'[]')
    vd_note.value = str([raw_data.experiment[i].get('note', 'No_Note')
                         for i in selected_items]).strip('\'[]')
    vd_flag.value = str([raw_data.experiment[i].get('flag', 'No_flag')
                           for i in selected_items]).strip('\'[]')
    vd_fit_method.value = str(
        ([raw_data.experiment[i].get('fit_method', 'N/A') for i in selected_items])).strip('[]\'')

    if len(set([raw_data.experiment[i].get('assay_type', 'N/A') for i in selected_items])) == 1:
        assay_type = raw_data.experiment[selected_items[0]].get('assay_type', 'N/A')
    else:
        assay_type = 'N/A'
    vd_assay_type.value = assay_type
    if len(set([raw_data.experiment[i].get('fit_method', 'kd') for i in selected_items])) == 1:
        fit_method_para_reader(raw_data.experiment[selected_items[0]].get(
            'fit_method', 'kd'), selected_items)
    else:
        fit_method_para_reader('various')
    global info_change_keep
    info_change_keep = dict.fromkeys(info_change_keep, False)

def syn_plot_display(selected_items, **kwargs):
    raw_plot, norm_plot = plot_generator(selected_items, **kwargs)
    read_layout_plots.children=[raw_plot,norm_plot]
    curve_fit_plots.children=[raw_plot,norm_plot]

def sync_fitting_para(selected_items):
    fit_para_field = set()
    fitting_dict = {}
    for i in selected_items:
        fit_para_field.update(raw_data.experiment[i].get('fit_para',{}).keys())

    fitting_dict.update(idx=['idx'],name=['name'],fit_method=['fit_method'],r_squared=['r_squared'])
    fit_para_field=list(fit_para_field)
    for i in fit_para_field:
        fitting_dict.update([(i,[i])])
        fitting_dict.update([(i+'_95%CI',[i+'_95%CI'])])
    for idx in selected_items:
        fitting_dict['idx'].append(idx)
        fitting_dict['name'].append(raw_data.experiment[idx].get('name','No_name'))
        fitting_dict['r_squared'].append('{:.5f}'.format(raw_data.experiment[idx].get('r_squared',0.00)))
        fitting_dict['fit_method'].append(raw_data.experiment[idx].get('fit_method','N/A'))
        for j in fit_para_field:
            para=raw_data.experiment[idx].get('fit_para',{}).get(j,'N/A')
            lower_CI=raw_data.experiment[idx].get('fit_para_CI',{}).get('lower_CI',{}).get(j,'N/A')
            upper_CI=raw_data.experiment[idx].get('fit_para_CI',{}).get('upper_CI',{}).get(j,'N/A')
            fitting_dict[j].append('{:.4g}'.format(para) if type(para)!=str else '{}'.format(para))
            lower_CI = '{:.4g}'.format(lower_CI) if type(lower_CI)!=str else '{}'.format(lower_CI)
            upper_CI = '{:.4g}'.format(upper_CI) if type(upper_CI)!=str else '{}'.format(upper_CI)
            fitting_dict[j+'_95%CI'].append(lower_CI+' ~ '+upper_CI)
    columns=[TableColumn(field=i, title=i, width=100) for i in fitting_dict.keys()]
    datasource = ColumnDataSource(fitting_dict)
    para_source.data = datasource.data
    cf_parameter_viewer.columns=columns

def input_to_rawdata(data):
    load_data(reload_menu=False,reload_data=False)
    if data == 'None':
        info_box.text = info_deque('No data entered.')
        raise ValueError('no data input.')
    author = sd_author.value
    date = sd_date.value
    assay_type = sd_assay_type.value
    if assay_type == 'N/A':
        fit_method = 'kd'
    else:
        fit_method = assay_type.split('-')[1]
    data = data.strip('\n')
    data = [i.strip('\r').split('\t') for i in data.split('\n')]
    save_entry_list = raw_data.next_exp(len(data[0])-1)
    data_re = list(map(list, zip(*data)))
    if data_re[0][0:3] != ['tag', 'note', 'nM_Name']:
        info_box.text = info_deque(
            'Wrong Order: tag, note, nM_Name.')
        raise ValueError('input format')
    concentration = data_re[0][3:]
    result_dict = {}
    for key, value in zip(save_entry_list, data_re[1:]):
        dict_to_save = {}
        dict_to_save.update(tag=value[0], note=value[1],name=value[2],author=author, date=date, assay_type=assay_type, fit_method=fit_method)
        conc_ = []
        signal = []
        for i, j in zip(concentration, value[3:]):
            if i == '' or j == '':
                pass
            else:
                try:
                    conc_.append(float(i))
                    signal.append(float(j))
                except:
                    info_box.text = info_deque('Error: concentration or signal contain non-number values.')
        if len(conc_) == len(signal) and len(signal) > 3:
            dict_to_save.update(concentration=conc_, signal=signal)
        else:
            info_box.text = info_deque('Error: value format not correct or too few data points')
            raise ValueError('not length')
        result_dict[key] = dict_to_save
    info_box.text = info_deque('Format check passed.')
    return result_dict, save_entry_list

def sd_data_generator():
    try:
        raw_contents = upload_file_source.data['file_contents'][0]
        prefix, b64_contents = raw_contents.split(",", 1)
        file_contents = base64.b64decode(b64_contents)
        file_contents = file_contents.decode("utf-16")
        if sd_upload_opt.value == 'hplc':
            file_name = upload_file_source.data['file_name'][0].split('.')[0]
            data = '\n'.join(['tag\t'+file_name,'note\t ','nM_Name\t'+file_name,file_contents])
        elif sd_upload_opt.value == 'plojo':
            data = file_contents
        else:
            data = 'sd_data_generator_error'
    except:
        data = 'None'
    return data

def sd_load_data_to_table(data):
    if data != 'None':
        info_box.text = info_deque('Loading data...')
        data = data.strip('\n')
        data = [i.split('\t') for i in data.split('\n')]
        save_entry_list = raw_data.next_exp(len(data[0])-1)
        data_re = list(map(list, zip(*data)))
        data_field = ['Field']
        data_field.extend(save_entry_list)
        datasource = ColumnDataSource(dict(zip(data_field, data_re)))
        columns = [TableColumn(field=i, title=i, width=90) for i in data_field]
        display_layout.children[3].children[0] = DataTable(
            source=datasource, columns=columns, width=600, height=280, fit_columns=False,reorderable=True)
        info_box.text = info_deque('Check data in the table.')
    else:
        pass

def check_consistency():
    index = Data().index
    data_index = Data.all_experiment_index()
    index_ = set()
    index_.update([i for j in index.values() for i in j])
    index_x = index_ - data_index
    data_x = data_index -index_
    if index_x:
        info_box.text = info_deque('Index:{}'.format(index_x))
    elif data_x:
        info_box.text = info_deque('Data:{}'.format(data_x))
    else:
        info_box.text = info_deque('No mismatch found.')

def clean_redundancy():
    index = Data().index
    data_index = Data.all_experiment_index()
    index_ = set()
    index_.update([i for j in index.values() for i in j])
    index_x = index_ - data_index
    data_x = data_index -index_
    if index_x:
        for i in raw_data.index.keys():
            if index_x & raw_data.index[i]:
                raw_data.index[i] -= index_x
                raw_data.index_to_save.update({i:'sync'})
        info_box.text = info_deque('Index removed: {}'.format(index_x))
        
    elif data_x:
        raw_data.index['0-temporary'].update(data_x)
        info_box.text = info_deque('Added to temporary: {}'.format(data_x))
        raw_data.index_to_save.update({'0-temporary':'sync'})
    else:
        info_box.text = info_deque('No mismatch found.')
    save_data()

def active_selected_item():
    if data_outlier_tab.active == 1 and button_mode.active != 0:
        to_delete = cf_select_data.value
    elif data_outlier_tab.active == 2 and button_mode.active != 0:
        to_delete = cf_focused_select_data.value
    else:
        info_box.text = info_deque('Go to Experiment/To Plot tab.')
        raise ValueError(' go to experiment/To Plot tab')
        # to_delete = []
    return to_delete

# widgets
button_mode = RadioButtonGroup(labels=[
                               'Upload', 'Browse', 'Fitting'], active=0, button_type='warning',width=230)
# button_mode = Dropdown(label='Plojo', value='none', menu=[('View Data','view'),('Curve Fitting','fit'),('Upload Data','upload')],button_type='success', width=120)
info_box = PreText(text='Welcome!',width=300)
edit_dropdown_menu = [('Copy Fit Para','copy_para'),('Paste Fit Para','paste_para'),None,('Alias/Merge Data','alias'),None,('Cut Data','cut'),('Copy Data','copy'),('Paste Data','paste'),None,('Check Consistency','check'),('Align Index','align')]
edit_dropdown = Dropdown(label='Edit', button_type='success',value='none',menu = edit_dropdown_menu,width=130)
button_load = Button(label='Load', button_type='success',width =130)
button_save = Button(label='Save', button_type='danger',width =130)

cf_assay_type = MultiSelect(
    title='Assay Type', value=assay_type_options, options=assay_type_options, size=5)
cf_filter = TextInput(title='Key:AND/OR/NOT/ANY | Enter Alias')
cf_search_field = MultiSelect(title='Search field:', value=[
                              'tag', 'note', 'fit_method'], options=search_field_options, size=7)
cf_select_data = MultiSelect(title='Select Experiment Data To View',
                             options=menu_generator([]), size=30, width=600)
cf_outlier = MultiSelect(
    title='Mark Data Points As Outlier', options=[], size=30, width=600)
# cf_parameter_viewer = PreText(text='Fitting Result:\n', width=600, height=160)
para_source = ColumnDataSource({'name':[1]})
columns=[TableColumn(field='name', title='n', width=90)]
cf_parameter_viewer =DataTable(width=600, height=160,columns=columns, source=para_source,fit_columns=False,reorderable=True,editable=True,header_row=True,index_position=None)
cf_focused_select_data = MultiSelect(
    title='Data of interest', options=[], size=30, width=600)
project_list = MultiSelect(title='Project List',options=project_menu_generator(),size=25,width=370)
project_name = TextInput(title='Project Name',value='Enter a name',width=150)
project_dropdown = Dropdown(width=150,label='Edit Project',button_type='success',value='none',menu=[('New Project','create'),('Rename Project','rename'),None,('Delete Project','delete')])

project_tab = row(project_list, column(project_name, project_dropdown),)
data_outlier_tab = Tabs(active=0, width=600, height=550, tabs=[Panel(child=project_tab,title='Project'),Panel(child=cf_select_data, title="Experiment"), Panel(
    child=cf_focused_select_data, title='To Plot'), Panel(child=cf_outlier, title="Raw Data"), Panel(child=cf_parameter_viewer, title='Fitting Result')])
vd_save_info = Button(label='Save Info', button_type='danger',width=140)
vd_delete_data = Button(label='Delete Data', button_type='warning',width=140)
plot_dropdown = Dropdown(label='Plot', button_type='success',menu = dropdown_opt_menu,width=130)
vd_new_search = Button(label='Search',button_type='success',width=140)
vd_refine_search = Button(label='Refine',button_type='success',width=140)

vd_search_refine = row(vd_new_search,vd_refine_search)
options=column(vd_search_refine,row(vd_delete_data,vd_save_info),widgetbox(cf_filter,cf_assay_type, cf_search_field),)
vd_name = TextInput(title='Experiment Name : ')
vd_author = TextInput(title='Author :')
vd_flag = TextInput(title='Flag :')
vd_date = TextInput(title='Experiment Date :')
vd_tag = TextAreaInput(title='Tag :', rows=3, cols=35, max_length=50000)
vd_note = TextAreaInput(title='Note :', rows=5, cols=35, max_length=50000)
vd_fit_method = TextInput(title='Fit Method, edit here won\'t have effect.')
vd_assay_type = Select(title='Assay Type', value='N/A', options=assay_type_options)
vd_data_info = widgetbox(vd_name,vd_assay_type,vd_tag,vd_flag, vd_note,vd_author, vd_date, vd_fit_method)
read_layout_plots=column(plot_, norm_plot)

######## curve_fitting layout

# cf_alias_name = TextInput(title='Enter name for new data:', value='copy')
# cf_make_alias = Button(label='Creat Alias / Merge Data', button_type='primary')
# cf_copy = Button(label='Copy Fitting Para', button_type='success')
# cf_paste = Button(label='Paste Fitting Para', button_type='success')
# cf_mark_outlier = Button(label='Mark Outlier', button_type='success')
cf_fit_method = Select(title='Fit method:', value='kd',
                       options=fb.supported_fit_method)
cf_kd_bound = TextInput(title='Kd range in nM:', value='default')
cf_ic_50_bound = TextInput(title='IC50 range in nM:', value='default')
cf_a_0_bound = TextInput(title='Fixed Component Conc. in nM:', value='default')
cf_ns_bound = TextInput(title='Non Specific AU/nM : ', value='default')
cf_Fmax_bound = TextInput(title='Max Signal AU:', value='default')
cf_Fmin_bound = TextInput(title='Min Signal AU:', value='default')
cf_r0_bound = TextInput(title='Receptor Conc. in nM:', value='default')
cf_v0_bound = TextInput(title='VEGF Conc. in nM:', value='default')
cf_kd_r_bound = TextInput(title='VEGF-Receptor Kd in nM:', value='default')
cf_kd_a_bound = TextInput(title='VEGF-Aptamer Kd in nM:', value='default')
cf_ec_50_bound = TextInput(title='EC50 value in nM:', value='default')
cf_Hill_bound = TextInput(title='Hill Coefficient:', value='default')
cf_S_bound = TextInput(title='Symmetry Coefficient:', value='default')
cf_slope_bound = TextInput(title='Linear fit slope:', value='default')
cf_b_bound = TextInput(title='Y intercept:', value='default')
cf_fit_bound = widgetbox(cf_fit_method, cf_kd_bound,
                         cf_Fmax_bound, cf_Fmin_bound)
cf_fit_plot_data = Button(label='Fit and Plot', button_type='success',width=140)
cf_restore = Button(label='Reset Para', button_type='warning',width=140)

cf_select_data_widgets = column(vd_search_refine, row(cf_fit_plot_data, cf_restore),widgetbox(cf_assay_type, cf_filter, cf_search_field),)
curve_fit_plots =column(plot_, norm_plot)

#########save layout
sd_author = TextInput(title='Author', value='none')
sd_date = TextInput(title='Experiment Date',
                    value=current_time.strftime('%Y%m%d'))
sd_assay_type = Select(title='Assay Type', value='beads-kd', options=assay_type_options)
sd_row_1 = row(sd_author, sd_date, sd_assay_type)
sd_data = TextAreaInput(title='Experiment Data:',
                        rows=27, cols=70,width=600, max_length=5000000)
# sd_text = PreText(text='Select a Project')
sd_type_check = Button(label='Read Input Data', button_type='success')
sd_upload_opt_menu=[('Upload plojo template data','plojo'),('Not Available','hplc')]
sd_upload_opt = Dropdown(label='Upload Data',button_type='success',menu = sd_upload_opt_menu,value='none')
sd_save_data = Button(label='Save Input Data', button_type='danger')
source = ColumnDataSource({})
sd_data_table = DataTable(width=600, height=280, source=source)

############login layout
plot_login = Plot(title=None, plot_width=600, plot_height=201,
                  min_border=0, toolbar_location=None)
glyph_0_ = ColumnDataSource(dict(x=[0], y=[0], text=['']))
glyph_0 = Text(x='x', y='y', text='text')
glyph_00_ = ColumnDataSource(dict(x=[6], y=[3.1], text=['']))
glyph_00 = Text(x=6, y=4, text='text')
glyph_1_ = ColumnDataSource(
    dict(x=[0], y=[2.5], text=['Aptitude Medical Systems']))
glyph_1 = Text(x='x', y='y', text='text', text_color="orangered",
               text_font_size='33pt', text_font_style='bold', text_font='helvetica')
glyph_2_ = ColumnDataSource(dict(x=[1.34,3.245,4], y=[0,0.99,0.99], text=['P L @j@','~','~']))
glyph_2 = Text(x='x', y='y', text='text', text_color="darkturquoise",
               text_font_size='60pt', text_font='cursive',text_font_style='bold')
plot_login.add_glyph(glyph_0_, glyph_0)
plot_login.add_glyph(glyph_00_, glyph_00)
plot_login.add_glyph(glyph_1_, glyph_1)
plot_login.add_glyph(glyph_2_, glyph_2)
login_text = PreText(
    text="Aptitude Medical Systems, Inc.\n\n      LOG IN TO USE\n")
login_user = TextInput(placeholder="username", title="User Name:")
# login_pwd = PasswordInput(placeholder="password", title="Password:")
# login_btn = Button(label="LOGIN", width=150, button_type='success')
time_text="""<div style="text-align:center;padding:1em 0;"><h3><span style="color:gray;">Current local time in</span>
<br />Santa Barbara, United States</a></h3>
<iframe src="http://free.timeanddate.com/clock/i6nvx52g/n1050/szw110/szh110/hocbbb/hbw6/
cf100/hgr0/fas16/fdi64/mqc000/mqs4/mql20/mqw2/mqd94/mhc000/mhs3/mhl20/mhw2/mhd94/mmc000/mml10/mmw1/mmd94/hmr7/hsc000/hss1/hsl90"
frameborder="0" width="110" height="110"></iframe>
</div>"""
login_info = Div(text=time_text)


# call back functions
sd_upload_opt.callback = CustomJS(args=dict(file_source=upload_file_source), code = """
function read_file(filename) {
    var reader = new FileReader();
    reader.onload = load_handler;
    reader.onerror = error_handler;
    // readAsDataURL represents the file's data as a base64 encoded string
    reader.readAsDataURL(filename);
}

function load_handler(event) {
    var b64string = event.target.result;
    file_source.data = {'file_contents' : [b64string], 'file_name':[input.files[0].name]};
    file_source.trigger("change");
}

function error_handler(evt) {
    if(evt.target.error.name == "NotReadableError") {
        alert("Can't read file!");
    }
}

var input = document.createElement('input');
input.setAttribute('type', 'file');
input.onchange = function(){
    if (window.FileReader) {
        read_file(input.files[0]);
    } else {
        alert('FileReader is not supported in this browser');
    }
}
input.click();
""")

def button_mode_cb(attr, old, new):
    if new == 1:
        display_layout.children = read_layout.children
    elif new == 2:
        display_layout.children = curve_fit_layout.children
    else:
        display_layout.children = save_layout.children
        project_list.value = ['0-temporary']

def cf_select_data_cb(attr, old, new):
    selected_items = cf_select_data.value
    cf_focused_select_data.options = menu_generator(selected_items)
    cf_focused_select_data.title='Data of interest ( ' + str(len(cf_focused_select_data.options)) + ' items)'
    sync_vd_info_widgets(selected_items)
    sync_fitting_para(selected_items)

def cf_assay_type_cb(attr,old,new):
    search_engine(raw_data.exp_selection)

def update_select_menu(attr,old,new):
    search_engine(raw_data.exp_selection)

def vd_new_search_cb():
    search_engine(raw_data.exp_selection)

def search_engine(search_keys=[]):
    assay_type = cf_assay_type.value
    search_field = cf_search_field.value
    keyword = cf_filter.value
    if 'AND' in keyword:
        keyword = [i.strip().lower() for i in keyword.split('AND')]
        logic = 'AND'
    elif 'OR' in keyword:
        keyword = [i.strip().lower() for i in keyword.split('OR')]
        logic = 'OR'
    elif 'NOT' in keyword:
        logic = 'NOT'
        keyword = [i.strip().lower() for i in keyword.split('NOT')]
        if len(keyword)==1:
            keyword=[''].extend(keyword)
    elif 'ANY' in keyword:
        keyword = [i.strip().lower() for i in keyword.split()]
        logic='ANY'
    else:
        logic = 'ALL'
        keyword = [keyword.lower()]
    search_hit = []
    for key in search_keys:
        item=raw_data.experiment[key]
        item_type = item.get('assay_type', 'N/A')
        if item_type in assay_type:
            look = ' '.join(list(item.get(field_, ' ').lower() for field_ in search_field))
            if logic in 'ANYOR':
                if any([i in look for i in keyword]):
                    search_hit.append(key)
            elif logic in 'ALLAND':
                if all([i in look for i in keyword]):
                    search_hit.append(key)
            elif logic == 'NOT':
                if keyword[0] in look and keyword[1] not in look:
                    search_hit.append(key)
    menu = menu_generator(search_hit)
    cf_select_data.options = menu
    cf_select_data.title='Select Experiment Data To View ( ' + str(len(cf_select_data.options)) + ' items)'
    info_box.text = info_deque('{} results found!'.format(len(search_hit)))

def refine_select_menu():
    if cf_select_data.options:
        keys = [i[0] for i in cf_select_data.options]
        search_engine(keys)
    else:
        info_box.text = info_deque('Empty search scope.')


def cf_focused_select_data_cb(attr, old, new):
    selected_items = cf_focused_select_data.value
    if len(selected_items) == 1:
        conc = raw_data.experiment[selected_items[0]]['concentration']
        sig = raw_data.experiment[selected_items[0]]['signal']
        conc_outlier = raw_data.experiment[selected_items[0]].get('outlier',{'concentration':[]})['concentration']
        sig_outlier = raw_data.experiment[selected_items[0]].get('outlier',{'signal':[]})['signal']
        outlier_list= [str(i)+' -> '+str(j) for i, j in zip(conc, sig)]
        outlier_list.append('none')
        cf_outlier.options = outlier_list
        cf_outlier.value = [str(i)+' -> '+str(j) for i, j in zip(conc_outlier, sig_outlier)]
    else:
        cf_outlier.options = []
        cf_outlier.value = []
    info_box.text = info_deque('Drawing...')
    sync_vd_info_widgets(selected_items)
    syn_plot_display(selected_items)
    sync_fitting_para(selected_items)
    info_box.text = info_deque('New plot generated.')

def vd_delete_data_cb():
    global current_time
    current = datetime.datetime.now()
    if (current-current_time).total_seconds() > 2:
        current_time = datetime.datetime.now()
        info_box.text = info_deque(
            'Caution! Click again within 2s to delete data.')
        raise ValueError('click again')
    to_delete = active_selected_item()
    if len(to_delete) == 0:
        info_box.text = info_deque('Select Data in Experiment or To plot tab')
        raise ValueError('no select')
    for i in to_delete:
        del raw_data.experiment[i]
        for j,k in raw_data.index.items():
            if i in k:
                k.discard(i)
                raw_data.index_to_save.update({j:'sync'})
        raw_data.experiment_to_save.update({i:'del'})
        
    info_box.text = info_deque('Selected data was deleted.')
    cf_select_data_menu = cf_select_data.options
    selected_data = cf_select_data.value
    cf_select_data.options = [
        i for i in cf_select_data_menu if i[0] not in to_delete]
    cf_select_data.value = [i for i in selected_data if i not in to_delete]
    cf_select_data.title='Select Experiment Data To View ( ' + str(len(cf_select_data.options)) + ' items)'


def vd_author_callback(attr, old, new):
    info_change_keep.update(author=True)

def vd_name_callback(attr, old, new):
    info_change_keep.update(name=True)

def vd_date_callback(attr, old, new):
    info_change_keep.update(date=True)

def vd_flag_callback(attr, old, new):
    info_change_keep.update(flag=True)

def vd_tag_cb(attr, old, new):
    info_change_keep.update(tag=True)

def vd_note_cb(attr, old, new):
    info_change_keep.update(note=True)

def vd_assay_type_cb(attr, old, new):
    info_change_keep.update(assay_type=True)

def vd_save_info_callback():
    selected_items = active_selected_item()
    global info_change_keep
    info_box.text = info_deque('saving info...')
    new_input = dict(zip(['name','author', 'date', 'tag', 'note', 'fit_method', 'assay_type','flag'], [vd_name.value,
                     vd_author.value, vd_date.value, vd_tag.value, vd_note.value, vd_fit_method.value, vd_assay_type.value,vd_flag.value]))
    update_dict = {i: new_input[i] for i, j in info_change_keep.items() if j}
    for i in selected_items:
        raw_data.experiment[i].update(update_dict)
        raw_data.experiment_to_save.update({i:'sync'})
    info_change_keep = dict.fromkeys(info_change_keep, False)
    saved_field = list(update_dict.keys())
    cf_select_data.options = menu_generator([i[0] for i in cf_select_data.options])
    cf_focused_select_data.options = menu_generator([i[0] for i in cf_focused_select_data.options])
    info_box.text = info_deque(str(saved_field).strip('[]')+' saved.')
    save_data()

def cf_restore_callback():
    selected_items = cf_focused_select_data.value
    if len(selected_items) != 1:
        info_box.text = info_deque('Select single experiment to restore.')
        raise ValueError('select 1 item')
    raw_data.experiment[selected_items[0]].update(fit_para={}, bounds={}, outlier={
                                       'concentration': [], 'signal': []})
    cf_outlier.value = []
    info_box.text = info_deque('Fitting parameters have been reset.')

def cf_fit_method_callback(attr, old, new):
    choice = cf_fit_method.value
    selected_items = cf_focused_select_data.value
    fit_method_para_reader(choice, selected_items)

def cf_fit_plot_callback():
    info_box.text = info_deque('start fitting...')
    selected_items = cf_focused_select_data.value
    fit_method = cf_fit_method.value
    bounds = bounds_generator()
    info_box.text = info_deque('bounds data loaded...')
    outlier = outlier_generator()
    info_box.text = info_deque('outlier data loaded...')
    for i in selected_items:
        raw_data.experiment[i].update(fit_method=fit_method,
                           bounds=bounds.get(i, {}), fit_para={})
        raw_data.experiment_to_save.update({i:'sync'})
    if len(selected_items)==1:
        raw_data.experiment[selected_items[0]].update(outlier=outlier.get(i, {'concentration': [], 'signal': []}))
        raw_data.experiment_to_save.update({selected_items[0]:'sync'})
    syn_plot_display(selected_items, new_fit=True)
    sync_fitting_para(selected_items)
    info_box.text = info_deque('Fitting completed.')

def make_alias_callback():
    selected_data = active_selected_item()
    name_affix = cf_filter.value.strip() if cf_filter.value.strip() else 'Copy'
    if len(selected_data)==1:
        alias = selected_data[0] + '-' + name_affix
        info_box.text = info_deque('creating copy...')
    elif len(selected_data) > 1:
        alias = selected_data[0] + '-' + name_affix
        info_box.text = info_deque('Merging selected data...')
        a=set(raw_data.experiment[selected_data[0]]['concentration'])
        for j in selected_data[1:]:
            b=set(raw_data.experiment[j]['concentration'])
            if b != a:
                info_box.text=info_deque('Concentration doesn\'t match, cannot merge!!')
                raise ValueError('conc. match failed.')
    else:
        info_box.text = info_deque('Make selection in Tab')
        raise ValueError('selection not right.')
    if raw_data.experiment.get(alias, None) != None:
        info_box.text = info_deque('This alias already exists.')
        raise KeyError('key exist for this alias.')
    raw_data.experiment[alias] = copy.deepcopy(raw_data.experiment[selected_data[0]])
    if len(selected_data) > 1:
        for j in selected_data[1:]:
            raw_data.experiment[alias]['signal'].extend(raw_data.experiment[j]['signal'])
            raw_data.experiment[alias]['concentration'].extend(raw_data.experiment[j]['concentration'])
            raw_data.experiment[alias].update(fit_para={}, bounds={}, outlier={
                                               'concentration': [], 'signal': []})
    for i in project_list.value:
        if raw_data.index.get(i,'None') != 'None':
            if selected_data[0] in raw_data.index[i]:
                raw_data.index[i].add(alias)
    raw_data.experiment_to_save.update({alias:'sync'})
    cf_select_data.options.append(*menu_generator([alias]))
    cf_select_data.value.append(alias)
    cf_focused_select_data.value = [alias]
    cf_select_data.title='Select Experiment Data To View ( ' + str(len(cf_select_data.options)) + ' items)'
    info_box.text = info_deque('Data copy created.')


def cf_mark_outlier_callback():
    """
    mark outlier out
    """
    info_box.text = info_deque('Marking outlier ...')
    sele = cf_focused_select_data.value
    outlier = outlier_generator()
    x = outlier[sele[0]].get('concentration', [])
    y = outlier[sele[0]].get('signal', [])
    if 0 in x:
        x_o=np.array(raw_data.experiment[sele[0]].get('concentration',[]))
        min_x=min(x_o[x_o!=0])/1000.0
        x=list(map(lambda i:min_x if i ==0 else i,x))
    source = ColumnDataSource(dict(x=x, y=y))
    syn_plot_display(sele, mark_outlier=source)
    info_box.text = info_deque('Outlier marked.')

def sd_type_check_cb():
    global temp_data_to_save
    temp_data_to_save = sd_data.value
    sd_load_data_to_table(temp_data_to_save)
    upload_file_source.data={'file_contents':[],'file_name':[]}

def upload_file_source_cb(attr,old,new):
    global temp_data_to_save
    data = sd_data_generator()
    if data != 'None':
        temp_data_to_save = data
        sd_load_data_to_table(temp_data_to_save)

def sd_save_data_cb():
    global temp_data_to_save
    result, save_entry_list = input_to_rawdata(temp_data_to_save)
    if len(project_list.value) != 1 or 'recent' in project_list.value:
        info_box.text = info_deque('select 1 project to upload')
        raise ValueError('sele 1')
    else:
        project = project_list.value[0]
    info_box.text = info_deque('Start saving...')
    result_conc_list = []
    for key, item in result.items():
        result_conc_list.append(item['signal'])
        for i, j in raw_data.experiment.items():
            if item['signal'] == j['signal']:
                info_box.text = info_deque(
                    'Library record(s) collision found in input data.')
                raise KeyError('same data as in raw data')
    for idx, conc in enumerate(result_conc_list[:-1]):
        for con_2 in result_conc_list[(idx+1):]:
            if conc == con_2:
                info_box.text = info_deque(
                    'Duplicate data was found in input.')
                raise ValueError('duplicate found')
    raw_data.experiment.update(result)
    raw_data.experiment_to_save.update(dict.fromkeys(result,'sync'))
    cf_select_data.options = menu_generator(save_entry_list)
    cf_select_data.title='Select Experiment Data To View ( ' + str(len(cf_select_data.options)) + ' items)'
    raw_data.index[project].update(save_entry_list)
    save_data()
    temp_data_to_save = 'None'
    upload_file_source.data={'file_contents':[],'file_name':[]}

def login_btn_callback():
    user = login_user.value
    # password = login_pwd.value
    # if password in user_pwd.get(user, ['aptitude','ams']):
    button_mode.active = 1
    sd_author.value = user
    # else:
    #     login_text.text = 'Wrong Username/Password \n'
#
def login_user_cb(attr,old,new):
    login_btn_callback()

# def refresh_time_cb():
#     ltime = datetime.datetime.now()
#     botton_spacer.text = ("""<div style="text-align:right;"><pre>"""+'\n\n\nToday is : '+ltime.strftime('%Y-%m-%d, %a')
#                        + '\n\nCurrent time: '+ltime.strftime('%I:%M:%S %p')+"<pre>")
#     # ('<pre>'+'\n'*2+' '*53+'Today is : '+ltime.strftime('%Y-%m-%d, %a')+','
#     #                       + '\tCurrent time: '+ltime.strftime('%I:%M:%S %p')+"\n\n"+' '*77+
#     #                       """<a href="http://www.aptitudemedical.com/index.html">Aptitude Medical Systems, Inc.</a>"""+'<pre>')
#     # # login_info.text = ('Today is : '+ltime.strftime('%Y-%m-%d, %a')
#     #                    + '\nCurrent time: '+ltime.strftime('%I:%M:%S %p'))

def cf_copy_cb():
    global bounds_temp_saver
    bounds_temp_saver = {}
    info_box.text = info_deque('Copying...')
    selected_items = active_selected_item()
    if len(selected_items)==1:
        bounds_temp_saver['bounds'] = raw_data.experiment[selected_items[0]].get('bounds',{})
        bounds_temp_saver['fit_method']=raw_data.experiment[selected_items[0]].get('fit_method','kd')
        info_box.text = info_deque('Fit Para Copyed.')
    else:
        info_box.text = info_deque('select 1 in correct tab')
        raise ValueError('wrong selection')

def cf_paste_cb():
    global bounds_temp_saver
    info_box.text = info_deque('Pasting...')
    selected_items = active_selected_item()
    if len(selected_items)==0:
        info_box.text = info_deque('select in correct tab')
        raise ValueError('wrong selection')
    else:
        for i in selected_items:
            raw_data.experiment[i].update(fit_method=bounds_temp_saver['fit_method'],bounds=bounds_temp_saver['bounds'], fit_para={})
            raw_data.experiment_to_save.update({i:'sync'})
    sync_vd_info_widgets(selected_items)
    info_box.text = info_deque('Fitting Para Pasted.')

def plot_dropdown_cb(attr,old,new):
    global plot_scale,plot_format,plot_CI
    plot_dropdown.value = 'none'
    if new == 'none':
        pass
    elif new in ['log','linear','svg','canvas','hide','show']:
        if new in ['log','linear']:
            plot_scale = new
            info_box.text = info_deque('X_scale changed to {}'.format(new))
        elif new in ['svg','canvas']:
            plot_format = new
            info_box.text = info_deque('Plot format changed to {}'.format(new))
        elif new in ['hide','show']:
            plot_CI = new
            info_box.text = info_deque('Plot {} 95% confidence interval.'.format(new))
        selected_items = cf_focused_select_data.value
        syn_plot_display(selected_items)
    elif new == 'outlier':
        cf_mark_outlier_callback()


def edit_dropdown_cb(attr,old,new):
    global copyed_items
    edit_dropdown.value = 'none'
    if new == 'none':
        pass
    elif new == 'copy_para':
        cf_copy_cb()
    elif new == 'paste_para':
        cf_paste_cb()
    elif new == 'alias':
        make_alias_callback()
    elif new in ['cut','copy']:
        try:
            selected_items = active_selected_item()
            copyed_items = {new:set(selected_items)}
            info_box.text = info_deque('{} {} data.'.format(new,len(selected_items)))
        except:
            pass
    elif new == 'paste':
        project = project_list.value
        if len(project) != 1 or data_outlier_tab.active != 0:
            info_box.text = info_deque('Select 1 project in project tab.')
        else:
            id = project[0]
            for key,item in copyed_items.items():
                if key == 'cut':
                    for i in raw_data.index.keys():
                        if item & raw_data.index[i]:
                            raw_data.index[i] -= item
                            raw_data.index_to_save.update({i:"sync"})
                    raw_data.index[id] |= item
                elif key == 'copy':
                    raw_data.index[id] |= item
                info_box.text = info_deque('{} data pasted.'.format(len(item)))
            raw_data.index_to_save.update({id:"sync",})
            copyed_items = {}
            project_list.options = project_menu_generator()
            project_list.value = []
            project_list.value = [id]
    elif new == 'check':
        check_consistency()
    elif new == 'align':
        clean_redundancy()


def project_dropdown_cb(attr,old,new):
    old_ = project_list.value
    try:
        if new == 'none':
            pass
        elif new == 'delete':
            if '0-temporary' in old_:
                info_box.text = info_deque('Can\'t delete temporary project.')
            else:
                for i in old_:
                    raw_data.index['0-temporary'].update(raw_data.index.pop(i))
                    raw_data.index_to_save.update({'0-temporary':'sync',i:'del'})
                    project_list.options = project_menu_generator()
                    project_list.value = []
        else:
            new_name = project_name.value
            if new_name == 'Enter a name':
                info_box.text = info_deque('Enter a Valid project name.')
            else:
                if new == 'create':
                    new_index = raw_data.new_index(new_name)
                    project_list.options = project_menu_generator()
                    raw_data.index_to_save.update({new_index:'sync'})
                    project_list.value = [new_index]
                    save_data()
                elif new == 'rename':
                    if len(old_) != 1:
                        info_box.text = info_deque('Select 1 project.')
                    else:
                        index_ = old_[0].split('-')[0]+'-'+new_name
                        raw_data.index[index_]=raw_data.index.pop(old_[0])
                        raw_data.index_to_save.update({old_[0]: index_})
                        project_list.options = project_menu_generator()
                        project_list.value = [index_]
                        save_data()
    except:
        info_box.text = info_deque('Error during project_dropdown_cb.')
    project_dropdown.value='none'

# assign callback to elements
button_load.on_click(load_data)
button_save.on_click(save_data)
button_mode.on_change('active', button_mode_cb)
cf_focused_select_data.on_change('value', cf_focused_select_data_cb)
cf_select_data.on_change('value', cf_select_data_cb)
cf_assay_type.on_change('value', cf_assay_type_cb)
vd_new_search.on_click(vd_new_search_cb)
vd_refine_search.on_click(refine_select_menu)
vd_delete_data.on_click(vd_delete_data_cb)
vd_author.on_change('value', vd_author_callback)
vd_date.on_change('value', vd_date_callback)
vd_name.on_change('value',vd_name_callback)
vd_flag.on_change('value',vd_flag_callback)
vd_tag.on_change('value', vd_tag_cb)
vd_note.on_change('value', vd_note_cb)
vd_assay_type.on_change('value', vd_assay_type_cb)
vd_save_info.on_click(vd_save_info_callback)
cf_restore.on_click(cf_restore_callback)
cf_fit_method.on_change('value', cf_fit_method_callback)
cf_fit_plot_data.on_click(cf_fit_plot_callback)
sd_type_check.on_click(sd_type_check_cb)
sd_save_data.on_click(sd_save_data_cb)
# login_btn.on_click(login_btn_callback)
# login_pwd.on_change('value',login_pwd_cb)
login_user.on_change('value',login_user_cb)
plot_dropdown.on_change('value',plot_dropdown_cb)
upload_file_source.on_change('data',upload_file_source_cb)
project_list.on_change('value',project_list_cb)
project_dropdown.on_change('value',project_dropdown_cb)
edit_dropdown.on_change('value',edit_dropdown_cb)



# layouts
save_layout = layout([button_mode, info_box,edit_dropdown,plot_dropdown, button_load, button_save], [sd_row_1], [
                     sd_data, column(project_name, project_dropdown,project_list)], [sd_data_table, column(sd_type_check, sd_upload_opt, sd_save_data)], )  # [ams_logo,botton_spacer]

read_layout = layout([button_mode, info_box,edit_dropdown,plot_dropdown, button_load, button_save], [read_layout_plots,column(data_outlier_tab, row(options, vd_data_info))],)

curve_fit_layout = layout([button_mode, info_box,edit_dropdown, plot_dropdown,button_load, button_save], [curve_fit_plots, column(
    data_outlier_tab, row(cf_select_data_widgets, column(cf_fit_bound)))])

display_layout = layout([plot_login], [login_info, column(login_text, login_user, )])  # login_pwd,login_btn

# run
# curdoc().add_periodic_callback(refresh_time_cb, 1000)
curdoc().add_root(display_layout)
