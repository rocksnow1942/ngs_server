"""
plot data from the pstrace monitor log file to grids.
"""
import numpy as np
import matplotlib.pyplot as plt
from myfit import myfitpeak
import json
import os


def readpss(f):
    ff = open(f, 'rt')
    data = ff.read()
    ff.close()
    data = data.strip().split('\n')
    v = [float(i.split()[0]) for i in data[1:]]
    a = [float(i.split()[1]) for i in data[1:]]
    return v, a


def myfitplotax(v, a, ax, index, color):
    fit = myfitpeak(np.array([v, a]))
    xnotjunk, ynotjunk, xforfit, gauss, baseline, peakcurrent, peakvoltage, fiterror = fit
    if isinstance(xforfit, int):
        ax.plot(v, a)
        ax.set_title("Failed To FIt", fontsize=10, color='r')
        ax.set_xticks([])
        ax.set_yticks([])
        return peakcurrent
    x1, x2 = xforfit
    y1, y2 = baseline
    k = (y2-y1)/(x2-x1)
    b = -k*x2 + y2
    baselineatpeak = k*peakvoltage + b
    ax.plot(v, a, v, ynotjunk, xforfit, baseline,
            [peakvoltage, peakvoltage], [baselineatpeak, baselineatpeak+peakcurrent])
    ax.set_title("{}-{:.2f}nA".format(index, peakcurrent),
                 fontsize=10, color=color)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('on')
    return peakcurrent


def plottogrid(files,save='ams101.png'):
    l = len(files) 
    rows = int(np.ceil(np.sqrt(l))) 
    cols = int( np.ceil( l / rows) )
    fig, axes = plt.subplots(rows,cols, figsize=( 1.5*cols, 1.5*rows ))
    axes = [i for j in axes for i in j]
    for ax in axes:
        ax.axis('off')
    for k, (file, ax) in enumerate(zip(files, axes)):
        v, a = readpss(file)
        myfitplotax(v, a, ax, k, 'b')
    plt.tight_layout()
    plt.savefig(save)
    plt.close()
    
if __name__ == "__main__":

    with open('pstracelog_DONT_TOUCH.json', 'rt') as f:
        logs = json.load(f)

    amskeys = {}
    for folder, data in logs.items():
        for file, amskey, time, timepoint in data:
            key = folder + '-' + amskey
            if key in amskeys:
                amskeys[key].append(file)
            else:
                amskeys[key] = [file]

    if not os.path.exists('curve_fit_output'):
        os.mkdir('curve_fit_output')

    for key, files in amskeys.items():
        plottogrid(files, save=os.path.join('curve_fit_output', key + '.png'))
                