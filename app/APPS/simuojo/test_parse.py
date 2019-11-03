from scipy.optimize import least_squares
import numpy as np



def prep_function(known_variable,unknown_variable,equation):
    kv = [i.strip() for i in known_variable.strip().split(',') if i]
    ukv = [i.strip() for i in unknown_variable.strip().split(',') if i]
    eq = [i.strip().split('=')[0] for i in equation.strip().split('\n') if i]
    assert len(eq)==len(ukv), ('{} equations but {} variables'.format(len(eq),len(ukv)))
    funcstring = "def _prepared_function(X,*args):\n\t{}=X\n\t{}=args\n\treturn {}".format(','.join(ukv),','.join(kv),','.join(eq))
    exec(funcstring)
    return locals()['_prepared_function'],kv,ukv

f,kv,ukv=prep_function("A0,B0,Kd1,","A,B,AB,,","A*B-Kd1*AB=0\nA0-A-AB=0\nB0-AB-B=0\n")
kv
ukv
_plot='AB/B0'
_against = 'A0'
_kv_arg = [1,1]
_bound = "([0,0,0],[A0,B0,min(A0,B0)])"
_against_start=1
_against_range="Kd1/100,Kd1*100"
"""
A*B-Kd1*AB=0
A0-A-AB=0
B0-AB-B=0
#
A0 : Aptamer conc. / nM
B0 :  Targent concentration /nm
Kd1 : binding Kd /nM
AB/B0 : percent binding
"""

def log_first_deri(x,y):
    if len(x)<2:
        return 1
    return (y[-1][0]-y[-2][0])/(np.log(x[-1])-np.log(x[-2]))#/np.max(y)

def log_second_deri(x,y):
    if len(x)<3:
        return 1
    y1 = log_first_deri(x,y)
    y2 = log_first_deri(x[:-1],y[:-1])
    return (y1-y2)/(np.log(x[-1])-np.log(x[-2]))

def line_solver(_kv_arg,_f,_kv,_ukv,_plot,_against,_bound=None,_against_start="1",_against_range=None):

    _tempargs = list(_kv_arg)
    _tempargs.insert(_kv.index(_against),None)
    for _n,_value in zip(_kv,_tempargs ):
        exec(f"{_n}={_value}")

    def point_solver(against_value):
        # nonlocal _bound
        args = list(_kv_arg)
        args.insert(_kv.index(_against),against_value)
        for _n,_value in zip(_kv,args):
            exec(f"{_n}={_value}")
        if _bound==None:
            _boundtouse=([0]*len(_ukv),[1e6]*len(_ukv))
            _guess = [1]*(len(_ukv))
        else:
            _boundtouse = eval(_bound)
            _guess = [ (i+j)/2 for i,j in zip(*_boundtouse)]
        print(_f,_guess,args,_boundtouse)
        _result = least_squares(_f,_guess,args=tuple(args),bounds=_boundtouse)

        for _n,_value in zip(_ukv, _result.x):
            exec(f"{_n}={_value}")
        _return_result = []
        for _p_l in _plot.split(','):
            if _p_l:
                _return_result.append(eval(_p_l))
        return _return_result


    def directional(ratio):
        _against_values = [eval(_against_start)]
        _plot_values = [point_solver(eval(_against_start))]
        _keeplooping=True
        while _keeplooping==True and len(_against_values)<100:
            _against_values.append(_against_values[-1]*ratio)
            _plot_values.append(point_solver(_against_values[-1]))
            if abs(log_first_deri(_against_values,_plot_values))/np.max(_plot_values)<0.01 \
                and abs(log_second_deri(_against_values,_plot_values))/np.max(_plot_values)<0.01:
                _keeplooping=False
        return _against_values,_plot_values
    if _against_range:
        _plot_x,_plot_y=[],[]
        for i in np.geomspace(*eval(_against_range),100):
            _plot_x.append(i)
            _plot_y.append(point_solver(i))
        return _plot_x,_plot_y
    else:
        _against_value_upper ,_plot_values_upper = directional(1.2)
        _against_value_lower,_plot_values_lower = directional(0.83333)
        return _against_value_lower[::-1]+_against_value_upper[1:],_plot_values_lower[::-1]+_plot_values_upper[1:]



x,y=line_solver([1, 1] ,f, ['A0', 'B0', 'Kd1'], ['A', 'B', 'AB'], "AB/B0", "A0", "([0,0,0], [max(A0,B0,Kd1),max(A0,B0,Kd1),max(A0,B0,Kd1)])", "1", "[Kd1/100,Kd1*100]")



len(y)
len(x)
fd=[]
sd=[]
for i in range(len(x)-1):
    fd.append(log_first_deri(x[0:i+2],y[0:i+2]))
for i in range(len(x)-2):
    sd.append(log_second_deri(x[0:i+3],y[0:i+3]))

len(x)

len(fd)
import matplotlib.pyplot as plt

fig,ax = plt.subplots()
ax.plot(x,y)
# ax.plot(x[1:],fd)
# ax.plot(x[2:],sd)
ax.set_xscale('log')




import json


[1,2,3].copy()


a,*b=[1,2,3]
b
a
