from scipy.optimize import least_squares



test="def func(X,*args):\n\t{} = X\n\t{} = args\n\t{}\n\treturn {}".format("A,B,AB","A0,B0,Kd1","y1=A*B-Kd1*AB\n\ty2=A0-A-AB\n\ty3=B0-AB-B","y1,y2,y3")
exec(test)

func([1,2,3],*[1,2,3])

def wrapper():
    test="def func(X,*args):\n\t{} = X\n\t{} = args\n\t{}\n\treturn {}".format("A,B,AB","A0,B0,Kd1","y1=A*B-Kd1*AB\n\ty2=A0-A-AB\n\ty3=B0-AB-B","y1,y2,y3")
    exec(test)
    return func
f=wrapper()

guess = (0.5,0.5,0.5)
lowerbound = [0,0,0]
upperbound = [1,1,1]

result=ls(f,guess,bounds=(lowerbound,upperbound),args=(1,1,1))
result.x

a=1
b=2

sig = eval('a+b')

exec('Fmax=1')


known_variable = ""
unknown_variable = ""
equation = ""

def prep_function(known_variable,unknown_variable,equation):

    kv = [i.strip() for i in known_variable.split(',')]
    ukv = [i.strip() for i in unknown_variable.split(',')]
    eq = [i.strip().split('=')[0] for i in equation.split('\n') if i]
    assert len(eq)==len(ukv), ('{} equations but {} variables'.format(len(eq),len(ukv)))
    funcstring = "def testfunction(X,*args):\n\t{}=X\n\t{}=args\n\treturn {}".format(','.join(ukv),','.join(kv),','.join(eq))
    exec(funcstring,locals())
    print(funcstring)
    return locals()['testfunction'],kv,ukv


def func(X,*args):
	A,B,AB=X
	A0,B0,Kd1=args
	return A*B-Kd1*AB,A0-A-AB,B0-AB-B

f,kv,ukv=prep_function("A0,B0,Kd1","A,B,AB","A*B-Kd1*AB=0\nA0-A-AB=0\nB0-AB-B=0\n")
kv
ukv
_plot='AB/B0'
_against = 'A0'
_kv_arg = [1,1]
_bound = None
_against_start=1

def line_solver(_f,_kv,_ukv,_plot,_against,_kv_arg,_bound=None,_against_start=1):
    """
    f: function from prep_function
    kv: known_variable signature
    unk: unknown_variable signature
    plot: formula to plot
    against : one of the known variable to plot against
    kv_arg : list of the other known variable value
    bound :tuple of two list, uppder and lower bound of unknown_variable boundary; "([{}],[{}])"
    generate dots at 1.2 X up or down, until flat or up to 1e6, low to 1e-6
    _against_start: starting point of the against value
    all units are in nM.
    """
    def point_solver(against_value):
        nonlocal _bound
        args = list(_kv_arg)
        args.insert(kv.index(_against),against_value)
        for _n,_value in zip(_kv,args):
            exec(f"{_n}={_value}")
        if _bound==None:
            _bound=([0]*len(_ukv),[1e6]*len(_ukv))
            _guess = [1]*(len(_ukv))
        else:
            _bound = eval(_bound)
            _guess = [ (i+j)/2 for i,j in zip(*_bound)]
        _result = least_squares(_f,_guess,args=tuple(args),bounds=_bound)
        for _n,_value in zip(_ukv, _result.x):
            exec(f"{_n}={_value}")
        return eval(_plot)
    return point_solver(_against_start)

line_solver(f,kv,ukv,_plot,_against,_kv_arg,_bound,_against_start)
