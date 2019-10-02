from flask import Blueprint

bp = Blueprint('apps', __name__,)  # template_folder='templates'

from app.APPS import routes



#NOTE
# to use session id secret
# run bokeh sercret to get a key.
# then before run bokeh server,
#
#export BOKEH_SECRET_KEY=jpwLZikCcKlokJtvjMjmSwhe06po51SGpeCcbNbbKEJj
#export BOKEH_SIGN_SESSIONS=1
#bokeh serve  --session-ids external-signed simuojo plojo ... 
#also set flask environment variable with the same 
#BOKEH_SECRET_KEY=jpwLZikCcKlokJtvjMjmSwhe06po51SGpeCcbNbbKEJj
#BOKEH_SIGN_SESSIONS=1
