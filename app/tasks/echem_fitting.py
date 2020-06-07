import numpy as np
from scipy import signal, optimize
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
    if potential and amp:
        try:
            xydataIn = numpy.array([potential, amp])
            res = fitpeak(xydataIn)
            peakcurrent = round(float(res[5]), 6)
        except:
            peakcurrent = -100 # to indicate fitting error
    else:
        peakcurrent = -50  # to indicate missing value

    plojodata = Plojo_Data.query.get(amsid) 
    plojodata_data = plojodata.data
    # md5 = data.get('md5', None)
    # data_key = data.get('key', None)
    filename = data.get('filename', 'Unknown') 
    plojodata_data['note'] = plojodata_data.get('note','No Note').split('||')[0] + "||" + f"Ending File: {filename}"
    time = round(float(data.get('time', 0)),6)
    # date = data.get('date', datetime.now().strftime('%Y%m%d %H:%M'))
    # if data_key:
    #     note = plojodata_data.get('note', 'No note')
    # else:
    #     note = "Starting File: " + filename

    # plojodata_data.update(flag=md5, note=note, name=date, author='Script upload', 
    #     date=datetime.now().strftime('%Y%m%d'), assay_type="echem", fit_method='none',)
    for i, j in zip(['concentration', 'signal'], [time, peakcurrent]):
        plojodata_data[i] = plojodata_data.get(i,[]) 
        plojodata_data[i].append(j)
    plojodata.data = plojodata_data 
    db.session.commit()


def fitpeak(xydataIn, nstd=3.1, peakwidth=0.25, minpot=-1, maxpot=0.1):
    '''Gives me the peak current from a scan
    fits the data to a polynomial and a gaussian, then subtracts the
    xydataIn this is the current and voltage data set for one scan
    nstd = 3.5  this is normally obtained from the user - the number of standard deviations to look
    peakwidth = 0.2 %% this is the peakwidth of the gaussianpolynomial to find peak current on a scan by scan basis
    nstd = 3.1
    peakwidth = 0.25  # not used any more - taken care of automatically in fitpeak
    minpot = -1  # not necessary any more - peakfitting is robust enough to not require chopping of the edges
    maxpot = .1
    '''
    #
    # Assign voltage and current data
    x = xydataIn[0, :]  # voltage
    y = xydataIn[1, :]  # current

    # Cut out the bad data; didn't cut since the old code is not doing it.
    truncx, truncy = x, y

    # Normalize the current by the average current value
    norm = truncy.mean()
    truncy = truncy/norm

    # Apply butterfilter
    voltageInterval = abs(truncx[1]-truncx[0])
    fs = 1/voltageInterval  # Sampling rate
    fc = 0.1*fs  # Cut off frequency ***We made up this scale factor based on limited emperical data***

    sos = signal.butter(1, fc, btype='lowpass', output='sos', fs=fs)
    truncy = signal.sosfilt(sos, truncy)

    # Override values
    nstd = 4.5  # 4 is good
    peakwidthScaleFactor = 4  # 3.1 is good

    # Find the peak location and its height
    # MinPeakProminence can cause issues if peak is too small, if getting
    # "Matrix dimensions must agree error" on line 54 (baseMask 0
    # (truncx...), decrease MinPeakProminenece
    centerLocs, peakProps = signal.find_peaks(
        truncy, height=0, width=0, rel_height=0.5)

    if len(peakProps["peak_heights"]) > 2:
        prom = 0
        while len(peakProps["peak_heights"]) > 2:
            prom = prom + .01
            centerLocs, peakProps = signal.find_peaks(
                truncy, height=100*(10**(-9)), prominence=prom, width=100*(10**(-3)), rel_height=0.5)

    # Remove false peaks at extreme voltages
    edge = 0.015  # Emperically chosen cut off value in Volts

    for i in range(0, len(centerLocs)):
        if (truncx[centerLocs[i]] > ((truncx.max())-edge)) or (truncx[centerLocs[i]] < ((truncx.min())+edge)):
            centerLocs[i] = 0
    peakHeights = peakProps["peak_heights"]
    peakwidths = peakProps["widths"]
    # Need to cut out all elements peak height, width, centerlocs where we are outside of edge
    peakHeights = np.delete(
        peakHeights, [i for i in range(len(centerLocs)) if centerLocs[i] == 0])
    peakwidths = np.delete(peakwidths, [i for i in range(
        len(centerLocs)) if centerLocs[i] == 0])
    centerLocs = np.delete(centerLocs, [i for i in range(
        len(centerLocs)) if centerLocs[i] == 0])

    peakHeight = 0
    if(len(peakHeights) > 0):
        peakHeight = max(peakHeights)
    centerLoc = centerLocs[[i for i in range(
        len(peakHeights)) if peakHeights[i] == peakHeight]]
    peakwidth = peakwidths[[i for i in range(
        len(peakHeights)) if peakHeights[i] == peakHeight]]

    if len(centerLoc) > 1:
        centerLoc = min(centerLoc)
        peakwidth = sum(peakwidths[[i for i in range(
            len(peakHeights)) if peakHeights[i] == peakHeight]])
        peakHeight = truncy[centerLoc]

    center = truncx[centerLoc]
    # Convert peakwidth to voltage and scale
    # Scale value is arbitrary, was 4 previously
    peakwidth = peakwidthScaleFactor*peakwidth[0]*(voltageInterval)

    if len(centerLoc) == 0:
        xnotjunk = truncx
        ynotjunk = truncy*norm
        xforfit = 0
        gauss = 0
        baseline = 0
        peakcurrent = 0
        peakvoltage = 0
        fiterror = -0.001  # increase so that it can be seen
        return xnotjunk, ynotjunk, xforfit, gauss, baseline, peakcurrent, peakvoltage, fiterror
    else:
        # this is to get the base part of the peak, that is -PW/1.5 ~ - PW/2.5 , PW/2.5 ~ PW/1.5; this peakwidth is weirdly scaled.
        peakandbaseMask = np.logical_and(np.logical_or(truncx < (center - peakwidth/2.5), truncx > (center + peakwidth/2.5)),
                                         np.logical_and(truncx > (center - peakwidth/1.5), truncx < (center + peakwidth/1.5)))
        xbase = truncx[peakandbaseMask]
        ybase = truncy[peakandbaseMask]

        # Get liner least squares fit for baseline data
        vp = np.polyfit(xbase, ybase, 1)

        # Get reasonable guesses for non-linear regression
        # give reasonable starting values for non-linear regression
        v0 = [vp[0], vp[1], np.log(
            peakHeight-linFit(vp, center))[0], center[0], peakwidth/6]

        # Run minimization of fitting error to get optimal values for the fitting parameters v
        v = optimize.fmin(getFillFitError, v0, (truncx, truncy), disp=False)
        fiterrornorm = getFillFitError(v, truncx, truncy)

        ip = gaussAndLinFit(v, v[3]) - linFit(v, v[3])
        potp = v[3]

        # peak mask that is number of SD away.
        peakMask = np.logical_and(
            truncx > (v[3] - nstd*v[4]), truncx < (v[3] + nstd*v[4]))

        truncxMasked = x[peakMask]
        full = gaussAndLinFit(v, truncxMasked)
        base = linFit(v, truncxMasked)

        # Outputs
        xnotjunk = truncx
        ynotjunk = truncy * norm
        xforfit = truncxMasked
        gauss = full * norm
        baseline = base * norm
        peakcurrent = ip * norm
        peakvoltage = potp
        fiterror = fiterrornorm*norm*100
        if len(gauss) == 0:
            xnotjunk = truncx
            ynotjunk = truncy * norm
            xforfit = 0
            gauss = 0
            baseline = 0
            peakcurrent = 0
            peakvoltage = 0
            fiterror = -0.002  # increase so that it can be seen
        return xnotjunk, ynotjunk, xforfit, gauss, baseline, peakcurrent, peakvoltage, fiterror


def linFit(v, x):
    '''Linear portion of fit.
       This function attempts to describe current (y) as a function of voltage
       (x). That function captures the linear portion
       Fitting parameters are handed by the arrary (v),
       where v = [slope intercept]'''
    y = v[0]*x + v[1]
    return y


def gaussAndLinFit(v, x):
    '''
        Gaussian on a lienar baseline
           This function attempts to describe current (y) as a function of voltage
           (x).  That function is a combination of gaussian on a cosh baseline.
           Fitting parameters are handed by the arrary (v),
           where v = [slope, y-intecept, Gaussian scalar, Gaussian mean, SD]    
    '''
    return v[0]*x + v[1] + np.exp(v[2])*np.exp(-(((x-v[3])**2)/(2*v[4]**2)))


def gaussNormFit(v, x):
    '''
    linear portion of fit 
       This function attempts to describe current (y) as a function of voltage
       (x). That function captures the gaussian portion
       Fitting parameters are handed by the arrary (v),
       where v = [y-intecept, slope, Gaussian scalar, Gaussian mean, SD]
    '''
    return np.exp(-(((x-v[3])**2)/(2*v[4]**2)))


def getFillFitError(v, x, y):
    '''
        This function fits the peak only within the number of standard
        deviations (nSD) of the peak in a weighted manner
    '''
    nstd = 4.5

    peakMask = np.logical_and(x > (v[3] - 2.5*v[4]), x < (v[3] + 2.5*v[4]))
    baseMask = np.logical_or(np.logical_and(x > (v[3] - nstd*v[4]), x < (v[3] - 2.5*v[4])),
                             np.logical_and(x > (v[3] + 2.5*v[4]), x < (v[3] + nstd*v[4])))

    normMask = gaussNormFit(v, x) * peakMask + baseMask

    return (((gaussAndLinFit(v, x) - y) * normMask) ** 2 / (peakMask.sum() + baseMask.sum())).sum()

    # This Following code is a strict implement of the original code,
    # but I think it's more reasonable to use the number of both peak and base as error denominator.
    # xbase = x[baseMask]
    # ybase = y[baseMask]
    # subGaussAndLin = gaussAndLinFit(v, xbase) - ybase
    # error_vector = subGaussAndLin/np.sqrt(baseMask.sum())
    #
    # # Peak error is weighted by exp(-distance from peak)
    # xpeak = x[peakMask]
    # ypeak = y[peakMask]
    # subGaussAndLin = gaussAndLinFit(v, xpeak)-ypeak
    # multGuassNorm = gaussNormFit(v,xpeak)
    # productArray = subGaussAndLin/np.sqrt(peakMask.sum()) * multGuassNorm
    #
    # return (error_vector ** 2).sum() + (productArray**2).sum()
