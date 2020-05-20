from scipy.optimize import curve_fit
import numpy as np
from bokeh.plotting import ColumnDataSource
from scipy.stats import t

supported_fit_method = ['kd','ic_50','ric_50','kd_with_depletion','kd_ns','kd_ns_w_depletion','DR_4PL','DR_5PL','linear','none','various']

def kd(x,kd,Fmax,Fmin,**kwargs):
    return ((Fmax-Fmin)*x/(x+10**kd))+Fmin

def kd_ns(x,kd,ns,Fmax,Fmin,**kwargs):
    return ((Fmax-Fmin)*x/(x+10**kd))+Fmin+ns*x

def ic_50(x,ic_50,Fmax,Fmin,**kwargs):
    return Fmax - (Fmax-Fmin)*x/(x+10**ic_50)

def kd_with_depletion(x,kd,a_0,Fmax,Fmin,**kwargs):
    kd = 10**kd
    a_0 = 10**a_0
    ab =a_0-((a_0-kd-x)+np.sqrt((kd+x)**2+a_0**2+2*kd*a_0-2*x*a_0))*0.5
    return (Fmax-Fmin)*ab/a_0 +Fmin

def kd_ns_w_depletion(x,kd,ns,a_0,Fmax,Fmin,**kwargs):
    kd = 10**kd
    a_0 = 10**a_0
    ab =a_0-((a_0-kd-x)+np.sqrt((kd+x)**2+a_0**2+2*kd*a_0-2*x*a_0))*0.5
    return (Fmax-Fmin)*ab/a_0 +Fmin +ns*x

def DR_4PL(x,ec_50,Fmax,Fmin,Hill,**kwargs):
    ec_50 = 10**ec_50
    return Fmax - (Fmax-Fmin)*(x**Hill)/(x**Hill+(ec_50)**Hill)

def DR_5PL(x,ec_50,Fmax,Fmin,Hill,S,**kwargs):
    """
    Five parameters logistic regression
    signal = Fmin + (Fmax-Fmin)*(X**(Hill*S))/(X**Hill + EC50**Hill*(2**(1/S)-1))**S
    """
    ec_50 = 10**ec_50
    denominator = (x**Hill+(ec_50)**Hill*(2**(1/S)-1))**S
    signal = Fmax - (Fmax-Fmin)*(x**(Hill*S))/denominator
    return signal

def linear(x,slope,b,**kwargs):
    return slope*x+b


def ric_50(a_0, r_0, v_0, kd_r, kd_a,Fmax,Fmin,**kwargs):
    kd_r = 10**kd_r
    kd_a = 10**kd_a
    r_0 = 10**r_0
    v_0 = 10**v_0
    a=kd_a-kd_r
    d=-v_0*kd_a*r_0**2
    result=np.array([])
    min_rv=min(r_0,v_0)
    for i in a_0:
        b=kd_r*r_0-2*kd_a*r_0+kd_r**2-kd_r*kd_a-kd_r*i+kd_r*v_0-kd_a*v_0
        c=r_0**2*kd_a+kd_r*kd_a*r_0-v_0*r_0*kd_r+2*v_0*r_0*kd_a+i*kd_r*r_0
        root=np.roots(np.array([a,b,c,d]))
        if root.dtype == 'complex128':
            real_root = [i.real for i in root if i.imag == 0]
            if len(real_root)==1:
                pass
            else:
                real_root=[0]
        else:
            real_root = [i for i in root if 0<i<min_rv ]
            if len(real_root)==1:
                pass
            else:
                real_root=[0]
        result=np.append(result,real_root)
    signal = result/r_0*(Fmax-Fmin) + Fmin
    return signal


def fit_method_fetcher(fit_method,**kwargs):
    m_=[1e-3,1e5]
    Fm_ = [0,2e6]
    def kwarg_get(kwargs,tag,default):
        res_ = default if kwargs.get(tag,default) == 'default' else kwargs.get(tag,default)
        if tag in ['kd','ec_50','ic_50','r_0','v_0','kd_r','kd_a','a_0']:
            res_ = [np.log10(i) if i != 0 else -3 for i in res_]
        return res_
    if fit_method == 'kd':
        func = kd
        bound_name = ['kd','Fmax','Fmin']
        bounds_= tuple(list(i) for i in zip(kwarg_get(kwargs,'kd',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_)))
    elif fit_method == 'DR_4PL':
        func = DR_4PL
        bound_name = ['ec_50','Fmax','Fmin','Hill']
        bounds_ = tuple(list(i) for i in zip(kwarg_get(kwargs,'ec_50',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_),kwarg_get(kwargs,'Hill',[0.01,2])))
    elif fit_method == 'DR_5PL':
        func = DR_5PL
        bound_name = ['ec_50','Fmax','Fmin','Hill','S']
        bounds_ = tuple(list(i) for i in zip(kwarg_get(kwargs,'ec_50',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_),kwarg_get(kwargs,'Hill',[0.01,2]),kwarg_get(kwargs,'S',[0.1,10])))
    elif fit_method == 'linear':
        func = linear
        bound_name = ['slope','b']
        bounds_ =  tuple(list(i) for i in zip(kwarg_get(kwargs,'slope',[-1e6,1e6]),kwarg_get(kwargs,'b',[-1e6,1e6])))
    elif fit_method == 'ic_50':
        func = ic_50
        bound_name = ['ic_50','Fmax','Fmin']
        bounds_ = tuple(list(i) for i in zip(kwarg_get(kwargs,'ic_50',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_)))
    elif fit_method == 'ric_50':
        func = ric_50
        bound_name = ['r_0','v_0','kd_r','kd_a','Fmax','Fmin']
        bounds_= tuple(list(i) for i in zip(kwarg_get(kwargs,'r_0',m_),kwarg_get(kwargs,'v_0',m_),kwarg_get(kwargs,'kd_r',m_),kwarg_get(kwargs,'kd_a',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_)))
    elif fit_method == 'kd_with_depletion':
        func = kd_with_depletion
        bound_name = ['kd','a_0','Fmax','Fmin']
        bounds_=tuple(list(i) for i in zip(kwarg_get(kwargs,'kd',m_),kwarg_get(kwargs,'a_0',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_)))
    elif fit_method == 'kd_ns':
        func = kd_ns
        bound_name = ['kd','ns','Fmax','Fmin']
        bounds_=tuple(list(i) for i in zip(kwarg_get(kwargs,'kd',m_),kwarg_get(kwargs,'ns',Fm_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_)))
    elif fit_method == 'kd_ns_w_depletion':
        func = kd_ns_w_depletion
        bound_name = ['kd','ns','a_0','Fmax','Fmin']
        bounds_=tuple(list(i) for i in zip(kwarg_get(kwargs,'kd',m_),kwarg_get(kwargs,'ns',Fm_),kwarg_get(kwargs,'a_0',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_)))
    else:
        fit_method=='kd'
        func = kd
        bound_name = ['kd','Fmax','Fmin']
        bounds_= tuple(list(i) for i in zip(kwarg_get(kwargs,'kd',m_),kwarg_get(kwargs,'Fmax',Fm_),kwarg_get(kwargs,'Fmin',Fm_)))
    return func, bounds_,bound_name

def convert_x_y(x,y):
    conc_set = set(x)
    if len(x)!=len(conc_set):
        new_x = list(conc_set)
        new_y = [[] for i in range(len(new_x))]
        for i,j in zip(x,y):
            new_y[new_x.index(i)].append(j)
        multi_set = True
        y_mean = [np.mean(i) for i in new_y]
        temp = [np.std(i,ddof=1) if len(i)>1 else 0 for i in new_y]
        average_temp = np.mean([i for i in temp if i!=0])
        y_stdev = [average_temp if i==0 else i for i in temp]
    else:
        new_x = x
        y_mean = y
        y_stdev = 0
        multi_set = False
    return new_x, y_mean, y_stdev, multi_set


def fitting_data(x,y,fit_method,**bounds):
    func,bounds_,bound_name = fit_method_fetcher(fit_method,**bounds)
    p_0 = [0.5*(i+j) for i,j in zip(bounds_[0],bounds_[1])]
    x,y,y_stdev,multi_set = convert_x_y(x,y)
    try:
        freedom = max(1,len(x)-len(bound_name))
        lower_CI = []
        upper_CI = []
        if multi_set:
            fit_result,corv_=curve_fit(func, x, y,p0=p_0,sigma=y_stdev,bounds = bounds_,absolute_sigma=False) #
        else:
            fit_result,corv_=curve_fit(func, x, y,p0=p_0,bounds = bounds_,absolute_sigma=False)
        sigma = np.sqrt(np.diagonal(corv_))
        for i,j in zip(sigma,fit_result):
            C_interval = t.interval(0.95,freedom,j,i)
            lower_CI.append(C_interval[0])
            upper_CI.append(C_interval[1])
    except Exception as e:
        print(e)
        fit_result = [1]*len(bound_name)
        lower_CI = fit_result
        upper_CI = fit_result
    return dict(zip(bound_name, fit_result)),dict(zip(bound_name, lower_CI)),dict(zip(bound_name, upper_CI))

def log_para_coverter(fit_para,to_log=True):
    new_para = dict.fromkeys(fit_para,0.0)
    for key,item in fit_para.items():
        if key in ['kd','ec_50','ic_50','r_0','v_0','kd_r','kd_a','a_0']:
            if to_log:
                new_para[key]=np.log10(item)
            else:
                new_para[key]=10**item
        else:
            new_para[key]=item
    return new_para

def fit_CI_value(func,x_fit,fit_method,fit_para_CI,fit_para):
    lower_para = log_para_coverter(fit_para_CI['lower_CI'])
    upper_para = log_para_coverter(fit_para_CI['upper_CI'])
    fit_result = log_para_coverter(fit_para)
    if fit_method != 'linear':
        if 'kd' in fit_method:
            temp = lower_para['kd']
            lower_para['kd'] = upper_para['kd']
            upper_para['kd'] = temp
            if 'depletion' in fit_method:
                lower_para['a_0']=upper_para['a_0']=fit_result.get('a_0',None)
        elif fit_method=='ric_50':
            lower_para=upper_para=fit_result
        elif fit_method == 'ic_50':
            pass
        elif 'DR_' in fit_method:
            if fit_result['Fmax'] < fit_result['Fmin']:
                temp = lower_para['ec_50']
                lower_para['ec_50'] = upper_para['ec_50']
                upper_para['ec_50'] = temp
            else:
                pass
            lower_para['Hill']=upper_para['Hill']=fit_result.get('Hill',None)
            if fit_method == 'DR_5PL':
                lower_para['S']=upper_para['S']=fit_result.get('S',None)
        else:
            pass
        y_fit_lower_CI = func(x_fit,**lower_para)
        y_fit_upper_CI = func(x_fit,**upper_para)
    else:
        a = func(x_fit,**lower_para)
        b = func(x_fit,**upper_para)
        y_fit = np.stack((a,b),axis=0)
        y_fit_lower_CI = y_fit.min(axis=0)
        y_fit_upper_CI = y_fit.max(axis=0)
    return y_fit_lower_CI, y_fit_upper_CI

def r_squared_calc(x_o_tofit,y_o_tofit,fit_para,fit_method):
    """
    give the fit method and normal scale fit_para dict, calculate r_squared.
    """
    func,_b,_a = fit_method_fetcher(fit_method)
    residuals = y_o_tofit-func(x_o_tofit,**fit_para)
    ss_residual = np.sum(residuals**2)
    ss_total = np.sum((y_o_tofit-np.mean(y_o_tofit))**2)
    r_squared = 1- ss_residual/ss_total
    return r_squared

def generate_cds(data,**kwargs):
    """
    data format:
    {"tag": "D20F+D20R, 1nMA121, ELISA-eylea, V1+BSA+hsDNA",
     "note": "2019 09 18 elisa ahu-r2 ric50 a121/165 1/0.1nM 1hr", 
     "name": "Lucentis 1nMA121", 
     "author": "JIM", 
     "date": "20190919", 
     "assay_type": "beads-ic_50", 
     "fit_method": "DR_4PL", 
     "concentration": [16, 0.1, 0.0], 
     "signal": [11313.0, 95420, 153102.0, 195982.0], 
     "fit_para": {
        "ec_50": 0.3443225792934813, 
        "Fmax": 194408.5101691507, 
        "Fmin": 6877.471459973062, 
        "Hill": 1.1171495830161238}, 
        "fit_para_CI": {
            "lower_CI": 
            {"ec_50": 0.1, "Fmax": 17, "Fmin": -3, "Hill": 0.}, 
            "upper_CI": 
            {"ec_50": 0., "Fmax": 2, "Fmin": 1, "Hill": 1.}}, 
        "r_squared": 0., 
        "bounds": {"ec_50": "default", "Fmax": "default", "Fmin": "default", "Hill": "default"}
        }
    kwargs have new_fit == True or False
    """


    x_o = np.array(data['concentration'])
    min_x=min(x_o[x_o!=0])/10.0
    x_o_no_zero = np.array([i if i>0 else min_x for i in x_o])
    y_o = np.array(data['signal'])

    # remove outliner from input data. 
    outlier=data.get('outlier',{'concentration':[],'signal':[]})
    if outlier['concentration']:
        x_outlier = data['outlier']['concentration']
        y_outlier = data['outlier']['signal']
        x_y_zip = [i for i in zip(x_o,y_o)]
        for i in zip(x_outlier,y_outlier):
            x_y_zip.remove(i)
        x_o_tofit=np.array([i for i,j in x_y_zip])
        y_o_tofit=np.array([j for i,j in x_y_zip])
    else:
        x_o_tofit=x_o
        y_o_tofit=y_o
    

    fit_method = data.get('fit_method','kd')

    # if the data type is not fitable return immediately.
    if fit_method == 'none': 
        x_offset = data.get('bounds',{}).get('x_offset',0)
        y_offset = data.get('bounds', {}).get('y_offset', 0)
        print("*****",x_o_tofit,x_offset)
        x_o_tofit += x_offset
        y_o_tofit += y_offset
        norm_factor = 100/max(y_o_tofit)
        norm_y = norm_factor * y_o_tofit
        outlier = ColumnDataSource(outlier)
        raw_data = ColumnDataSource(dict(x=x_o_tofit, y=y_o_tofit, yn=norm_y))
        fit_data = ColumnDataSource(dict(x=[], y=[], yn=[], lower=[],
                                         upper=[], upper_n=[], lower_n=[]))
        export_result = dict(fit_para_CI={}, raw_data=raw_data, fit_data=fit_data, tooltip=[],
                             fit_para={}, outlier=outlier, fit_method=fit_method, r_squared=0)
        return export_result

    # start fitting
    fit_para=data.get('fit_para',{})
    fit_para_CI = data.get('fit_para_CI',{})
    func,_b,_a = fit_method_fetcher(fit_method)
    if kwargs.get('new_fit',False) or (not (fit_para and fit_para_CI)):
        # this is performing the fit
        bounds = data.get('bounds',{})
        fit_para,lower_CI,upper_CI = [log_para_coverter(i,to_log=False) for i in fitting_data(x_o_tofit,y_o_tofit,fit_method,**bounds)]
        fit_para_CI = {'lower_CI':lower_CI,'upper_CI':upper_CI}
    else:
        pass
    if fit_method == 'linear':
        x_fit=np.linspace(min(x_o_no_zero)-max(x_o)*0.2,max(x_o)*1.2,200)
    else:
        x_fit=np.geomspace(min(x_o_no_zero)/100.0,max(x_o)*100.0,200)
    y_fit=func(x_fit,**log_para_coverter(fit_para))
    y_fit_lower_CI,y_fit_upper_CI = fit_CI_value(func,x_fit,fit_method,fit_para_CI,fit_para)
    r_squared=data.get('r_squared',False)
    if (not r_squared) or kwargs.get('new_fit',False):
        residuals = y_o_tofit-func(x_o_tofit,**log_para_coverter(fit_para))
        ss_residual = np.sum(residuals**2)
        ss_total = np.sum((y_o_tofit-np.mean(y_o_tofit))**2)
        r_squared = 1- ss_residual/ss_total
    outlier_no_zero = outlier.copy()
    if len(outlier['concentration'])!=0 and (0 in outlier['concentration']):
        outlier_no_zero.update(concentration=[i if i>0 else min_x for i in outlier['concentration']])
    min_yfit = min(y_fit)
    norm_factor = max(y_fit)-min_yfit
    norm_y = (y_o-min_yfit)/norm_factor * 100.0
    norm_y_fit=(y_fit-min_yfit)/norm_factor * 100.0
    upper_n= (y_fit_upper_CI-min_yfit)/norm_factor * 100.0
    lower_n = (y_fit_lower_CI-min_yfit)/norm_factor * 100.0
    raw_data = ColumnDataSource(dict(x=x_o_no_zero,y=y_o,yn=norm_y))
    fit_data = ColumnDataSource(dict(x=x_fit,y=y_fit,yn=norm_y_fit,lower=y_fit_lower_CI,upper=y_fit_upper_CI,upper_n=upper_n,lower_n=lower_n))
    outlier = ColumnDataSource(outlier_no_zero)
    fit_para_ = [(i,"{:.3g}".format(j)) for i,j in fit_para.items() if isinstance(j,float)]
    tooltip = fit_para_+[('R_squared','{:.5f}'.format(r_squared)),('Tag',data.get('tag','No_Tag'))]
    export_result = dict(fit_para_CI=fit_para_CI, raw_data=raw_data, fit_data=fit_data, tooltip=tooltip,
                         fit_para=fit_para, outlier=outlier, fit_method=fit_method, r_squared=r_squared)
    return export_result
