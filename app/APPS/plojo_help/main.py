from bokeh.io import curdoc
from bokeh.models.widgets import Div, MultiSelect
from bokeh.layouts import layout
from help_text import text_dict

import os
from dotenv import load_dotenv
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))



header_text = Div(text="""<h1>Plojo Help Document</h1>""",width=800)

topic_list = [
chr(9608)*2+' Top Row Buttons ','+---- Upload/Browse/Fitting Button','+---- Information Box','+---- Edit Button','+---- Plot Button','+---- Load/Save Button',
chr(9608)*2+' Upload Layout ', '+---- Upload Data Options',
chr(9608)*2+' Browse Layout ','+---- Project/Experiment... Tabs','+---- plojo Keyword Search','+---- Edit/Save Experiment Information',
chr(9608)*2+' Fitting Layout ','+---- Curve Fitting with plojo',
chr(9608)*2+' Simuojo ', '+---- How to use simuojo?',
chr(9608)*2+' Fitting Methods ','+---- How does fitting work?','+---- Supported Fitting Models','+---- Confidence Intervals'
]

topic_key = ['toprow','ubfbutton','infobox','editbutton','plotbutton','loadsavebutton',
'uploadlayout','uploadoptions','browselayout','tabs','search','editinfo','fittinglayout','curvefit',
'simuojo','howtosimuojo','fitmethod','howfit','supportedfitmodel','confidence']

topic_menu = [i for i in zip(topic_key,topic_list)]

topic_select = MultiSelect(title='Topic',value=['none'],options=topic_menu,size=30)
text_show=Div(text='Select a topic to view.',width=800,height=800)

def topic_select_cb(attr,old,new):
    new=new[0]
    text_show.text = text_dict[new]

topic_select.on_change('value',topic_select_cb)
div_1 = Div(text='',width=50)
display_layout = layout([header_text],[div_1,topic_select,text_show])
curdoc().add_root(display_layout)
