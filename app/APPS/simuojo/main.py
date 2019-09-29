from simuojo_module import ic50_simu,DR_5PL,Kd_simu,ric50_simu,ri50_coop_simu
from bokeh.io import curdoc
from bokeh.layouts import row, layout
from bokeh.models.widgets import Div, Select
import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

load_dotenv(os.path.join(basedir, '.env'))





simu_sele = Select(title='Select a simulation model',value='Select a model',options=['Select a model','kd simulation','ic_50 simulation','ric_50 simulation','ric_50_coop simulation','Dose-Response 5 Para Logistic'])

model_display = Div(text="""<h1>Welcome to Simuojo!</h1>""",width=600,height=75)

def simu_sele_cb(attr,old,new):
    if new == 'kd simulation':
        kd_layout = Kd_simu().layout
        temp = layout([model_display,simu_sele],*kd_layout)
        select_layout.children = temp.children
        model_display.text = """ 
        <img src="simuojo/static/kd_formula.png" height='50' width="530" ">"""
    elif new=='ic_50 simulation':
        ic_50_layout = ic50_simu().layout
        temp = layout([model_display,simu_sele],*ic_50_layout)
        select_layout.children = temp.children
        model_display.text = """ <div style="text-align:center;">
        <img src="simuojo/static/ic_50.png" height='75' width="403" "></div>"""
    elif new == 'ric_50 simulation':
        ric_50_layout = ric50_simu().layout
        temp = layout([model_display,simu_sele],*ric_50_layout)
        select_layout.children = temp.children
        model_display.text = """ <div style="text-align:center;">
        <img src="simuojo/static/ric_50.png" height='75' width="485" "></div>"""
    elif new == 'Dose-Response 5 Para Logistic':
        dr5pl_layout = DR_5PL().layout
        temp = layout([model_display,simu_sele],*dr5pl_layout)
        select_layout.children = temp.children
        model_display.text = """ <div style="text-align:center;">
        <img src="simuojo/static/DR_5PL.png" height='60' width="503" "></div>"""
    elif new == 'ric_50_coop simulation':
        ric_50_coop_layout = ri50_coop_simu().layout
        temp = layout([model_display,simu_sele],*ric_50_coop_layout)
        select_layout.children = temp.children
        model_display.text = """<div style="text-align:center;">
        <img src="simuojo/static/ric_50_co.png" height='60' width="286" "></div>"""

simu_sele.on_change('value',simu_sele_cb)
select_layout = layout([row(model_display, simu_sele)], [Div(
    text="""
    <div class="jumbotron col-md-12">
      <h1>Select a model to start</h1>
    </div>""",width=900, height=875)])

curdoc().add_root(select_layout)
