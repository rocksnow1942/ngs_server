import numpy
from scipy import signal, optimize
from app import create_app
from app.plojo_models import Plojo_Data
from datetime import datetime
from app import db

app = create_app(keeplog=False)
app.app_context().push()

def add_echem_pstrace(amsid, data):
    """
    add a new echem scan data to Plojo_Data and Plojo_Project
    data: {md5, key, filename, date, potential, amp}
    """
    plojodata = Plojo_Data.query.get(amsid) 
    plojodata_data = plojodata.data
    md5 = data.get('md5', None)
    data_key = data.get('key', None)
    filename = data.get('filename', 'Unknown') 
    time = round(float(data.get('time', 0)),6)
    date = data.get('date', datetime.now().strftime('%Y%m%d %H:%M'))
    if not data_key: 
        plojodata_data.update(flag=md5, note='Starting file: '+filename, name=date,
                              author='Script upload', date=datetime.now().strftime('%Y%m%d'), assay_type="echem",
                              fit_method='none',)
    
    potential = data.get('potential',None)
    amp = data.get('amp',None)
    if potential and amp:
        xydataIn = numpy.array([potential, amp])
        res = fitpeak(xydataIn) 
        peakcurrent = round(float(res[5]),6)
    else:
        peakcurrent = -100 # to indicate fitting error
    for i, j in zip(['concentration', 'signal'], [time, peakcurrent]):
        plojodata_data[i] = plojodata_data.get(i,[]) 
        plojodata_data[i].append(j)
    
    plojodata.data = plojodata_data 
    db.session.commit()

def fitpeak(xydataIn, nstd=3.5, peakwidth=0.25, minpot=-1, maxpot=0.1):
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

    # Cut out the bad data
    truncx, truncy = truncEdges(x, y, minpot, maxpot)

    # Normalize the current by the average current value
    norm = numpy.mean(truncy)
    truncy = truncy/norm

    # Apply butterfilter
    voltageInterval = abs(truncx[1]-truncx[0])
    fs = 1/voltageInterval  # Sampling rate
    fc = 0.1*fs  # Cut off frequency ***We made up this scale factor based on limited emperical data***

    filt_b, filt_a = signal.butter(1, fc/(fs/2))
    truncy = signal.lfilter(filt_b, filt_a, truncy)

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
        if (truncx[centerLocs[i]] > (max(truncx)-edge)) or (truncx[centerLocs[i]] < (min(truncx)+edge)):
            centerLocs[i] = 0
    peakHeights = peakProps["peak_heights"]
    peakwidths = peakProps["widths"]
    # Need to cut out all elements peak height, width, centerlocs where we are outside of edge
    peakHeights = numpy.delete(
        peakHeights, [i for i in range(len(centerLocs)) if centerLocs[i] == 0])
    peakwidths = numpy.delete(
        peakwidths, [i for i in range(len(centerLocs)) if centerLocs[i] == 0])
    centerLocs = numpy.delete(
        centerLocs, [i for i in range(len(centerLocs)) if centerLocs[i] == 0])

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
        baseMask = []
        peakMask = []
        xbase = []
        ybase = []

        # Now we find the regions of the data for determining the baseline and the reduction peak (peak)
        for i in range(0, len(truncx)):
            # Gets the portion of the data that's (1/4 of the peakwidth) either side of the center. 1/8 samples more of the peak, 1/2.5 samples less of the peak
            baseMask.append((truncx[i] > (center + peakwidth/2.5))
                            or (truncx[i] < (center - peakwidth/2.5)))

            # Gets the portion aroud the center (1/2 peak width) that's the gaussian
            peakMask.append((truncx[i] > (center - peakwidth/1.5))
                            and (truncx[i] < (center + peakwidth/1.5)))

            # Isolates the data to consider for the baseline fit
            if baseMask[i] and peakMask[i]:
                # Finds the intersection of these to consider for the baseline fit
                xbase.append(truncx[i])
                # Corresponding y data
                ybase.append(truncy[i])

        # Get liner least squares fit for baseline data
        vp = numpy.polyfit(xbase, ybase, 1)

        # Get reasonable guesses for non-linear regression
        # give reasonable starting values for non-linear regression
        v0 = [vp[0], vp[1], numpy.log(
            peakHeight-linFit(vp, center))[0], center[0], peakwidth/6]

        # Run minimization of fitting error to get optimal values for the fitting parameters v
        v = optimize.fmin(getFillFitError, v0, (truncx, truncy), disp=False)
        fiterrornorm = getFillFitError(v, truncx, truncy)

        ip = numpy.subtract(gaussAndLinFit(v, [v[3]]), linFit(v, v[3]))
        potp = v[3]

        peakMask = []
        for i in range(0, len(truncx)):
            peakMask.append((truncx[i] > (v[3] - nstd*v[4]))
                            and (truncx[i] < (v[3] + nstd*v[4])))

        truncxMasked = x[[i for i in range(
            len(peakMask)) if peakMask[i] == True]]
        full = gaussAndLinFit(v, truncxMasked)
        base = linFit(v, truncxMasked)

        # Outputs
        xnotjunk = truncx
        ynotjunk = numpy.dot(truncy, norm)
        xforfit = truncxMasked
        gauss = numpy.dot(full, norm)
        baseline = numpy.dot(base, norm)
        peakcurrent = numpy.dot(ip, norm)
        peakvoltage = potp
        fiterror = fiterrornorm*norm*100
        if len(gauss) == 0:
            xnotjunk = truncx
            ynotjunk = numpy.dot(truncy, norm)
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


def truncEdges(x, y, min, max):
    '''
        Removes outlier portion of fit of known bad signal from a scan data
    '''

    # Eliminate the values that are outside of the desired range
    truncxOutTemp = numpy.zeros(len(x))  # init lists
    truncyOutTemp = numpy.zeros(len(x))

    count = -1
    for j in range(0, len(x)):
        if x[j] >= min and x[j] <= max:
            count += 1
            truncxOutTemp[count] = x[j]
            truncyOutTemp[count] = y[j]

    # Trim the padded zeros off the vectors
    truncxOut = numpy.zeros(count)
    truncyOut = numpy.zeros(count)

    for j in range(0, count):
        truncxOut[j] = truncxOutTemp[j]
        truncyOut[j] = truncyOutTemp[j]

    truncxOut = numpy.transpose(truncxOut)
    truncyOut = numpy.transpose(truncyOut)
    return truncxOut, truncyOut


def gaussAndLinFit(v, x):
    '''
        Gaussian on a lienar baseline
           This function attempts to describe current (y) as a function of voltage
           (x).  That function is a combination of gaussian on a cosh baseline.
           Fitting parameters are handed by the arrary (v),
           where v = [slope, y-intecept, Gaussian scalar, Gaussian mean, SD]    
    '''
    y = []
    for i in range(len(x)):
        y.append(v[0]*x[i] + v[1] + numpy.exp(v[2]) *
                 numpy.exp(-(((x[i]-v[3])**2)/(2*v[4]**2))))
    return y


def gaussNormFit(v, x):
    '''
    linear portion of fit 
       This function attempts to describe current (y) as a function of voltage
       (x). That function captures the gaussian portion
       Fitting parameters are handed by the arrary (v),
       where v = [y-intecept, slope, Gaussian scalar, Gaussian mean, SD]
    '''
    y = []
    for i in range(len(x)):
        if(numpy.exp(-(((x[i]-v[3])**2)/(2*v[4]**2))) != None):
            y.append(numpy.exp(-(((x[i]-v[3])**2)/(2*v[4]**2))))
    return y


def getFillFitError(v, x, y):
    '''
        This function fits the peak only within the number of standard
        deviations (nSD) of the peak in a weighted manner
    '''
    nstd = 4.5
    peakMask = []
    baseMask = []
    for i in range(0, len(x)):
            peakMask.append((x[i] > (v[3] - 2.5*v[4]))
                            and (x[i] < (v[3] + 2.5*v[4])))
            baseMask.append((x[i] > (v[3] - nstd*v[4])) and (x[i]
                                                             < (v[3] + nstd*v[4])) and (not peakMask[i]))

    xbase = x[[i for i in range(len(baseMask)) if baseMask[i] == True]]
    ybase = y[[i for i in range(len(baseMask)) if baseMask[i] == True]]
    subGaussAndLin = numpy.subtract(gaussAndLinFit(v, xbase), ybase)
    error_vector = subGaussAndLin/numpy.sqrt(sum(baseMask))

    # Peak error is weighted by exp(-distance from peak)
    xpeak = x[[i for i in range(len(peakMask)) if peakMask[i] == True]]
    ypeak = y[[i for i in range(len(peakMask)) if peakMask[i] == True]]
    subGaussAndLin = numpy.subtract(gaussAndLinFit(v, xpeak), ypeak)
    multGuassNorm = gaussNormFit(v, xpeak)
    productArray = numpy.multiply(
        subGaussAndLin/numpy.sqrt(sum(peakMask)), multGuassNorm)

    error_vector = numpy.concatenate((error_vector, productArray))

    for i in range(len(error_vector)):
        error_vector[i] = error_vector[i]**2
    sse = sum(error_vector)
    return sse
