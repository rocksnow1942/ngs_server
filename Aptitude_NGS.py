from app import create_app,db
from app.models import models_table_name_dictionary

app = create_app()


@app.shell_context_processor
def make_shell_context():
    models_table_name_dictionary.update({'db': db, })
    return models_table_name_dictionary


#TODO
#1. add admin background task control: to update all known sequence.
#2. add admin deletion on sequence.
#3. Edit known as for sequence.
#4. 
# add user favorites option.
# 1. add a favirites url to database and its description / name.
# add elastic search.
# add sequence length distribution to round details.
# ajax to sort order 

# port foldojo to NGS server
# download data to process.
