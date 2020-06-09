import numpy as np
from scipy import signal
from app import create_app
from app.plojo_models import Plojo_Data
from app import db

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


def smooth(x, windowlenth=11, window='hanning'):
    "windowlenth need to be an odd number"
    s = np.r_[x[windowlenth-1:0:-1], x, x[-2:-windowlenth-1:-1]]
    w = getattr(np, window)(windowlenth)
    return np.convolve(w/w.sum(), s, mode='valid')[windowlenth//2:-(windowlenth//2)]


def intercept(x, x1, x2, whole=False):
    """
    determine whether the line that cross x1 and x2 and x[x1],x[x2] will intercept x.
    if whole == False, will only consider one side.
    Only consider the direction from x2 -> x1,
    that is:
    if x1 > x2; consider the right side of x2
    if x1 < x2; consider the left side of x2
    """
    # set tolerance to be 1/1e6 of the amplitude
    xtol = - (x.max() - x.min())/1e6
    y1 = x[x1]
    y2 = x[x2]
    k = (y2-y1)/(x2-x1)
    b = -k*x2 + y2
    maxlength = len(x)
    res = x - k*(np.array(range(maxlength)))-b
    if whole:

        return np.any(res[x1 - maxlength//20 - 5:x2 + maxlength//20 + 5] < xtol)
    if x1 > x2:
        return np.any(res[x2:min(maxlength, x1 + maxlength//20 + 5)] < xtol)
    else:
        # only consider extra half max width; make sure at least 5 points
        return np.any(res[max(0, x1 - maxlength//20 - 5):x2] < xtol)


def sway(x, center, step, fixpoint):
    if center == 0 or center == len(x):
        return center

    if not intercept(x, center, fixpoint):
        return center
    return sway(x, center+step, step, fixpoint)


def find_tangent(x, center):
    left = center - 1
    right = center + 1
    while intercept(x, left, right, True):
        if intercept(x, left, right):
            newleft = sway(x, left, -1, right)
        if intercept(x, right, left):
            newright = sway(x, right, 1, newleft)
        if newleft == left and newright == right:
            break
        left = newleft
        right = newright
    return left, right


def pickpeaks(peaks, props, totalpoints):
    "the way to pick a peak"
    if len(peaks) == 1:
        return peaks[0]
    # scores = np.zeros(len(peaks))
    # heights = np.sort(props['peak_heights'])
    # prominences = np.sort(props['prominences'])
    # widths = np.sort(props['widths'])
    normheights = props['peak_heights']/(props['peak_heights']).sum()
    normprominences = props['prominences']/(props['prominences']).sum()
    normwidths = props['widths']/(props['widths']).sum()
    bases = ((props['left_bases'] == props['left_bases'].min()) &
             (props['right_bases'] == props['right_bases'].max()))
    scores = normheights + normprominences + normwidths - 2*bases
    topick = scores.argmax()
    return peaks[topick]


def myfitpeak(xydataIn):
    x = xydataIn[0, :]  # voltage
    y = xydataIn[1, :]  # current

    y = smooth(y)
    # limit peak width to 1/50 of the totoal scan length to entire scan.
    # limit minimum peak height to be over 0.2 percentile of all neighbors
    heightlimit = np.quantile(np.absolute(y[0:-1] - y[1:]), 0.2)
    peaks, props = signal.find_peaks(
        y, height=heightlimit, width=len(y) / 50, rel_height=0.5)

    # return if no peaks found.
    if len(peaks) == 0:
        return x, y, 0, 0, 0, 0, 0, -1

    peak = pickpeaks(peaks, props, len(y))

    # find tagent to 3X peak width window
    x1, x2 = find_tangent(y, peak)

    y1 = y[x1]
    y2 = y[x2]
    k = (y2-y1)/(x2-x1)
    b = -k*x2 + y2

    peakcurrent = y[peak] - (k*peak + b)
    peakvoltage = x[peak]

    twopointx = np.array([x[x1], x[x2]])
    twopointy = np.array([y[x1], y[x2]])

    # for compatibility return the same length tuple.
    return x, y, twopointx, twopointy, twopointy, peakcurrent, peakvoltage, 0
