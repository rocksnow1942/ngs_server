from bokeh.plotting import figure, ColumnDataSource
from bokeh.io import curdoc
from bokeh.models import HoverTool, Plot,CustomJS,LinearAxis, Range1d,LabelSet,Arrow,VeeHead,BoxSelectTool,Rect
from bokeh.models.glyphs import Text
from bokeh.models.widgets import Panel, Tabs, Button, TextInput, Select, MultiSelect, RadioButtonGroup, PreText, TextAreaInput,Dropdown,Div,Toggle
from bokeh.layouts import widgetbox, row, column, layout
from bokeh.palettes import Category10
from bokeh.events import Tap
import os,glob,base64,copy,datetime
from io import BytesIO
import pandas as pd
import numpy as np
from utils import upload_data_folder
from dotenv import load_dotenv
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

load_dotenv(os.path.join(basedir, '.env'))

from plojo_nior_sql_mapping import Data

# declare globals
global info_change_keep,data_index,info_deque_holder,current_time,temp_data_to_save,raw_data,axis_label_dict,user_pwd,copyed_runs,analysis_temp_keep
box_select_source = ColumnDataSource(data=dict(x=[], y=[], width=[], height=[]))
info_change_keep = dict.fromkeys(['exp_name','run_extcoef','exp_tag','run_name','run_speed','run_date','run_note'],False)
analysis_temp_keep = {}
user_pwd = {'hui':['h']}
axis_label_dict = {'A': 'DAD signal / mA.U.', 'B':'Solvent B Gradient %' ,'P': 'Pressure / bar', 'default': 'Arbitrary Unit' }
current_time = datetime.datetime.now()
info_deque_holder = ['Welcome!']*3
upload_file_source = ColumnDataSource({'file_contents':[],'file_name':[]})
curve_type_options = ['A','B','P','A1','A2','A3']
copyed_runs = []
raw_data = Data()

_updatenote="""
Updates 20190602:
    1. Added box selection tool.
    2. Align curves by box select or manual align.
    3. Select Integrate coordinates by box select tool.
""".split('\n')
view_data_plot = figure(plot_width=1200,plot_height=450)
view_data_plot.annulus(x=[1, 2, 3,4,5], y=[1, 2, 3,4,5], color="hotpink",inner_radius=0.2, outer_radius=0.5)
updatenote = ColumnDataSource(dict(x=[1]*len(_updatenote),y=[4.7-i*0.35 for i in range(len(_updatenote))],text=_updatenote))
update_ = Text(x='x', y='y', text='text',text_font_size='12pt',text_font='helvetica')
view_data_plot.add_glyph(updatenote,update_)
_updatenote


# define functions

def info_deque(text):
    global info_deque_holder
    j = len(info_deque_holder)
    info_deque_holder.append(str(j)+'>>'+text)
    result = '\n'.join(info_deque_holder[-3:])
    return result

def generate_cds(run_index,**kwargs):
    secondary_axis=kwargs.get('secondary_axis','B')
    primary_axis = kwargs.get('primary_axis','A')
    align_mode = kwargs.get('align_mode',False)
    offset_curve,offset = kwargs.get('offset',('A',0))
    index = run_index.split('-')[0]
    run_speed = raw_data.experiment[index].get(run_index,{}).get('speed',0)
    run = raw_data.experiment[index].get(run_index,{})
    run_raw = raw_data.experiment_raw[index].get(run_index,{})
    if not run_raw:
        info_box.text = info_deque('{} broken, delete and reupload.'.format(run_index))
    curve_type_options=[primary_axis,secondary_axis]
    run_dict = dict.fromkeys(curve_type_options)
    integration_dict = dict.fromkeys(curve_type_options)
    annotate = dict.fromkeys(curve_type_options)
    for curve in curve_type_options:
        curve_dict = run.get(curve,{})
        extinction_coeff = curve_dict.get('extcoef',0)
        curve_dict_raw = run_raw.get(curve,{})


        time_space = curve_dict_raw.get('time',None) or curve_dict_raw.get('volume',None)
        x_unit = 'time' if 'time' in curve_dict_raw.keys() else 'volume'
        if time_space:
            time_space=np.linspace(*time_space)
        else:
            time_space = np.linspace(0,0,1)
        curve_time = time_space +offset*int(curve==offset_curve)
        curve_signal =  curve_dict_raw.get('signal',[0])
        curve_integrate = curve_dict.get('integrate',{})
        integrate_gap_x=curve_integrate.get('integrate_gap_x',[])
        integrate_gap_y=curve_integrate.get('integrate_gap_y',[])
        label_cordinate_x = curve_integrate.get('label_cordinate_x',[])
        label_cordinate_y = curve_integrate.get('label_cordinate_y',[])
        label_ = curve_integrate.get('area',[])
        label = curve_integrate.get('label',[])
        label_area = ['{:.1f}'.format(i) for i in label_]
        integrate_percent = ['{:.1f}%'.format(i*100/(sum(label_))) for i in label_]
        if x_unit == 'time':
            label_mass = ['{:.1f}ug'.format(i*extinction_coeff*run_speed/1000) for i in label_]
        else:
            label_mass = ['{:.1f}ug'.format(i*extinction_coeff/1000) for i in label_]
        temp_cds = ColumnDataSource( {'time':curve_time,'signal':curve_signal})
        integration_cds = ColumnDataSource({'integrate_percent':integrate_percent,'integrate_gap_x':integrate_gap_x,'integrate_gap_y':integrate_gap_y,'label_cordinate_x':label_cordinate_x,'label_cordinate_y':label_cordinate_y,'label_area':label_area,'label_mass':label_mass,'label':label})

        # generate annotate
        annotate_dict = curve_dict.get('annotate',{})
        anno_height,anno_x,anno_y,anno_label = [annotate_dict.get(i,[]) for i in ['height','x','y','label']]
        label_data_source = ColumnDataSource({'label_x':anno_x,'label_y':[i+j for i,j in zip(anno_y,anno_height)],'label':anno_label})
        arrow_position = [i for i in zip(anno_x,anno_y,anno_height) ]

        if (curve == primary_axis) and align_mode:
            x_offset,y_offset,scale = curve_dict.get('align_offset',(0,0,1))
            temp_cds.data['time']=temp_cds.data['time']+x_offset
            temp_cds.data['signal']=(np.array(temp_cds.data['signal'])+y_offset)*scale
            # for i in ['integrate_gap_x','integrate_gap_y','label_cordinate_x','label_cordinate_y']:
            integration_cds.data['integrate_gap_x']=list(np.array(integration_cds.data['integrate_gap_x'])+x_offset)
            integration_cds.data['integrate_gap_y']=list((np.array(integration_cds.data['integrate_gap_y'])+y_offset)*scale)
            integration_cds.data['label_cordinate_x']=np.array(integration_cds.data['label_cordinate_x'])+x_offset
            integration_cds.data['label_cordinate_y']=(np.array(integration_cds.data['label_cordinate_y'])+y_offset)*scale
            label_data_source.data['label_x']=np.array(label_data_source.data['label_x'])+x_offset
            label_data_source.data['label_y']=(np.array(label_data_source.data['label_y'])+y_offset)*scale
            arrow_position=[(i[0]+x_offset,(i[1]+y_offset)*scale,i[2]*scale) for i in arrow_position]

        run_dict.update({curve:temp_cds})
        integration_dict.update({curve:integration_cds})
        annotate.update({curve:{'label':label_data_source,'arrow':arrow_position}})

    return {'run':run_dict,'integrate':integration_dict,'annotate':annotate}

def plot_generator(plot_list=[],**kwargs):
    # box_select_source.data=dict(x=[], y=[], width=[], height=[]) # empty the data.

    plot_backend = kwargs.get('plot_backend','canvas')
    primary_axis = kwargs.get('primary_axis','A')
    secondary_axis=kwargs.get('secondary_axis','B')
    secondary_axis_range = kwargs.get('secondary_axis_range',(0,100))
    color_={'A':'magenta','B':'green','P':'royalblue','A1':'teal','A2':'deepskyblue','A3':'red','none':'red'}
    tools_list = "pan,ywheel_zoom,xwheel_zoom,box_zoom,save,crosshair,reset"
    primary_axis_labelset = set()
    secondary_axis_labelset =set()
    if len(plot_list) > 1:
        alpha = 0.75
        use_colorp = True
        for run_index in plot_list:
            primary_axis_labelset.update(raw_data.experiment[run_index.split('-')[0]][run_index].get(primary_axis,{}).get('y_label','AU'))
            secondary_axis_labelset.update(raw_data.experiment[run_index.split('-')[0]][run_index].get(secondary_axis,{}).get('y_label','AU'))
        if len(primary_axis_labelset)==1:
            primary_yaxis_label = list(primary_axis_labelset)[0]
        else:
            primary_yaxis_label = axis_label_dict.get(primary_axis[0],'AU')
        if len(secondary_axis_labelset)==1:
            secondary_yaxis_label = list(secondary_axis_labelset)[0]
        else:
            secondary_yaxis_label =  axis_label_dict.get(secondary_axis[0],'AU')
    else:
        use_colorp = False
        alpha = 0.9
        run_index=plot_list[0]
        primary_yaxis_label = raw_data.experiment[run_index.split('-')[0]][run_index].get(primary_axis,{}).get('y_label','AU')
        secondary_yaxis_label = raw_data.experiment[run_index.split('-')[0]][run_index].get(secondary_axis,{}).get('y_label','AU')
    p=figure(plot_width=1200,plot_height=450,tools=tools_list,toolbar_location='above')

    p.toolbar.active_inspect = None
    p.output_backend=plot_backend

    p.yaxis.axis_label = primary_yaxis_label
    p.extra_y_ranges = {'secondary':Range1d(*secondary_axis_range)}
    p.add_layout(LinearAxis(y_range_name='secondary',axis_label=secondary_yaxis_label),'right')
    analysis = kwargs.get('analysis',[])
    analysis_s = kwargs.get('analysis_s',[])
    analysis = set([ k for j in [i.split('-') for i in analysis] for k in j])
    analysis_s = set([ k for j in [i.split('-') for i in analysis_s] for k in j])
    angle = 0.6
    x_offset = -10
    integrate_offset_s = 15
    integrate_offset_p = 15

    x_axis_label = set()
    for i,run_index in enumerate(plot_list):

        cds_dict = generate_cds(run_index,**kwargs)

        tag = raw_data.experiment[run_index.split('-')[0]][run_index].get('note','')

        if 'time' in raw_data.experiment_raw[run_index.split('-')[0]][run_index].get(primary_axis,{}).keys():
            x_axis_label.update(['time'])
        else:
            x_axis_label.update(['volume'])

        if use_colorp:
            p_color_touse = Category10[10][i % 10]
            s_color_touse = Category10[10][(i+3) % 10]
            labelset_color_s = s_color_touse
            labelset_color_p = p_color_touse
        else:
            p_color_touse = color_[primary_axis]
            s_color_touse = color_[secondary_axis]
            labelset_color_s = 'black'
            labelset_color_p = 'black'

        if secondary_axis != 'none':
            p_render_2=p.line('time','signal',source=cds_dict['run'][secondary_axis],alpha=alpha,line_width=1.5,color=s_color_touse,legend=run_index+' '+secondary_axis+' '+tag,y_range_name='secondary')
            p_data_hover_2 = HoverTool(tooltips=[('Time: ', '@time{0.000}'), ('Value: ', '@signal{0,0.00}')],renderers=[p_render_2],mode='vline')
            p.add_tools(p_data_hover_2)

        if primary_axis != 'none':
            p_render = p.line('time','signal',source=cds_dict['run'][primary_axis],alpha=alpha,color=p_color_touse,line_width=1.5,legend=run_index+' '+primary_axis+' '+tag)
            p_data_hover = HoverTool(tooltips=[('Time: ', '@time{0.000}'), ('Value: ', '@signal{0,0.00}')],renderers=[p_render],mode='vline')
            p.add_tools(p_data_hover)

        if secondary_axis != 'none':
            if 'integrate' in analysis_s:
                p.multi_line(y_range_name='secondary',xs='integrate_gap_x',ys='integrate_gap_y',source=cds_dict['integrate'][secondary_axis],line_width=1,color=labelset_color_s)
            if 'area' in analysis_s:
                int_labels = LabelSet(y_range_name='secondary',x='label_cordinate_x',y='label_cordinate_y',angle=angle, text='label_area', level='glyph',text_font_size='9pt',text_color=labelset_color_s, x_offset=x_offset, y_offset=integrate_offset_s, source=cds_dict['integrate'][secondary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_s +=22
            if 'percent' in analysis_s:
                int_labels = LabelSet(y_range_name='secondary',x='label_cordinate_x',y='label_cordinate_y',angle=angle, text='integrate_percent', level='glyph',text_font_size='9pt',text_color=labelset_color_s, x_offset=x_offset, y_offset=integrate_offset_s, source=cds_dict['integrate'][secondary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_s +=22
            if 'mass' in analysis_s:
                int_labels = LabelSet(y_range_name='secondary',x='label_cordinate_x',y='label_cordinate_y',angle=angle, text='label_mass', level='glyph',text_font_size='9pt',text_color=labelset_color_s, x_offset=x_offset, y_offset=integrate_offset_s, source=cds_dict['integrate'][secondary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_s +=22
            if 'label' in analysis_s:
                int_labels = LabelSet(y_range_name='secondary',x='label_cordinate_x',y='label_cordinate_y', angle=angle,text='label', level='glyph',text_font_size='9pt', x_offset=x_offset, text_color=labelset_color_s,y_offset=integrate_offset_s, source=cds_dict['integrate'][secondary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_s +=22
            if 'annotate' in analysis_s:
                for j in cds_dict['annotate'][secondary_axis]['arrow']:
                    p.add_layout(Arrow(y_range_name='secondary',end=VeeHead(size=8), line_color=s_color_touse,x_start=j[0], y_start=j[1]+j[2], x_end=j[0], y_end=j[1]))
                anno_label = LabelSet(y_range_name='secondary',x='label_x',y='label_y',angle=angle, text='label', level='glyph',text_font_size='9pt', x_offset=0, y_offset=5, source=cds_dict['annotate'][secondary_axis]['label'], render_mode='canvas')
                p.add_layout(anno_label)

        if primary_axis != 'none':
            if 'integrate' in analysis:
                p.multi_line(xs='integrate_gap_x',ys='integrate_gap_y',source=cds_dict['integrate'][primary_axis],line_width=1,color=labelset_color_p)
            if 'area' in analysis:
                int_labels = LabelSet(x='label_cordinate_x',y='label_cordinate_y',angle=angle, text='label_area', text_color=labelset_color_p, level='glyph',text_font_size='9pt', x_offset=x_offset, y_offset=integrate_offset_p, source=cds_dict['integrate'][primary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_p +=22
            if 'percent' in analysis:
                int_labels = LabelSet(x='label_cordinate_x',y='label_cordinate_y', angle=angle,text='integrate_percent', text_color=labelset_color_p,level='glyph',text_font_size='9pt', x_offset=x_offset, y_offset=integrate_offset_p, source=cds_dict['integrate'][primary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_p +=22
            if 'mass' in analysis:
                int_labels = LabelSet(x='label_cordinate_x',y='label_cordinate_y',angle=angle, text='label_mass', text_color=labelset_color_p,level='glyph',text_font_size='9pt', x_offset=x_offset, y_offset=integrate_offset_p, source=cds_dict['integrate'][primary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_p +=22
            if 'label' in analysis:
                int_labels = LabelSet(x='label_cordinate_x',y='label_cordinate_y', angle=angle,text='label', text_color=labelset_color_p,level='glyph',text_font_size='9pt', x_offset=x_offset, y_offset=integrate_offset_p, source=cds_dict['integrate'][primary_axis], render_mode='canvas')
                p.add_layout(int_labels)
                integrate_offset_p +=22
            if 'annotate' in analysis:
                for j in cds_dict['annotate'][primary_axis]['arrow']:
                    p.add_layout(Arrow(end=VeeHead(size=8), line_color=p_color_touse,x_start=j[0], y_start=j[1]+j[2], x_end=j[0], y_end=j[1]))
                anno_label = LabelSet(x='label_x',y='label_y',angle=angle, text='label', level='glyph',text_font_size='9pt', x_offset=0, y_offset=5, source=cds_dict['annotate'][primary_axis]['label'], render_mode='canvas')
                p.add_layout(anno_label)
    if len(x_axis_label)==1:
        if 'time' in x_axis_label:
            p.xaxis.axis_label = 'Run Time /min'
        else:
            p.xaxis.axis_label = 'Run Volume / mL'
    else:
        p.xaxis.axis_label = 'Run Time ? Volume Mixture'

    p.legend.click_policy = 'hide'
    p.legend.border_line_alpha = 0
    p.legend.background_fill_alpha = 0.1
    box_select = BoxSelectTool(callback=box_select_callback,renderers=[p_render])
    p.add_tools(box_select)
    rect = Rect(x='x',
                y='y',
                width='width',
                height='height',
                fill_alpha=0.1,
                fill_color='green')
    p.add_glyph(box_select_source, rect, selection_glyph=rect, nonselection_glyph=rect)
    p.on_event(Tap,mouse_click_cb)
    return p

def sync_plot(plot_list,**kwargs):
    p = plot_generator(plot_list,**kwargs)
    plot_row.children = [p]

def vd_plot_options_fetcher():
    pa = vd_primary_axis_option.value
    sa = vd_secondary_axis_option.value
    annotation = vd_anotation_option.value
    annotation_s = vd_anotation_option_s.value
    plot_format = 'canvas' if vd_plot_backend.value=='PNG' else 'svg'
    align_mode = vd_align_mode.active
    try:
        a=vd_secondary_axis_range.value.split('-')
        if len(a)>2:
            a = ('-'+a[1],a[2])
        sa_range = tuple(map(float,a))
        assert len(sa_range)==2
        offset = (sa,float(vd_offset_option.value))
    except:
        info_box.text = info_deque('enter valid plot options')
        sa_range = (0,100)
        offset = ('A',0)
    return dict(align_mode=align_mode,offset=offset,plot_backend=plot_format,primary_axis=pa,secondary_axis=sa,analysis=annotation,analysis_s=annotation_s,secondary_axis_range=sa_range)

def experiment_menu_generator(items):
    menu = []
    dates = []
    for i in items:
        name = raw_data.index[i].get('name', 'No_Name')
        # name = (name[:25]+'...') if len(name)>50 else name
        menu.append(' '.join([i,raw_data.index[i].get('date', '000000')[-4:],name]))
        dates.append(int(raw_data.index[i].get('date', '00000000')))
    result = list(zip(items, menu))
    result = [i for _,i in sorted(zip(dates,result),reverse=True)]
    return result

def runs_menu_generator(items):
    menu = []
    value_list = []
    for i in items:
        for j in raw_data.experiment[i].keys():
            value_list.append(j)
            curve = list(raw_data.experiment[i][j].keys())
            curve = [i for i in curve if i in curve_type_options]
            name = raw_data.experiment[i][j].get('name','No_name')
            # name = (name[:35]+'...') if len(name)>35 else name
            menu.append(' '.join([j,raw_data.experiment[i][j].get('date','No_date')[-4:],name,str(curve)]))
    result = list(zip(value_list, menu))
    result = sorted(result, key=lambda x: (int(x[0].split('-')[0][3:]),int(x[0].split('-')[1][3:])), reverse=True)
    return result

def copy_analysis():
    """
    copy analysis will copy the selected annotation options for primary_axis:
    i.e. if both integration and annotation are selected, both will be copyed to clipboard.
    """
    if len(sd_run_list.value)!=1:
        info_box.text = info_deque('Select Only 1 run to copy analysis.')
        raise ValueError ('sele 1')
    run_index = sd_run_list.value[0]
    index= run_index.split('-')[0]
    curve = vd_primary_axis_option.value
    target = raw_data.experiment[index][run_index]
    analysis = set([i.split('-')[0] for i in vd_anotation_option.value if i!='none'])
    if len(analysis) == 0:
        info_box.text = info_deque('Select primary_axis analysis in plot options.')
        raise ValueError ('sele 1')
    info_box.text = info_deque('Copying...')
    temp={}
    for key in analysis:
        if key == 'integrate':
            inte_para = target.get(curve,{}).get(key,{}).get('inte_para',[]).copy()
            label = target.get(curve,{}).get(key,{}).get('label',[]).copy()
            temp.update({'integrate':{'inte_para':inte_para,'label':label,'integrate_gap_x':[],'integrate_gap_y':[],'label_cordinate_x':[],'label_cordinate_y':[],'area':[]}})
        elif key == 'annotate':
            height = target.get(curve,{}).get(key,{}).get('height',[]).copy()
            x = target.get(curve,{}).get(key,{}).get('x',[]).copy()
            label = target.get(curve,{}).get(key,{}).get('label',[]).copy()
            temp.update({'annotate':{'height':height,'x':x,'label':label,'y':[]}})
        info_box.text = info_deque('{} copyed.'.format(key))
        global analysis_temp_keep
        analysis_temp_keep = copy.deepcopy(temp)

def check_run_analysis(run_index):
    """
    validate integration and annotation parameter
    generate result.
    """
    index= run_index.split('-')[0]
    target = raw_data.experiment[index][run_index]
    repair=False
    for k,i in target.items():
        if k in curve_type_options:
            time_space = raw_data.experiment_raw[index][run_index][k].get('time',None) or raw_data.experiment_raw[index][run_index][k].get('volume',None)
            if time_space:
                time_max = time_space[1]
            else:
                time_max=0
            for key,item in i.items():
                if key == 'integrate':
                    to_keep= [i for i in zip(item['inte_para'],item['label']) if i[0][1]<=time_max]
                    if len(to_keep) != len(item['inte_para']):
                        repair = True
                    item['inte_para']=[i[0] for i in to_keep]
                    item['label']=[i[1] for i in to_keep]
                    item.update({'integrate_gap_x':[],'integrate_gap_y':[],'label_cordinate_x':[],'label_cordinate_y':[],'area':[]})
                    generate_integration_from_para(run_index,k)
                elif key == 'annotate':
                    to_keep= [i for i in zip(item['height'],item['x'],item['label']) if i[1]<=time_max]
                    if len(to_keep) != len(item['x']):
                        repair = True
                    item.update({'height':[i[0] for i in to_keep],'x':[i[1] for i in to_keep],'label':[i[2] for i in to_keep],'y':[]})
                    annotate_generator(run_index,k)
    return repair

def check_selected_runs():
    """
    check the analysis of selected runs. currently only repairing integration error.
    Todo: add repair for missing index data.
    """
    entry = sd_run_list.value
    if mode_selection.active != 1:
        info_box.text = info_deque('Go to View tab to Select Experiments/Runs.')
        raise ValueError('go to view tab.')
    if not entry:
        to_repair = [i[0] for i in sd_run_list.options]
        info_box.text = info_deque('No runs selected, Repair {} runs in all selected experiments...'.format(len(to_repair)))
    else:
        to_repair = entry
        info_box.text = info_deque('Start repair {} runs...'.format(len(to_repair)))
    count=0
    for i in to_repair:
        _=check_run_analysis(i)
        if _:
            count+=1
            raw_data.experiment_to_save.append((i,'sync'))
            info_box.text = info_deque('Run {} repaired.'.format(i))
    info_box.text = info_deque('Done! {} runs repaired.'.format(count))
    if count:
        info_box.text = info_deque('!!!DON\'T forget to SAVE!!!')

def paste_analysis():
    """
    paste analysis to selected runs.
    will only paste down integration within allowed run time.
    """
    global analysis_temp_keep
    run_index = sd_run_list.value
    if not run_index:
        info_box.text = info_deque('Select runs to paste to.')
        raise ValueError('select run to paste.')
    index= [i.split('-')[0] for i in run_index]
    curve = vd_primary_axis_option.value
    for i,ri in zip(index,run_index):
        target = raw_data.experiment[i][ri]
        if target.get(curve,'none') == 'none':
            info_box.text = info_deque('{} doesn\'t have curve {}'.format(ri,curve))
        else:
            target[curve].update(copy.deepcopy(analysis_temp_keep))
            _=check_run_analysis(ri)
        raw_data.experiment_to_save.append((ri, 'sync'))
        info_box.text = info_deque('Pasted to {}.'.format(ri))
    sync_plot(run_index,**vd_plot_options_fetcher())

def copy_selected_run():
    global copyed_runs
    entry = sd_run_list.value
    if mode_selection.active != 1:
        info_box.text = info_deque('Go to View tab to cut.')
        raise ValueError('go to view tab to cut.')
    copyed_runs = entry.copy()
    if not entry:
        info_box.text = info_deque('No runs selected, clipboard cleared.')
    else:
        info_box.text = info_deque('{} runs in clipboard.'.format(len(copyed_runs)))

def paste_selected_run():
    global copyed_runs
    if mode_selection.active != 1:
        info_box.text = info_deque('Go to View tab to Paste.')
        raise ValueError('go to view tab to Paste.')
    target = sd_experiment_list.value
    if len(target) != 1:
        info_box.text = info_deque('Selecte only 1 Experiment to Paste to.')
        raise ValueError('SELECT 1 exp to paste.')
    if len(copyed_runs)==0:
        info_box.text = info_deque('Clipboard is empty, Cut runs first.')
        raise ValueError('SELECT before paste.')
    target = target[0]
    new_run = raw_data.next_run(target,len(copyed_runs))
    try:
        for i,j in zip(copyed_runs,new_run):
            exp = i.split('-')[0]
            raw_data.experiment[target].update({j:raw_data.experiment[exp].pop(i)})
            raw_data.experiment_raw[target].update({j:raw_data.experiment_raw[exp].pop(i)})
            raw_data.experiment_to_save.append((i,j))
        sd_run_list.options = runs_menu_generator([target])
        info_box.text = info_deque('{} runs moved to {}.'.format(len(copyed_runs),target))
        copyed_runs = []
    except:
        load_button_cb()
        info_box.text = info_deque('Error occured during pasting. No changes were made.')
        copyed_runs=[]

def it_para_check(xe,run_index,curve,xs=0):
    """
    check if the x value of integration interval is within the time of current run.
    """
    index= run_index.split('-')[0]
    time_ = raw_data.experiment_raw[index][run_index][curve].get('time',None) or raw_data.experiment_raw[index][run_index][curve].get('volume',None)
    if xs>=xe or xe>time_[1]:
        info_box.text = info_deque('Time parameter error, action aborted.')
        raise ValueError('time para error.')

def generate_integration_from_para(run_index,curve):
    index= run_index.split('-')[0]
    target = raw_data.experiment[index][run_index][curve]['integrate']
    time_ = raw_data.experiment_raw[index][run_index][curve].get('time',None) or \
        raw_data.experiment_raw[index][run_index][curve].get('volume',None)

    delta_t = (time_[1]-time_[0])/(time_[2]-1)

    signal=raw_data.experiment_raw[index][run_index][curve]['signal']
    update_start = len(target['integrate_gap_x'])
    for xs,xe,ys,ye in target['inte_para'][update_start:]:
        xs_i = int(round((xs-time_[0])/delta_t))
        xe_i = int(round((xe-time_[0])/delta_t))
        ym = signal[int((xs_i+xe_i)/2)]
        area = np.sum(signal[xs_i:xe_i])*(delta_t)-(ys+ye)*(xe-xs)/2
        target['integrate_gap_x'].append([ xs,xs ,xe ,xe ])
        target['integrate_gap_y'].append([ signal[xs_i],ys ,ye ,signal[xe_i] ])
        target['label_cordinate_x'].append((xs+xe)/2)
        target['label_cordinate_y'].append(ym)
        target['area'].append(area)

def it_integration_list_menu_generator(run_index,curve):
    index= run_index.split('-')[0]
    inte_para = raw_data.experiment[index][run_index].get(curve,{}).get('integrate',{}).get('inte_para',[])
    inte_label = raw_data.experiment[index][run_index].get(curve,{}).get('integrate',{}).get('label',[])
    menu = []
    for (i,j),k in zip(enumerate(inte_para),inte_label):
        xs = str(round(j[0],3))
        xe =str(round(j[1],3))
        ys =str(round(j[2],3))
        ye =str(round(j[3],3))
        value = k + ' ('+xs+','+ys+') -> ('+xe+','+ye+')'
        menu.append((str(i),value))
    return menu

def an_list_menu_generator(run_index,curve):
    index= run_index.split('-')[0]
    x_position = raw_data.experiment[index][run_index].get(curve,{}).get('annotate',{}).get('x',[])
    height = raw_data.experiment[index][run_index].get(curve,{}).get('annotate',{}).get('height',[])
    label = raw_data.experiment[index][run_index].get(curve,{}).get('annotate',{}).get('label',[])
    menu = []
    for (i,j),k,l in zip(enumerate(x_position),height,label):

        value = l + ' -> ' + str(round(j,3)) +' - ' + str(int(k))
        menu.append((str(i),value))
    return menu

def annotate_generator(run_index,curve):
    index= run_index.split('-')[0]
    target =  raw_data.experiment[index][run_index][curve]['annotate']
    signal=raw_data.experiment_raw[index][run_index][curve]['signal']
    time_ = raw_data.experiment_raw[index][run_index][curve].get('time',None) or raw_data.experiment_raw[index][run_index][curve].get('volume',None)
    delta_t = (time_[1]-time_[0])/(time_[2]-1)
    x_position = target['x']
    update_start = len(target['y'])
    for i in x_position[update_start:]:
        y_position = signal[int(round((i-time_[0])/delta_t))]
        target['y'].append(y_position)

def sync_vd_exp_info_widgets(sele):
    global info_change_keep
    vd_exp_name.value = str([raw_data.index[i].get('name','No_Name') for i in sele]).strip('\'[]')
    vd_exp_tag.value = str([raw_data.index[i].get('tag','No_note') for i in sele]).strip('\'[]')
    info_change_keep.update(exp_name=False,exp_tag=False)

def sync_vd_run_info_widgets(sele):
    global info_change_keep
    exp = [i.split('-')[0] for i in sele]
    curve = vd_primary_axis_option.value
    vd_run_ext_coef.value = str([raw_data.experiment[i][j].get(curve,{'extcoef':'No_Curve'}).get('extcoef','No_Ext') for i,j in zip(exp,sele)]).strip('\'[]')
    vd_run_name.value = str([raw_data.experiment[i][j].get('name','No_Name') for i,j in zip(exp,sele)]).strip('\'[]')
    vd_run_speed.value = str([raw_data.experiment[i][j].get('speed','No_Speed') for i,j in zip(exp,sele)]).strip('\'[]')
    vd_run_date.value = str([raw_data.experiment[i][j].get('date','No_Date') for i,j in zip(exp,sele)]).strip('\'[]')
    vd_run_note.value = str([raw_data.experiment[i][j].get('note','No_Tag') for i,j in zip(exp,sele)]).strip('\'[]')
    info_change_keep.update(run_name=False,run_date=False,run_note=False,run_speed=False,run_extcoef=False)

def load_analysis_para(index,run_index,curve):
    it_integration_list.options = it_integration_list_menu_generator(run_index,curve)
    an_list.options = an_list_menu_generator(run_index,curve)
    it_ext_coef.value =str(raw_data.experiment[index][run_index].get(curve,{}).get('extcoef','None'))
    it_run_speed.value = str(raw_data.experiment[index][run_index].get('speed','None'))


def sd_data_generator():
    """
    parse data from upload_file_source
    """
    if upload_file_source.data['file_name'][0] == 'nofile':
        result_dict = 'none'
    else:
        try:
            raw_contents = upload_file_source.data['file_contents'][0]
            prefix, b64_contents = raw_contents.split(",", 1)
            file_contents = base64.b64decode(b64_contents)
            extension =  upload_file_source.data['file_name'][0].split('.')[1]

            if extension.lower()=='csv':
                data = file_contents.decode("utf-16")
                file_name = upload_file_source.data['file_name'][0].split('.')[0].split('_')
                data = data.strip('\n')
                data = [list(map(float,i.strip('\r').split('\t'))) for i in data.split('\n')]
                data = list(map(list, zip(*data)))
                data_range = (data[0][0],data[0][-1],len(data[0]))
                data_signal = data[1]
                data_date=file_name[0]
                data_name=file_name[1]
                data_key = file_name[2].upper()
                run_speed = float(sd_run_speed.value)
                ext_coef = float(sd_ext_coef.value)
                if data_key not in curve_type_options:
                    raise ValueError('not correct curve type')
                meta = {'speed':run_speed,'date':data_date,'name':data_name,data_key:{'y_label':axis_label_dict.get(data_key[0],'default')}}
                if data_key[0]=='A':
                    meta[data_key].update(extcoef=ext_coef)
                raw = {data_key:{'time':data_range,'signal':[round(i,6) for i in data_signal]}}
                result_dict = {'meta':meta,'raw':raw}
            elif extension.lower()=='xls':
                toread = BytesIO(file_contents)
                df = pd.read_excel(toread)
                result_dict=process_df_upload(df)
            else:
                info_box.text = info_deque('Extension {} not supported.'.format(extension))
        except Exception as e:
            raise e
            info_box.text = info_deque('Wrong uploaded.')
            result_dict = 'none'
    return result_dict

def process_df_upload(df):
    run_speed = float(sd_run_speed.value)
    ext_coef = float(sd_ext_coef.value)

    meta={}
    raw={}
    name=df.iloc[0,0].split(':')[0]
    date=name[0:8]
    if date.isnumeric():
        meta['date']=date
        meta['name']=name[8:].strip()
    else:
        meta['date']=sd_date.value
        meta['name'] = name[8:].strip()
    meta.update(speed=run_speed)
    unit=df.iloc[1,0]
    unit = 'time' if unit=='min' else 'volume'
    integrate=dict(inte_para=[],label=[])
    for _i,_d in zip(df.columns[::2],df.columns[1::2]):
        data=df[_d].dropna().tolist()
        time=df[_i].dropna().tolist()
        tag=time[0].split(':')[1].strip()
        y_label=None
        if "UV" in tag:
            if "UV1" in tag:
                curve = 'A'
            elif 'UV2' in tag:
                curve = 'A1'
            elif "UV3" in tag:
                curve = 'A2'
            y_label=tag[tag.index('UV'):] + ' / mA.U.'
        elif 'Cond' in tag and ('%' not in tag):
            curve='A3'
            y_label='Conductivity (mS/cm)'
        elif 'Conc' in tag:
            curve='B'
            y_label='Solvent B Gradient %'
        elif 'Pressure' in tag:
            curve = 'P'
            y_label = 'Pressure MPa'
        elif 'Fractions' in tag:
            puretime=time[2:]
            labels=data[1:-1]
            for i,(t,l) in enumerate(zip(puretime,labels)):
                if t>0:
                    integrate['inte_para'].append((t,puretime[i+1],0,0))
                    integrate['label'].append(l)

        if y_label:
            meta.update({curve:{'y_label':y_label,'extcoef':ext_coef}})
            _time,_data=condense_time_points(time[2:],data[1:])

            raw.update({curve:{unit: _time,'signal': _data }})

    for k in list(meta.keys()):
        newint=dict(inte_para=integrate['inte_para'],label=integrate['label'],area=[],integrate_gap_x=[],integrate_gap_y=[],label_cordinate_x=[],label_cordinate_y=[])
        if k.startswith('A'):
            meta[k].update(integrate=newint)

    return {'meta':meta,'raw':raw}

def condense_time_points(t,sig):
    gaps = (t[0],t[-1],len(t))
    if check_arithmetic(t):
        return gaps,sig
    newsig=[]
    for _t in np.linspace(*gaps):
        newsig.append(sig[np.abs(t-_t).argmin()])
    return gaps,newsig

def check_arithmetic(t):
    diff = np.diff(t)
    mi =np.min(diff)
    mx =np.max(diff)
    avg = np.mean(diff)
    return (mx-mi)/avg < 0.001

def data_dict_to_exp(data,index,run_index):

    if run_index == 'new':
        run_index = raw_data.next_run(index,1)[0]
    else:
        if raw_data.experiment[index][run_index]['name'] != data['meta']['name'] or raw_data.experiment[index][run_index]['date'] != data['meta']['date']:
            info_box.text = info_deque('Input file name didn\'t match selected run name')
            raise ValueError('name mismatch')
    curve = list(data['raw'].keys())
    if run_index not in raw_data.experiment[index].keys():
        raw_data.experiment[index].update({run_index:data['meta']})
        raw_data.experiment_raw[index].update({run_index:data['raw']})
    else:
        raw_data.experiment[index][run_index].update(data['meta'])
        raw_data.experiment_raw[index][run_index].update(data['raw'])

    for curve in raw_data.experiment[index][run_index]:
        if curve.startswith('A'):
            if raw_data.experiment[index][run_index][curve].get('integrate',None):
                generate_integration_from_para(run_index,curve)

    raw_data.experiment_to_save.append((run_index, 'upload'))
    info_box.text = info_deque('Curve {} uploaded to run {}.'.format(curve[0],run_index))
    sd_run_list.options = runs_menu_generator(sd_experiment_list.value)

def load_csv_to_experiment(run_list,index):
    temp_result_dict={}
    temp_raw_dict={}
    run_speed = float(sd_run_speed.value)
    ext_coef = float(sd_ext_coef.value)
    for i in run_list:
        file_name = os.path.basename(i)
        data_date,data_name,data_key = file_name.split('.')[0].split('_')
        with open(i,'rb') as f:
            data = pd.read_csv(BytesIO(f.read().decode('utf-16').encode('utf-8')),names=['time','signal'],sep='\t')
        data_range = (float(data.iloc[0,0]),float(data.iloc[-1,0]),len(data['time']))
        data_signal = list(data['signal'])
        temp_key = data_date+data_name
        if temp_key in temp_result_dict.keys():
            temp_result_dict[temp_key].update({data_key:{}})
            if data_key[0]=='A':
                temp_result_dict[temp_key][data_key].update(extcoef=ext_coef)
            temp_raw_dict[temp_key].update({data_key:{'time':data_range,'signal':data_signal}})
        else:
            temp_result_dict.update({temp_key:{'date':data_date,'name':data_name,'speed':run_speed,data_key:{}}})
            temp_raw_dict.update({temp_key:{data_key:{'time':data_range,'signal':data_signal}}})
    run_number = len(temp_result_dict.keys())
    run_entry = raw_data.next_run(index,run_number)
    for i,j in zip(run_entry,temp_result_dict.keys()):
        raw_data.experiment[index].update({i:temp_result_dict[j]})
        raw_data.experiment_raw[index].update({i:temp_raw_dict[j]})
        info_box.text = info_deque('Run {} uploaded to experiment {}.'.format(run_entry,index))
        raw_data.experiment_to_save.append((i, 'upload'))
    sd_run_list.options = runs_menu_generator([index])

def load_folder_to_experiment(exp_list):
    new_exp_entry = raw_data.next_index(len(exp_list))
    for i,j in zip(exp_list,new_exp_entry):
        exp_date,exp_name = os.path.basename(i).split('_')
        raw_data.index.update({j:{'date':exp_date,'name':exp_name,'author':sd_author.value}})
        raw_data.experiment.update({j:{}})
        raw_data.experiment_raw.update({j:{}})
        raw_data.index_to_save.append((j, 'sync'))
        run_list = glob.glob(os.path.join(i,'*.[cC][sS][vV]'))
        load_csv_to_experiment(run_list,j)
    sd_experiment_list.options=experiment_menu_generator(raw_data.index.keys())


# define callback functions

def edit_dropdown_cb(attr,old,new):
    try:
        if new == 'integrate':
             analyze_layout.children[2].children = [it_tool_box]
        elif new == 'annotate':
             analyze_layout.children[2].children = [annotate_tool_box]
        elif new == 'copy':
            copy_analysis()
        elif new == 'paste':
            paste_analysis()
        elif new == 'copy_run':
            copy_selected_run()
        elif new == 'paste_run':
            paste_selected_run()
        elif new == 'check':
            check_selected_runs()
        elif new == 'integrateall':
            if len(box_select_source.data['x'])!=0:
                for run_index in sd_run_list.value:
                    _it_add_button_cb(run_index)
                plot_para = vd_plot_options_fetcher()
                sync_plot(sd_run_list.value,**plot_para)
                info_box.text=info_deque('Integrated {} curves.'.format(len(sd_run_list.value)))
            else:
                info_box.text=info_deque('Make a box selection.')
        else:
            pass
    except:
        pass
    if new != 'none':
        edit_dropdown.value = 'none'

def it_add_button_cb():
    run_index = sd_run_list.value[0]
    curve = vd_primary_axis_option.value
    _it_add_button_cb(run_index)
    it_integration_list.options = it_integration_list_menu_generator(run_index,curve)
    it_integration_list.value = [it_integration_list.options[-1][0]]
    plot_para = vd_plot_options_fetcher()
    plot_para.update(analysis=['integrate-area','integrate-mass','integrate-label','integrate-percent'])
    sync_plot([run_index],**plot_para)

def _it_add_button_cb(run_index):
    """
    add integration
    """
    index= run_index.split('-')[0]
    curve = vd_primary_axis_option.value
    label = it_integration_name.value
    offset = raw_data.experiment[index][run_index][curve].get('align_offset',(0,0,1))
    try:
        # raw_data.experiment[index][run_index].update(extcoef=float(it_ext_coef.value))
        xs= float(it_start_x.value)
        xe= float(it_end_x.value)
        ys = float(it_start_y.value)
        ye = float(it_end_y.value)
        if vd_align_mode.active:
            xs-=offset[0]
            xe-=offset[0]
    except:
        info_box.text = info_deque('enter valid numbers')
        raise ValueError('wrong input')
    inte_para= (xs,xe,ys,ye)
    it_para_check(xe,run_index,curve,xs)

    target = raw_data.experiment[index][run_index][curve]
    if not target.get('integrate',{}):
        target.update(integrate={'inte_para':[inte_para],'integrate_gap_x':[],'integrate_gap_y':[],'label_cordinate_x':[],'label_cordinate_y':[],'area':[],'label':[label]})
    else:
        target['integrate']['inte_para'].append(inte_para)
        target['integrate']['label'].append(label)
    generate_integration_from_para(run_index,curve)
    raw_data.experiment_to_save.append((run_index, 'sync'))

def it_update_button_cb():
    it_delete_button_cb()
    it_add_button_cb()

def an_list_cb(attr,old,new):
    if len(new)>0:
        if len(new)>1:
            info_box.text = info_deque('Only first sele used.')
        run_index = sd_run_list.value[0]
        index= run_index.split('-')[0]
        curve = vd_primary_axis_option.value
        an_index = int(new[0])
        label = raw_data.experiment[index][run_index].get(curve,{}).get('annotate',{}).get('label',[])[an_index]
        x_position = raw_data.experiment[index][run_index].get(curve,{}).get('annotate',{}).get('x',[])[an_index]
        height = raw_data.experiment[index][run_index].get(curve,{}).get('annotate',{}).get('height',[])[an_index]
        an_label.value = str(label)
        an_x.value = str(x_position)
        an_height.value = str(height)
    else:
        pass

def an_add_button_cb():
    run_index = sd_run_list.value[0]
    index= run_index.split('-')[0]
    curve = vd_primary_axis_option.value
    label = it_integration_name.value
    try:
        x_position = float(an_x.value)
        height = float(an_height.value)
        label = an_label.value
        signal=raw_data.experiment_raw[index][run_index][curve]['signal']
        time_ = raw_data.experiment_raw[index][run_index][curve].get('volume',None)  or raw_data.experiment_raw[index][run_index][curve].get('time',None)
        delta_t = (time_[1]-time_[0])/(time_[2]-1)
        y_position = signal[int(round((x_position-time_[0])/delta_t))]
    except:
        info_box.text = info_deque('enter valid numbers')
        raise ValueError('wrong input')
    target =  raw_data.experiment[index][run_index][curve]
    it_para_check(x_position,run_index,curve)
    if not target.get('annotate',{}):
        target.update(annotate={'height':[height],'label':[label],'x':[x_position],'y':[y_position]})
    else:
        target['annotate']['height'].append(height)
        target['annotate']['label'].append(label)
        target['annotate']['x'].append(x_position)
        target['annotate']['y'].append(y_position)
    plot_para = vd_plot_options_fetcher()
    plot_para.update(analysis=['annotate'])
    sync_plot([run_index],**plot_para)
    an_list.options = an_list_menu_generator(run_index,curve)
    an_list.value = [an_list.options[-1][0]]
    raw_data.experiment_to_save.append((run_index, 'sync'))

def an_delete_button_cb():
    to_delete=an_list.value
    if len(to_delete)!=1:
        info_box.text = info_deque('select 1 to delete')
        raise ValueError('sele 1')
    run_index = sd_run_list.value[0]
    index= run_index.split('-')[0]
    to_delete = int(to_delete[0])
    curve = vd_primary_axis_option.value
    target = raw_data.experiment[index][run_index].get(curve,{}).get('annotate',{})
    for key in target.keys():
        try:
            del target[key][to_delete]
        except:
            pass
    an_list.options = an_list_menu_generator(run_index,curve)
    an_list.value = []
    raw_data.experiment_to_save.append((run_index, 'sync'))
    plot_para = vd_plot_options_fetcher()
    plot_para.update(analysis=['annotate'])
    sync_plot([run_index],**plot_para)

def an_update_button_cb():
    an_delete_button_cb()
    an_add_button_cb()

def it_integration_list_cb(attr,old,new):
    if len(new)>0:
        if len(new)>1:
            info_box.text = info_deque('Only first sele used.')
        run_index = sd_run_list.value[0]
        index= run_index.split('-')[0]
        curve = vd_primary_axis_option.value
        int_index = int(new[0])
        inte_para = raw_data.experiment[index][run_index].get(curve,{}).get('integrate',{}).get('inte_para',[])[int_index]
        inte_label = raw_data.experiment[index][run_index].get(curve,{}).get('integrate',{}).get('label',[])[int_index]
        it_start_x.value = str(inte_para[0])
        it_end_x.value = str(inte_para[1])
        it_start_y.value = str(inte_para[2])
        it_end_y.value = str(inte_para[3])
        it_integration_name.value = inte_label
    else:
        pass

def it_delete_button_cb():
    to_delete=it_integration_list.value
    if len(to_delete)!=1:
        info_box.text = info_deque('select 1 to delete')
        raise ValueError('sele 1')
    run_index = sd_run_list.value[0]
    index= run_index.split('-')[0]
    to_delete = int(to_delete[0])
    curve = vd_primary_axis_option.value
    target = raw_data.experiment[index][run_index].get(curve,{}).get('integrate',{})
    for key in target.keys():
        try:
            del target[key][to_delete]
        except:
            pass
    it_integration_list.options = it_integration_list_menu_generator(run_index,curve)
    it_integration_list.value = []
    raw_data.experiment_to_save.append((run_index, 'sync'))
    plot_para = vd_plot_options_fetcher()
    plot_para.update(analysis=['integrate-area','integrate-mass','integrate-label'])
    sync_plot([run_index],**plot_para)

def vd_save_info_button_cb():
    global info_change_keep
    selected_exp = sd_experiment_list.value
    selected_run = sd_run_list.value
    curve = vd_primary_axis_option.value
    try:
        new_input = dict(zip(['exp_name','exp_tag','run_name','run_extcoef','run_speed','run_date','run_note'],[vd_exp_name.value,vd_exp_tag.value,vd_run_name.value,vd_run_ext_coef.value,vd_run_speed.value,vd_run_date.value,vd_run_note.value]))
        for key,item in info_change_keep.items():
            if item:
                if key.split('_')[0]=='exp':
                    for i in selected_exp:
                        raw_data.index[i].update({key.split('_')[1]:new_input[key]})
                        raw_data.index_to_save.append((i, 'sync'))
                else:
                    for j in selected_run:
                        if key == 'run_speed':
                            raw_data.experiment[j.split('-')[0]][j].update({key.split('_')[1]:float(new_input[key])})
                        elif key == 'run_extcoef':
                            raw_data.experiment[j.split('-')[0]][j][curve].update({key.split('_')[1]:float(new_input[key])})
                        else:
                            raw_data.experiment[j.split('-')[0]][j].update({key.split('_')[1]:new_input[key]})
                        raw_data.experiment_to_save.append((j, 'sync'))
        sd_save_data_cb()
        info_change_keep = dict.fromkeys(info_change_keep.keys(),False)
    except:
        info_box.text = info_deque('Wrong input format.')
    sd_experiment_list.options = experiment_menu_generator(raw_data.index.keys())
    sd_run_list.options = runs_menu_generator(selected_exp)
def vd_exp_name_cb(attr,old,new):
    info_change_keep.update(exp_name=True)
def vd_exp_tag_cb(attr,old,new):
    info_change_keep.update(exp_tag=True)
def vd_run_name_cb(attr,old,new):
    info_change_keep.update(run_name=True)
def vd_run_speed_cb(attr,old,new):
    info_change_keep.update(run_speed=True)
def vd_run_date_cb(attr,old,new):
    info_change_keep.update(run_date=True)
def vd_run_note_cb(attr,old,new):
    info_change_keep.update(run_note=True)
def vd_run_ext_coef_cb(attr,old,new):
    info_change_keep.update(run_extcoef=True)

def box_select_source_cb(attr,old,new):
    if mode_selection.active != 0:
        if len(new['x'])>0:
            it_start_x.value=str(new['x'][0]-0.5*new['width'][0])
            it_end_x.value=str(new['x'][0]+0.5*new['width'][0])
            an_x.value=str(new['x'][0])

def sd_run_list_cb(attr,old,new):
    if mode_selection.active != 0 and new:
        sync_plot(new,**vd_plot_options_fetcher())
        sync_vd_run_info_widgets(new)
        vd_curve_selection.options=new
        vd_curve_selection.value = new[-1] if new else None
    else:
        pass

def vd_plot_option_cb(attr,old,new):
    selection = sd_run_list.value
    sd_run_list_cb(1,2,selection)

def vd_search_botton_cb():
    keyword = vd_search_keyword.value.split()
    keyword = keyword if keyword else [""]
    field = vd_search_field.value
    search_hit = []
    for key, item in raw_data.index.items():
        for field_ in field:
            hit_found = False
            for i in keyword:
                if i.lower() in item.get(field_.split('_')[1],'').lower():
                    search_hit.append(key)
                    hit_found = True
                    break
            if hit_found:
                break
    sd_experiment_list.options = experiment_menu_generator(search_hit)
    sd_experiment_list.value = []

def mode_selection_cb(attr,old,new):
    if new == 0:
        display_layout.children = upload_layout.children
    elif new == 1:
        display_layout.children = vd_layout.children
    elif new == 2:
        display_layout.children = analyze_layout.children
        if len(sd_run_list.value) ==0:
            info_box.text = info_deque ('Select a run to start!')
            raise ValueError('sele 1')
        else:
            info_box.text = info_deque ('Only first sele used!')
            run_index=sd_run_list.value[0]
            index= run_index.split('-')[0]
            sd_run_list.value = [run_index]
            curve = vd_primary_axis_option.value
        load_analysis_para(index,run_index,curve)
    else:
        pass

def upload_file_source_cb(attr,old,new):
    data = sd_data_generator()
    if data != 'none':
        index = sd_experiment_list.value
        if len(index)!=1:
            info_box.text = info_deque('Select 1 experiment to upload.')
            raise ValueError('sele 1')
        index = index[0]
        try:
            run_index = sd_run_list.value[0]
        except:
            run_index = 'new'
        upload_file_source.data={'file_contents':['none'],'file_name':['nofile']}
        data_dict_to_exp(data,index,run_index)



def sd_save_data_cb():
    print(raw_data.experiment_to_save)
    print(raw_data.index_to_save)
    tosave = len(raw_data.experiment_to_save)
    exptosave = len(raw_data.index_to_save)
    raw_data.save_data()
    info_box.text = info_deque('Saved {} Experiments, {} Runs.'.format(exptosave,tosave))
   

def sd_experiment_list_cb(attr,old,new):
    raw_data.load_experiment(new)
    new_option = runs_menu_generator(new)
    if mode_selection.active ==0:
        a=[('new','new')]
        a.extend(new_option)
        sd_run_list.options = a
    else:
        sd_run_list.options = new_option
    sd_run_list.value = []
    sync_vd_exp_info_widgets(new)

def sd_create_new_exp_cb():
    if sd_experiment.value == 'None':
        info_box.text = info_deque('Enter new exp name.')
        raise ValueError('enter new')
    new_exp = raw_data.next_index(1)
    index_update = {new_exp[0]:{'name':sd_experiment.value,'date':sd_date.value,'author':sd_author.value}}
    raw_data.index.update(index_update)
    raw_data.experiment.update({new_exp[0]:{}})
    raw_data.experiment_raw.update({new_exp[0]:{}})
    raw_data.index_to_save.append((new_exp[0], 'sync'))
    new_exp_opt = experiment_menu_generator(raw_data.index.keys())
    sd_experiment_list.options=new_exp_opt
    sd_experiment_list.value = [new_exp_opt[0][0]]

def sd_folder_upload_cb():
    """
    call back function for upload data from folder button
    """
    search=os.path.join(upload_data_folder,'[1-2][0][0-9]*')
    file_list = glob.glob(search)
    run_list = []
    exp_list = []
    for i in file_list:
        if os.path.isdir(i):
            exp_list.append(i)
        else:
            run_list.append(i)
    current_index = sd_experiment_list.value
    if run_list:
        if len(current_index)!=1:
            info_box.text = info_deque('Select 1 experiment to upload.')
            raise ValueError('sele 1')
        load_csv_to_experiment(run_list,current_index[0])
    else:
        info_box.text = info_deque('No CSV file found.')
    if exp_list:
        load_folder_to_experiment(exp_list)
    else:
        info_box.text = info_deque('No experiment folder found.')

def vd_delete_data_button_cb():
    if vd_selection_tab.active!=0:
        info_box.text = info_deque('Go to Experiment Tab')
        raise ValueError('sele')
    exp_to_del = sd_experiment_list.value
    run_to_del = sd_run_list.value
    if run_to_del:
        for i in run_to_del:
            exp = i.split('-')[0]
            _ = raw_data.experiment[exp].pop(i,None)
            _ = raw_data.experiment_raw[exp].pop(i,None)
            raw_data.experiment_to_save.append((i,'del'))
            sd_run_list.options = runs_menu_generator(exp_to_del)
            sd_run_list.value = []
    else:
        for i in exp_to_del:
            _= raw_data.index.pop(i,None)
            _= raw_data.experiment.pop(i,None)
            _= raw_data.experiment_raw.pop(i,None)
            raw_data.index_to_save.append((i,'del'))
            sd_experiment_list.options = experiment_menu_generator(raw_data.index.keys())
            sd_experiment_list.value = []

def load_button_cb():
    global raw_data
    raw_data = Data()
    info_box.text = info_deque('Data re-loaded.')
    sd_experiment_list.options = experiment_menu_generator(raw_data.index.keys())
    sd_experiment_list.value = []

def login_btn_callback():
    user = login_user.value
    # password = login_pwd.value
    # if password in user_pwd.get(user, ['aptitude','ams']):
    mode_selection.active = 1
    sd_author.value = user
    # else:
    #     login_text.text = 'Wrong Username/Password \n'

def login_user_cb(attr,old,new):
    login_btn_callback()


def vd_align_mode_cb(status):
    on = 'ON' if status else 'OFF'
    info_box.text=info_deque('Switch Align Mode {}.'.format(on))
    run_index = sd_run_list.value
    sync_plot(run_index,**vd_plot_options_fetcher())

def vd_curve_selection_cb(attr,old,new):
    if new:
        curve=vd_primary_axis_option.value
        index = new.split('-')[0]
        curve_dict = raw_data.experiment[index][new][curve]
        vd_curve_offset.value=','.join([str(i) for i in curve_dict.get('align_offset',(0,0,1))])

def vd_curve_offset_cb(attr,old,new):
    try:
        new = [float(i) for i in new.split(',')]
        assert len(new)==3
    except:
        info_box.text = info_deque('Wrong Offset Format. Use X_offset,Y_offset,Scale ')
        raise ValueError('wrong offset format.')
    curve=vd_primary_axis_option.value
    run_index=vd_curve_selection.value
    index = run_index.split('-')[0]
    curve_dict = raw_data.experiment[index][run_index][curve]
    old_offset = curve_dict.get('align_offset',(0,0,1))
    if new != old_offset:
        curve_dict.update(align_offset=new)
        raw_data.experiment_to_save.append((run_index,'sync'))
        sync_plot(sd_run_list.value,**vd_plot_options_fetcher())

def vd_auto_align_cb():
    """
    align to curve selected in curve to adjust.
    """
    x=box_select_source.data['x']
    w=box_select_source.data['width']
    if len(x)==0:
        info_box.text=info_deque('Box Select Region to align.')
        return None
    x1,x2=x[0]-0.5*w[0],x[0]+0.5*w[0]
    runindexlist = sd_run_list.value.copy()
    curve=vd_primary_axis_option.value
    toalign = vd_curve_selection.value
    if len(runindexlist)==1:
        info_box.text = info_deque('Select more than 1 curve to align.')
        return None
    raw_data.experiment_to_save.extend([(i,'sync') for i in runindexlist])
    toalign_run = toalign.split('-')[0]
    time=raw_data.experiment_raw[toalign_run][toalign][curve].get('time',None) or raw_data.experiment_raw[toalign_run][toalign][curve].get('volume',None)
    signal=raw_data.experiment_raw[toalign_run][toalign][curve]['signal']
    raw_data.experiment[toalign_run][toalign][curve].update(align_offset=[0,0,1])
    timesignal=sorted([i for i in zip(np.linspace(*time),signal) if x1<i[0]<x2],key=lambda x:x[1])
    _min,_max=timesignal[0][1],timesignal[-1][1]
    maxtime=np.mean([i[0] for i in timesignal if i[1]>0.999*_max])
    maxsignal=timesignal[-1][1]
    minsignal=np.median([i[1] for i in timesignal if i[1]<(_min+0.01*(_max-_min))])
    runindexlist.remove(toalign)
    indexlist = [i.split('-')[0] for i in runindexlist]
    for index,runindex in zip(indexlist,runindexlist):
        current_xoffset=raw_data.experiment[index][runindex][curve].get('align_offset',(0,0,1))[0] if vd_align_mode.active else 0
        time=raw_data.experiment_raw[index][runindex][curve].get('time',None) or raw_data.experiment_raw[index][runindex][curve].get('volume',None)
        signal=raw_data.experiment_raw[index][runindex][curve]['signal']
        timesignal= sorted([i for i in zip(np.linspace(*time),signal) if (x1-current_xoffset)<i[0]<(x2-current_xoffset)],key=lambda x:x[1])
        _min,_max=timesignal[0][1],timesignal[-1][1]
        tempmaxtime=np.mean([i[0] for i in timesignal if i[1]>0.999*_max])
        tempmaxsignal=timesignal[-1][1]
        tempminsignal=np.median([i[1] for i in timesignal if i[1]<(_min+0.01*(_max-_min))])
        x_offset = maxtime-tempmaxtime
        scale=(maxsignal-minsignal)/(tempmaxsignal-tempminsignal)
        y_offset=minsignal/scale-tempminsignal
        raw_data.experiment[index][runindex][curve].update(align_offset=[x_offset,y_offset,scale])
    sync_plot(sd_run_list.value,**vd_plot_options_fetcher())
    vd_curve_offset.value=','.join([str(i) for i in raw_data.experiment[toalign_run][toalign][curve].get('align_offset',(0,0,1))])
    info_box.text = info_deque('Align done.')

def mouse_click_cb(event):
    box_select_source.data=dict(x=[], y=[], width=[], height=[])


# CustomJS callbacks

box_select_callback = CustomJS(args=dict(source=box_select_source), code="""
        // get data source from Callback args


        /// get BoxSelectTool dimensions from cb_data parameter of Callback
        var geometry = cb_data['geometry'];

        /// calculate Rect attributes
        var width = geometry['x1'] - geometry['x0'];
        var height = geometry['y1'] - geometry['y0'];
        var x = geometry['x0'] + width/2;
        var y = geometry['y0'] + height/2;

        /// update data source with new Rect attributes
        source.data={'x':[x],'y':[y],'width':[width],'height':[height]};
        // emit update of data source
        source.change.emit();

    """)
sd_file_upload_callback=CustomJS(args=dict(file_source=upload_file_source), code = """
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


# plojo layout elements and widgets
tools_menu = [('Copy Analysis','copy'),('Paste Analysis','paste'),None,('Integrate','integrate'),('Annotate','annotate'),None,('Integrate All Curves','integrateall'),None,('Cut Runs','copy_run'),('Paste Runs','paste_run'),('Repair Broken Data','check')]
mode_selection = RadioButtonGroup(labels=['Upload', 'View', 'Analyze'], button_type='success', width=250)
edit_dropdown = Dropdown(label='Tool Kit', button_type='success',value='integrate',menu = tools_menu,width=150)
info_box = PreText(text='Welcome!',width=400)
load_button = Button (label = 'Load Data',button_type='success',width = 150)
save_button = Button(label = 'Save Data',button_type='danger',width = 150)
top_row_= row(mode_selection,edit_dropdown,info_box,load_button,save_button)
# upload widgets
sd_file_upload = Button(label='Upload Data from File', button_type='success')
sd_folder_upload = Button(label='Upload Data from folder', button_type='success')
sd_experiment = TextInput(title='New Experiment Name:',value='None')
sd_author = TextInput(title='Author', value='none')
sd_date = TextInput(title='Experiment Date',
                    value=current_time.strftime('%Y%m%d'))
sd_run_speed = TextInput(title='Run Speed ml/min',value='0.5')
sd_ext_coef = TextInput(title='Extinction Coefficient ug/ml/OD',value='33')
sd_create_new_exp = Button(label='Create New Experiment', button_type='success')
sd_experiment_list = MultiSelect(title='List of Experiments',options=experiment_menu_generator(raw_data.index.keys()),size=25,width=300)
sd_run_list = MultiSelect(title='List of runs',options=runs_menu_generator([]),size=25,width=490,)
sd_save_data = Button(label='Save Input Data', button_type='danger')
sd_row_1 = row(column(sd_author,sd_run_speed),column(sd_date,sd_ext_coef),column(sd_experiment,sd_create_new_exp))
sd_bottom_row = row(sd_file_upload,sd_folder_upload,sd_save_data)

# view data widgets

vd_axis_option_menu = curve_type_options.copy()
vd_axis_option_menu.append('none')
vd_primary_axis_option = Select(title='Primary Axis',value='A',options=vd_axis_option_menu,width=170)
vd_secondary_axis_option = Select(title='Secondary Axis',value='B',options=vd_axis_option_menu,width=170)
vd_anotation_option = MultiSelect(title='Primary',value=['integrate-mass','integrate-label'],options=[('none','None'),('integrate-line','Integrate Line'),('integrate-area','Integrate Area'),('integrate-percent','Integrate Percent'),('integrate-mass','Integrate Mass'),('integrate-label','Integrate Label'),('annotate','Annotation')],size=7,width=150)
vd_anotation_option_s = MultiSelect(title='Secondary',value=['none'],options=[('none','None'),('integrate-line','Integrate Line'),('integrate-area','Integrate Area'),('integrate-percent','Integrate Percent'),('integrate-mass','Integrate Mass'),('integrate-label','Integrate Label'),('annotate','Annotation')],size=7,width=150)
vd_secondary_axis_range = TextInput(title = 'Secondary Axis Range',value='0-100',width=150)
# vd_div_0 = Div(text='',width=50)
vd_plot_backend = Select(title='Plot Format', value='PNG',options = ['PNG','SVG'],width = 170)
vd_offset_option = TextInput(title = 'Secondary Axis Offset',value='0',width=150)
vd_curve_selection = Select(title='Curve to adjust',value=None,options=[],width=200)
vd_curve_offset = TextInput(title='X_Offset, Y_offset, Scale:',value='0',width=200)
vd_auto_align = Button(label = 'Auto Align',button_type='success',width=200)
vd_align_mode = Toggle(label="Align Mode", button_type="success",width=200)
vd_align_widgets = widgetbox(vd_align_mode,vd_curve_selection,vd_curve_offset,vd_auto_align)
vd_plot_options = row(widgetbox(vd_primary_axis_option,vd_secondary_axis_option,vd_secondary_axis_range,vd_offset_option,width=200),column(row(vd_anotation_option,vd_anotation_option_s),vd_plot_backend),column(vd_align_widgets))
vd_selection_tab = Tabs(active=0, width=800, height=470, tabs=[Panel(child=row(sd_experiment_list,sd_run_list), title="Experiment"),Panel(child=vd_plot_options,title='Plot Options')])
vd_div_1 = Div(text='',width=50)
vd_exp_name = TextInput(title='Experiment Name : ')
vd_exp_tag = TextAreaInput(title='Experiment Note :', rows=5, cols=35, max_length=50000)
vd_run_name = TextInput(title='Run name :')
vd_run_ext_coef = TextInput(title='Primary Extinction Coefficient ug/ml/OD : ')
vd_run_speed = TextInput(title='Run Speed (ml/min):')
vd_run_date = TextInput(title='Run Date :')
vd_run_note = TextInput(title='Run Tag :')
vd_info_widgets = widgetbox(vd_exp_name,vd_exp_tag,vd_run_name,vd_run_note,vd_run_ext_coef,vd_run_speed,vd_run_date)
search_field_options = [('exp_name','Experiment Name'),('exp_tag','Experiment Note'),('exp_date','Experiment Date')]
vd_search_field = MultiSelect(title='Search field:', value=['exp_name','exp_tag'], options=search_field_options, size=3,width = 300)
vd_save_info_button = Button(label='Save Info Changes', button_type='danger',width=300)
vd_delete_data_button = Button(label='Delete Selected Data', button_type='success',width=300)
vd_search_keyword = TextInput(title='Keyword filter',width=300)
vd_search_botton = Button(label = 'Search Experiment',button_type='success',width=300)
vd_div_2 = Div(text='',width=105)
vd_div_5 = Div(text='Search HPLC Data',width=150,)
vd_button_widgets = widgetbox(vd_search_botton,vd_save_info_button,vd_delete_data_button)
vd_search_box = row(column(vd_search_keyword,vd_search_field),column(vd_div_2,vd_button_widgets))
#analyze layout widgets
# integrate tools
it_start_x = TextInput(title='Integration Start X',width=190,value='none')
it_start_y = TextInput(title='Integration Start Y',width=190,value='0')
it_end_x = TextInput(title='Integration End X',width=190,value='none')
it_end_y = TextInput(title='Integration End Y',width=190,value='0')
it_integration_list = MultiSelect(title='Integration List',value=[],options=[],size=15,width=350)
it_add_button = Button(label='New Integration', button_type='success',width=190)
it_delete_button = Button(label='Delete Integration', button_type='success',width=190)
it_update_button = Button(label='Update Integration', button_type='success',width=190)
it_integration_name = TextInput(title='Integration Name',width=190,value='none')
it_ext_coef= TextInput(title='Extinction Coef. (DO)',width=190,value='none',disabled=True)
it_run_speed = TextInput(title='Run Speed ml/min (DO)',width=190,value='none',disabled=True)

it_tool_box = row(it_integration_list,column(row(it_start_x,it_end_x),row(it_start_y,it_end_y),row(it_add_button,it_update_button),it_delete_button),column(it_integration_name,it_ext_coef,it_run_speed))
# annotate tools
an_label = TextInput(title='New Annotation Label',value='none')
an_x = TextInput(title='Annotation Position',value='none')
an_height = TextInput(title='Annotation Height',value='none')
an_list = MultiSelect(title='Annotation List',value=[],options=[],size=15,width=350)
an_div_4 = Div(text='',width=20)
an_div_1 = Div(text='',width=20)
an_div_0 = Div(text='',width=20)
an_add_button = Button(label='New Annotation', button_type='success')
an_delete_button = Button(label='Delete Annotation', button_type='success')
an_update_button = Button(label='Update Annotation', button_type='success')
annotate_tool_box = row(an_list,an_div_4,column(an_label,an_x,an_height),an_div_1,column(an_div_0,an_add_button,an_update_button,an_delete_button))

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
glyph_2_ = ColumnDataSource(dict(x=[0.84,2.245,3], y=[0,0.99,0.99], text=['PL@j@-nior','~','~']))
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
# botton_spacer = PreText(text=('ho'), width=1200, height=100)



# add callbacks
edit_dropdown.on_change('value',edit_dropdown_cb)
it_add_button.on_click(it_add_button_cb)
it_update_button.on_click(it_update_button_cb)
an_list.on_change('value',an_list_cb)
an_add_button.on_click(an_add_button_cb)
an_delete_button.on_click(an_delete_button_cb)
an_update_button.on_click(an_update_button_cb)
mode_selection.on_change('active',mode_selection_cb)
upload_file_source.on_change('data',upload_file_source_cb)
sd_experiment_list.on_change('value',sd_experiment_list_cb)
sd_create_new_exp.on_click(sd_create_new_exp_cb)
sd_save_data.on_click(sd_save_data_cb)
sd_folder_upload.on_click(sd_folder_upload_cb)
vd_delete_data_button.on_click(vd_delete_data_button_cb)
load_button.on_click(load_button_cb)
save_button.on_click(sd_save_data_cb)
sd_run_list.on_change('value',sd_run_list_cb)
vd_search_botton.on_click(vd_search_botton_cb)
vd_anotation_option.on_change('value',vd_plot_option_cb)
vd_anotation_option_s.on_change('value',vd_plot_option_cb)
vd_plot_backend.on_change('value',vd_plot_option_cb)
vd_offset_option.on_change('value',vd_plot_option_cb)
vd_primary_axis_option.on_change('value',vd_plot_option_cb)
vd_secondary_axis_option.on_change('value',vd_plot_option_cb)
vd_secondary_axis_range.on_change('value',vd_plot_option_cb)
vd_auto_align.on_click(vd_auto_align_cb)
vd_align_mode.on_click(vd_align_mode_cb)
vd_curve_selection.on_change('value',vd_curve_selection_cb)
vd_curve_offset.on_change('value',vd_curve_offset_cb)
vd_save_info_button.on_click(vd_save_info_button_cb)
vd_exp_name.on_change('value',vd_exp_name_cb)
vd_run_ext_coef.on_change('value',vd_run_ext_coef_cb)
vd_exp_tag.on_change('value',vd_exp_tag_cb)
vd_run_name.on_change('value',vd_run_name_cb)
vd_run_speed.on_change('value',vd_run_speed_cb)
vd_run_date.on_change('value',vd_run_date_cb)
vd_run_note.on_change('value',vd_run_note_cb)
box_select_source.on_change('data',box_select_source_cb)
it_integration_list.on_change('value',it_integration_list_cb)
it_delete_button.on_click(it_delete_button_cb)
# login_btn.on_click(login_btn_callback)
login_user.on_change('value',login_user_cb)
sd_file_upload.callback = sd_file_upload_callback

#organize layouts

plot_row = row(view_data_plot)
analyze_layout = layout([top_row_],[plot_row],[it_tool_box], )#[analysis_too_box] [botton_spacer]
vd_layout = layout([top_row_],[plot_row],[column(vd_selection_tab,vd_div_5,vd_search_box),vd_div_1,vd_info_widgets],)
upload_layout = layout([top_row_],[sd_row_1],[sd_experiment_list,sd_run_list],[sd_bottom_row])
display_layout = layout([plot_login], [login_info, column(
    login_text, login_user, )])  # login_pwd login_btn


# curdoc().add_periodic_callback(refresh_time_cb, 1000)
curdoc().add_root(display_layout)#display_layout


# mode_selection.active = 0
