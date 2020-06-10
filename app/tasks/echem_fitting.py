import numpy as np
from app import create_app
from app.plojo_models import Plojo_Data
from app import db
from app.tasks.myfit import myfitpeak

app = create_app(keeplog=False)
app.app_context().push()

def add_echem_pstrace(amsid, data):
    """
    add a new echem scan data to Plojo_Data and Plojo_Project
    data: {md5, key, filename, date, potential, amp}
    """
    potential = data.get('potential', None)
    amp = data.get('amp', None)
    fittingerror = ""
    if potential and amp:
        try:
            xydataIn = np.array([potential, amp])
            res = myfitpeak(xydataIn)
            peakcurrent = round(float(res[5]), 6)
        except Exception as e:
            fittingerror = str(e)
            peakcurrent = -100 # to indicate fitting error
    else:
        peakcurrent = -50  # to indicate missing value

    plojodata = Plojo_Data.query.get(amsid) 
    plojodata_data = plojodata.data
    # md5 = data.get('md5', None)
    # data_key = data.get('key', None)
    filename = data.get('filename', 'Unknown') 
    if fittingerror:
        plojodata_data['note'] = "Fitting Error "+str(fittingerror)+ ' ON ' + filename+ ":::" +plojodata_data['note']

    plojodata_data['note'] = plojodata_data.get('note','No Note').split('||')[0].strip() + " || " + f"Ending File: {filename}"
    time = round(float(data.get('time', 0)),6)
    for i, j in zip(['concentration', 'signal'], [time, peakcurrent]):
        plojodata_data[i] = plojodata_data.get(i,[]) 
        plojodata_data[i].append(j)
    
    plojodata.data = plojodata_data 
    db.session.commit()