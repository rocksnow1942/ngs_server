from foldojo_module import structure_prediction
from bokeh.io import curdoc


from dotenv import load_dotenv

load_dotenv('/home/hui/ngs_server/app/APPS/.env')





predictlayout=structure_prediction().layout

curdoc().add_root(predictlayout)
curdoc().title = chr(128540) + 'Foldojo'

# test tag
