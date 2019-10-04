from app import create_app,db
from app.models import models_table_name_dictionary

app = create_app()


@app.shell_context_processor
def make_shell_context():
    models_table_name_dictionary.update({'db': db, })
    return models_table_name_dictionary


# to add foldojo and simuojo, bokeh serve bokeh server on localhost then allow websocket access. 

#TODO
#1. add admin background task control: to update all known sequence.
#2. add admin deletion on sequence.
#4. 
# add user favorites option.
# 1. add a favirites url to database and its description / name.
# add elastic search.

# ajax to sort order 
# monitor database size and database backup

# kudo project management system.

# URGENT
# add a folder for all setups on linux 