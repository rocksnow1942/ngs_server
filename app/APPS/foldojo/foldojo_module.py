import os,glob
from os import path
from bokeh.models.widgets import Button, TextInput,Div,TextAreaInput,Select,Dropdown, CheckboxGroup,PreText,Tabs,Panel
from bokeh.layouts import widgetbox,column,row,layout
from _structurepredict import Structure,SingleStructureDesign,StructurePerturbation,MultiStructureDesign,Multistrand
import datetime
from MSA import Alignment, buildMSA
from functools import partial

cache_loc=path.join(path.dirname(__file__),'static','cache')


"""
known bug:
weirdly, NUPACK defect function won't work if server start from ~ folder on mac mini.
"""


class Header():
    def __init__(self):
        self.template="""
        <style>
        h1 {{
          position: relative;
          animation: mymove 2s;
          animation-iteration-count: infinite;
        }}

        @keyframes mymove {{
        0%  {{ border:4px outset #81F7F3;  }}
        20% {{ border:4px outset #81F7F3; }}
        50% {{ border:4px outset #ff66ff; }}
        70% {{ border:4px outset #81F7F3; }}
        100%{{ border:4px outset #81F7F3;}}
        }}
        </style>
        <h1 style="width:1050px;height:50px;border: 4px outset #81F7F3;text-align:center;font-family:cursive;font-size:230%;color:#FF00BF;background-color:{color}"">
        &#128540
        <span style="color:#0000FF">F</span>
        <span style="color:red">O</span>
        <span style="color:#FFFF00">L</span>
        <span style="color:#31B404">D</span>
        <span style="color:#FF00BF">ojo </span>
        &#129322
        {subtitle}
        </h1>
        """

    @property
    def default(self):
        return self.template.format(subtitle='',color='#81F7F3')
    @property
    def plot(self):
        return self.template.format(subtitle='Plot Structure Mode',color='#088A85')
    @property
    def exclusion(self):
        return self.template.format(subtitle='Structure Exclusion Mode',color='#0404B4')
    @property
    def single(self):
        return self.template.format(subtitle='Single Strand Design Mode',color='#2EFE2E')
    @property
    def multi(self):
        # two strand design
        return self.template.format(subtitle='Multi-Strand Design',color='#100719')
    @property
    def cofold(self):
        return self.template.format(subtitle='Co-Fold of Multiple Sequences',color='#FE9A2E')
    @property
    def perturb(self):
        return self.template.format(subtitle='Structure Perturbation Mode',color='#F5A9D0')

header=Header()


class structure_prediction():
    """
    class that gives the layout of foldojo
    """
    def __init__(self):
        #parameters default
        width=150
        buttonwidth=150

        # define gadgets
        #inputs
        self.sequence =TextAreaInput(title="Enter Sequence:",value='ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG',
                            rows=7,cols=150,max_length=5000,width=1055,css_classes=['custom1'])
        self.name=TextInput(title='Sequence Name',value='NewSequence',width=width)
        self.inputa_backbone =Select(title='Backbone type:',value='rna',options=[('rna','RNA'),('dna','DNA')],width=width)
        self.inputb_SetTemperature = TextInput(title='Set Temperature (C):',value='37',width=width)
        self.inputc_percent= TextInput(title='Max % suboptimal',value='25',width=width)
        self.inputd_window = TextInput(title='Window',value='2',width=width)
        self.inpute_maxstr = TextInput(title='Max Structure NO',value='8',width=width)
        self.inputf_ForceSingleStranded =TextInput(title='Force Single Strand',value='None',width=width)
        self.inputg_ForceDoubleStranded = TextInput(title='Force Double Strand',value='None',width=width)
        self.inputh_ForcePair = TextInput(title='Force Pair',value='None',width=width)
        self.inputi_ForceProhibitPair = TextInput(title='Force No Pair',value='None',width=width)
        self.method = Select(title='Prediction Algorithm',value='RNAstructure',width=width,
                                    options=[('RNAstructure','RNAstructure'),('ViennaRNA','ViennaRNA'),('Nupack', 'Nupack'),('Compare_RVN','Compare Algorithms')])
        self.parainputs = [i for k,i in sorted(self.__dict__.items(),key=lambda x:x[0]) if k.startswith('input')]

        # align parameters
        self.align_gap = TextInput(title='Align Gap Penalty',value='4',width=width)
        self.align_gapext = TextInput(title='Align GapExt Penalty',value='2',width=width)
        self.align_options = CheckboxGroup(labels=["Align Offset", 'Sequence Order'], active=[1])
        self.align_widget = widgetbox(self.align_gap,self.align_gapext,self.align_options)


        # fold parameters
        self.fold_cluster = Select(title='Structure Filter Method',value='hamming',options=[('hamming','Hamming Distance'),('basepair','Base Pair Distance'),('tree','Tree Edit Distance')],width=150)
        self.fold_center = Select(title='Structure Pick Method',value='energy',options=[('energy','Lowest Energy'),('distance','Distance Centroid')],width=150)
        self.fold_widget = widgetbox(self.fold_cluster,self.fold_center)
        self.default_mode_para = row(self.align_widget,self.fold_widget)
        self.para_settings = column(PreText(text='Default Mode Parameter Settings'),self.default_mode_para)

        # NUPACK parameters
        self.dangles = Select(title='Set Dangle Energy',value='some',width=180,options=[('some','Some'),('all','All'),('none','None')])
        self.pseudo = CheckboxGroup(labels=["Allow Pseudo Knot"], active=[],width=180)
        self.energypara = Select(title='RNA Parameters',value='1995',width=180,options=[('1995','Serra and Turner, 1995'),('1999','Mathews et al., 1999')])
        self.sodium = TextInput(title='Sodium Concentration (M)',value='0.15',width=180)
        self.magnesium = TextInput(title='Magnesium Concentration (M)',value='0.002',width=180)
        self.nupack_para=widgetbox(self.energypara,self.dangles,self.pseudo,self.sodium,self.magnesium)

        # plot mode
        self.plot_mode_energy = TextInput(title='Enter Energy Value',value='-1',width=180)

        # structure exclusion parameters
        self.strexc_threshold = TextInput(title='Exclude structure threshold',value='10',width=180)
        self.strexc_method = Select(title='Structure Match Method',value='match',options=[('match','Exact Match'),
                        ('hamming','Hamming Distance'),('basepair','Base Pair Distance'),('tree','Tree Edit Distance'),('starmatch','Star Match')],width=180)
        self.strexc_strthreshold =  TextInput(title='Structure Match Threshold',value='4',width=180)
        self.strexc_mode_para = widgetbox(self.strexc_threshold,self.strexc_method,self.strexc_strthreshold)

        # perturbation mode parameters
        perturb_mode_explain="""<h2>Structure Perturbation</h2>
        <p>Mutate a number of sites concurrently and promote or inhibit a target structure.</p>
        <p>Only support Nupack/ViennaRNA algorithm.</p>
        """
        self.perturb_mode_explain = Div(text=perturb_mode_explain,width=700,height=100)
        self.perturb_range = TextInput(title='Mutation Region:',value='ALL',width=180)
        self.perturb_n = TextInput(title='Total Mutation Sites:',value='1',width=180)
        self.perturb_iteration = TextInput(title='Maximum Iterations:',value='1000',width=180)
        self.perturb_goal = Select(title="Perturbation Goal",value='inhibit',options=[('inhibit',"Inhibit Target Structure"),('promote',"Promote Target Structure")])
        self.perturb_mode_para=widgetbox(self.perturb_goal,self.perturb_range,self.perturb_n,self.perturb_iteration)


        # single strand parameters
        sgl_nexplaintext = """<h2>Single Strand Design</h2>
        <p>Enter IUPAC notation sequence and target structure. Then predict.</p>
        <p>Use Nupack/ViennaRNA Algorithm is much faster than RNAstructure.</p>
        <p> <b>*</b> is allowed to match any structure. However, This will drastically slow down prediction.</p>
        <h3>IUPAC notation:</h3>
        <p> W=AT S=CG M=AC K=GT R=AG Y=CT B=CGT D=AGT H=ACT V=ACG N=AGCT</p>
        """
        self.sgld_n = TextInput(title='Maximum Iterations:',value='10',width=180)
        self.sgld_top = TextInput(title='Show Top:',value='50',width=180)
        self.sgl_nexplain = Div(text=sgl_nexplaintext,width=700,height=200)
        self.sgld_mdoe_para =widgetbox(self.sgld_n, self.sgld_top,self.strexc_method,self.strexc_strthreshold)


        #multistrand design parameters
        mul_nexplaintext = """<h2>Multiple Strand Design</h2>
        <p>Enter IUPAC notation sequence and target structure. Strands seprated by '+'.</p>
        <h3> Only support <b>NUPACK</b> algorithm. </h3>
        <h3>IUPAC notation:</h3>
        <p> W=AT S=CG M=AC K=GT R=AG Y=CT B=CGT D=AGT H=ACT V=ACG N=AGCT</p>
        """
        self.mul_nexplain=Div(text=mul_nexplaintext,width=700,height=200)

        # cofold parameters
        cofold_nexplaintext="""<h2>Co-Fold</h2>
        <p>Enter sequence and concentration in uM. Enter max allowed complex strands.</p>
        <h3> Only support <b>NUPACK</b> algorithm. </h3>
        """
        self.cofold_nexplain=Div(text=cofold_nexplaintext,width=700,height=150)
        self.maxcofoldstrand = TextInput(title='Max Complex Strands:',value='2',width=180)


        # action buttons
        self.predict = Button(label=chr(9193)+' Predict ',button_type='success',width=buttonwidth,css_classes=['button'])
        self.tools = Dropdown(label=chr(127922)+' Tools ',button_type='success',width=buttonwidth,css_classes=['button'],
        value=None,menu = [('Draw Structure','plot'),None,('Default mode','default'),('Structure Exclusion','exclusion'),('Single Strand Design','single'),
        ('Multi-Strand Design','multi'),('Structure Perturbation','perturb'),None,('Co-Fold','cofold'),]) #('Co-Fold','cofold'),
        self.align = Button(label = chr(128260)+ ' Align',button_type='success',width=buttonwidth,css_classes=['button'])
        self.settings = Dropdown(label=chr(128295)+' Settings', button_type='success',value='.png',css_classes=['button'],
                                    menu = [('Reset Parameter','reset'),None,('As PNG','.png'),('As SVG','.svg')],width=buttonwidth)
        self.help = Button(label=chr(10067)+' Help',button_type='success',width=buttonwidth,)

        # holder for pasting temporary stuff.
        self.holder_1=TextAreaInput(title='Holder',rows=7,cols=100,max_length=5000,width=600,id='test1',css_classes=['custom1'])
        self.holder_2=TextAreaInput(title='Holder',rows=7,cols=100,max_length=5000,width=600,id='texta2',css_classes=['custom1'])
        self.holder_3=TextAreaInput(title='Holder',rows=7,cols=100,max_length=5000,width=600,id='texta3',css_classes=['custom1'])

        self.holder=column(self.holder_1,self.holder_2,self.holder_3)

        # misc
        #
        self.header= Div(text=header.default,width=1000,height=75,css_classes=['custom1'])
        self.plot = Div(text="<h2>Welcome!<br><br>Today is {}.</h2>".format(datetime.datetime.now().strftime("%A, %B %-d")),width=800,height=900,)

        self.text = Div(text='',width=800,height=900)
        self.plottab = Tabs(active=0,width=810,height=930,tabs=[Panel(child=self.plot,title='Output1'),Panel(child=self.text,title='Output2'),
                Panel(child=self.para_settings,title="Parameters"),Panel(child=self.holder,title="Holder")],)
        self.div=Div(width=5,)

        # add callbacks
        self.predict.on_click(self.predict_cb)
        for i in [self.holder_1,self.holder_2,self.holder_3]:
            cb = partial(self.holder_cb,tool=i)
            i.on_change('value',cb)

        # self.predict.callback=CustomJS(args=dict(plot=self.plot),code="""document.getElementById("Test1234").innerHTML = "whatever" """)

        self.tools.on_change('value',self.tools_cb)
        self.method.on_change('value',self.method_cb)
        self.settings.on_change('value',self.settings_cb)
        self.align.on_click(self.align_cb)
        self.help.on_click(self.help_cb)
        self.sequence.on_change('value',self.sequence_cb)

        # layouts
        self.layout=layout([self.header],[self.sequence],[widgetbox(self.name,self.method,*self.parainputs,css_classes=['widgetbox']),self.div,
                    column(row(self.predict,self.align,self.tools,self.settings,
                            self.help),self.plottab,css_classes=['plotarea'])],)


        # status attributes
        self.tool_mode='default'
        self.fold_status={}
        self.last_predict=''
        self.align_status={}
        self.align=Alignment()
        self.showingplot=True
        self.plotbackend = '.png'
        self.structure = None

    def sequence_cb(self,attr,old,new):
        """
        call back to update enter sequence input field title to show GC content info.
        """
        result=self._sequence_cleaner(new,alphabet='small')
        if len(result)!=1:
            self.sequence.title="Enter Sequence: {} entries entered".format(len(result))
            return 0
        seq=result[0].upper()
        length = len(seq)
        A=seq.count('A')
        T=seq.count('T')+seq.count('U')
        G=seq.count('G')
        C=seq.count('C')
        GC = round((G+C)/length*100,1)
        self.sequence.title=f"Enter Sequence: {length} n.t., A:{A}, T/U:{T}, G:{G}, C:{C}, GC:{GC}%"

    def holder_cb(self,attr,old,new,tool=None):
        """
        call back to update holder title.
        """
        seq=new
        A=seq.count('A')
        T=seq.count('T')+seq.count('U')
        G=seq.count('G')
        C=seq.count('C')
        length=A+T+G+C
        if length==0:
            tool.title='Not a Sequence.'
        else:
            GC = round((G+C)/length*100,1)
            tool.title=f"Total n.t.: {length}, A:{A}, T/U:{T}, G:{G}, C:{C}, GC:{GC}%"


    def align_cb(self):
        """
        call back function for align button.
        align funciton is only supported in two mode: default and exclusion mode.
        """
        name=self.name.value
        backend=self.plotbackend
        mode = self.tool_mode
        if backend=='dot': backend='.png'
        try:
            assert mode in 'default,exclusion',('Align not supported in {} mode. It is only supported in \
                            default and structure exclusion mode.'.format(mode))
            self.clear_cache()
            gap=int(self.align_gap.value)
            gapext=int(self.align_gapext.value)
            offset=0 in self.align_options.active
            order=1 in self.align_options.active
            para = dict(gap=gap,gapext=gapext,offset=offset,order=order)
            sequence=self.parsesequence(alphabet='small')
            if mode == 'default':
                if set(sequence)==set(self.align.seq) and para==self.align_status:
                    self.align.name = name
                else:

                    self.align = buildMSA(sequence,name=name,**para)

                    self.align_status=para
                self.sequence.value=self.align.format()
                savename= name +'_LOGO_'+ datetime.datetime.now().strftime("%m%d_%H%M%S") + backend
                save = path.join(cache_loc,savename)

                self.align.dna_logo(save=save,show=False)
                self.text.text="""
                <h3>Alignment LOGO:</h3>
                <img src="foldojo/static/cache/{}"  hspace='20' height='200' width='700'>
                """.format(savename)

                self.display_align()

            elif mode == 'exclusion':
                seq1,seq2=sequence
                ali1 = buildMSA(seq1,name=name,**para)
                ali2 = buildMSA(seq2,name=name,**para)
                ali1s,ali2s=ali1.format(),ali2.format()
                self.sequence.value=ali1s+'\n/\n'+ali2s
                two_align = ali1.align(ali2,name=name,**para)
                self.plot.text="""
                <h3>Alignment</h3>
                <p style= "font-family:monospace">{}</p>
                """.format(two_align.format(index=True,maxlength=95,link=True).replace('\n','</br>'))

        except Exception as e:
            self.plot.text=str(e)

    def display_align(self):
        """
        display align if more than 1 sequence is aligned.
        if only 1 sequence, also dispaly reverse complement sequence,
        """
        align=self.align
        self.plot.text="""
        <h3>Input Sequence Alignment:</h3>
        <p style= "font-family:monospace">{}</p>
        """.format(align.format(index=True,link=True,maxlength=95).replace('\n','</br>'))
        if len(align.seq)==1:
            seq=align.seq[0]
            rcdict=dict(zip('ATCGU','TAGCA'))
            if 'U' in seq:
                rcdict.update(A='U')
            rc=''.join([rcdict[i] for i in seq])[::-1]
            rcalign=Alignment(sequence=rc)
            self.plot.text+="""
            <h3>Reverse Complement, Same index as original sequence:</h3>
            <p style= "font-family:monospace">{}</p>
            """.format(rcalign.format(index=True,reverseindex=True,link=True,maxlength=95).replace('\n','</br>'))
            self.plot.text+="""
            <h3>Reverse Complement:</h3>
            <p style= "font-family:monospace">{}</p>
            """.format(rcalign.format(index=True,link=True,maxlength=95).replace('\n','</br>'))

    def settings_cb(self,attr,old,new):
        """
        settings button callback, offers change plot format and help.
        """
        if new in ['.png','.svg']:
            self.plotbackend = new
            return 0
        elif new == 'reset':
            self.reset_parameters()
            self.settings.value=old

    def help_cb(self):
        self.plot.text=helptext[self.tool_mode]

    def method_toggle(self,method):
        """
        selection available parameters option based on algorithm selection.
        """
        inputs=self.parainputs
        def toggle(*methods):
            for i,j in zip(inputs,methods):
                i.disabled=bool(j)
        if method=='ViennaRNA':
            toggle(1,0,0,0,0,0,0,0,1)
        elif method=='RNAstructure':
            toggle(0,0,0,0,0,0,0,0,0)
        elif method=='Nupack':
            toggle(0,0,0,0,0,1,1,1,1)
        else:
            toggle(0,0,0,0,0,0,0,0,0)

    def method_cb(self,attr,old,new):
        """
        prediction algorithm selection callback. disables unwanted settings options.
        """
        self.method_toggle(new)
        # append additional parameter inputs in parameters tab
        if new in ('Nupack','Compare_RVN'):
            self.para_settings.children.append(self.nupack_para)
        if old in ('Nupack','Compare_RVN'):
            self.para_settings.children.pop(-1)

    def tools_cb(self,attr,old,new):
        """
        change layout or reset parameters.
        """
        if new=='none':
            return 0
        else:
            self.header.text=getattr(header,new)
            self.tool_mode=new
            self.change_parameter(new)
        self.tools.value='none'

    def reset_parameters(self):
        self.plot.text=self.text.text="""
        <h2>Parameters under the hood reset to default.</h2>
        <h4>Align Gap Penalty=4,Align GapExt Penalty=2</h4>
        <h4>Structure Filter Method='hamming', Structure Pick Method='energy'</h4>
        <h4>Dangle Energy='some', Allow Pseudo Knot=False, RNA parameter=1995, Mg=2mM, Na=150mM</h4>
        <h4>Folding status wiped off.</h4>
        <h4>Examples are shown for each mode.</h4>"""
        self.fold_status={}
        self.change_parameter(self.tool_mode)
        self.align_gap.value='4'
        self.align_gapext.value='2'
        self.align_options.active=[1]
        self.fold_cluster.value='hamming'
        self.fold_center.value='energy'
        self.dangles.value='some'
        self.pseudo.active=[]
        self.energypara.value='1995'
        self.sodium.value='0.15'
        self.magnesium.value='0.002'

    def change_parameter(self,mode):
        """
        according to the mode selected,
        change available parameters input fields in paramters tab.
        also changes input field text if not previous operations have started.
        """
        if mode == 'default':
            recommendmethod=self.method.value
            self.para_settings.children = [PreText(text='Default Mode Parameter Settings'),self.default_mode_para]
            if not self.fold_status:self.sequence.value = 'ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG'

        elif mode == 'plot':
            recommendmethod=self.method.value
            self.para_settings.children = [Div(text="<h2>Nothing To Set Here.</h2>"),self.plot_mode_energy]
            if not self.fold_status:self.sequence.value = 'WANTSUBWAYHAMBURGRSTHURSDAYWHACKYSHMUCHYUK\n((((((..((((....))))..((((....))))..))))))'


        elif mode == 'exclusion':
            recommendmethod=self.method.value
            self.para_settings.children = [PreText(text='Structure Exclusion Mode Parameter Settings'),self.strexc_mode_para]
            if not self.fold_status:self.sequence.value = 'ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG\n/\nACCCTTGCTTGCGTAGCATTTTGCCAGTGAGTCGGATCTCCGCATATCACGC'

        elif mode == 'single':
            recommendmethod='ViennaRNA'
            self.para_settings.children = [self.sgl_nexplain,self.sgld_mdoe_para]
            if not self.fold_status:self.sequence.value = 'SWRNATATNYWS\n(((......)))'

        elif mode == 'perturb':
            recommendmethod='ViennaRNA'
            self.para_settings.children = [self.perturb_mode_explain,self.perturb_mode_para]
            if not self.fold_status:self.sequence.value = 'ACCCTTGCTTGCGTAGCATTTTACCAGTGAGTCGGATCTCCGCATATCTGCG\n......(((.(((........))).)))(((......)))((((....))))'

        elif mode == 'multi':
            self.para_settings.children = [self.mul_nexplain,self.sgld_top]
            recommendmethod='Nupack'
            if not self.fold_status:self.sequence.value = 'ACGNNNNNN+NNNNNNNNNNNAGCACNNNNNN\n...((((((+))))))....((((...)))).'

        elif mode == 'cofold':
            self.para_settings.children = [self.cofold_nexplain,self.maxcofoldstrand]
            recommendmethod='Nupack'
            if not self.fold_status:self.sequence.value = 'ACCCTTGCTTGCGTAGCATTTTACCA-1uM\nTGAGTCGGATCTCCGCATATCTGCG-0.5uM'

        self.method_cb(1,'old',self.method.value)
        self.method.value=recommendmethod

    def _sequence_cleaner(self,seq,alphabet='all',**kwargs):
        """
        clean up sequence by filter out unallowed characters.
        """

        alphabets =dict(all="ATGCUWSMKRYBDHVN-(.){}*+",small='ATGCU')

        seq = seq.strip().split('\n')
        result=[]
        for i in seq:
            temp=''.join([j.upper() for j in i.upper() if j in alphabets[alphabet] ])
            if temp:
                result.append(temp)
        return result

    def parsesequence(self,**kwargs):
        """
        output sequence reads based on currently selected tool mode.
        """
        mode =self.tool_mode
        seq = self.sequence.value
        if mode in ['default','plot']:
            return self._sequence_cleaner(seq,**kwargs)
        elif mode == 'exclusion':
            seq1,seq2 = seq.strip().split('/')
            seq1,seq2=self._sequence_cleaner(seq1,**kwargs),self._sequence_cleaner(seq2,**kwargs)
            return seq1,seq2
        elif mode in ['single','perturb','multi']:
            r = self._sequence_cleaner(seq,**kwargs)
            assert len(r)==2,('Must enter two row.')
            assert set(r[1])<=set("(.*){}+"),('Wrong structure format.')
            return r
        elif mode == 'cofold':
            r=seq.strip().split('\n')
            cl,sl=[],[]
            for i in r:
                conc=self.parse_conc(i.split('-')[1])
                s=self._sequence_cleaner(i.split('-')[0],**kwargs)
                cl.append(conc)
                sl.extend(s)
            return sl,cl

    def parse_conc(self,conc):
        """
        convert concentrations string to number in M.
        """
        amout=float(conc.lower().rstrip('nmupf'))
        unit=conc.lower().lstrip('0123456789.')
        unitdict={'um':1e-6,'m':1,'nm':1e-9,'mm':1e-3,'pm':1e-12,'fm':1e-15}
        return amout*unitdict[unit]


    def parsepara(self):
        """
        collect all parameter inputs and return a dict.
        """
        mode =self.tool_mode
        para={'method':self.method.value}
        if self.method.value in ('Nupack','Compare_RVN'):
            pseudo=0 in self.pseudo.active
            sodium=float(self.sodium.value)
            magnesium=float(self.magnesium.value)
            para.update(dangles=self.dangles.value,pseudo=pseudo,energypara=self.energypara.value,sodium=sodium,magnesium=magnesium)

        para.update(cluster=self.fold_cluster.value,center=self.fold_center.value)
        for k,i in filter(lambda x:x[0].startswith('input'),self.__dict__.items()):
            key=k.split('_')[1]
            value=i.value.strip()
            if 'Force' in key:
                if value == 'None' or (not value):
                    continue
                elif '-' in value:
                    _v=[(int(i.split('-')[0]),int(i.split('-')[1])) for i in value.split(',')]
                else:
                    _v=[int(i) for i in value.split(',')]
                para.update({key:_v})
            elif key=='backbone':
                para.update(backbone=value)
            elif key=='SetTemperature':
                para.update({key:float(value)})
            else:
                para.update({key:float(value)})

        if mode == 'exclusion':
            para.update(exclusion={'threshold':float(self.strexc_threshold.value),
                        'method':self.strexc_method.value,'diffthreshold':int(self.strexc_strthreshold.value)})
        if mode in ['single','multi']:
            para.update(n=int(self.sgld_n.value),top=int(self.sgld_top.value),
                        strexc_method=self.strexc_method.value,strexc_threshold=int(self.strexc_strthreshold.value))

        if mode == 'cofold':
            para.update(maxcofoldstrand=int(self.maxcofoldstrand.value))

        if mode =='perturb':
            mutrange = self.perturb_range.value
            if '-' in mutrange:
                mutrange= [(int(i.split('-')[0]),int(i.split('-')[1])) for i in mutrange.split(',')]
            else:
                mutrange=None
            para.update(n=int(self.perturb_n.value),mutrange=mutrange,
                    iteration=int(self.perturb_iteration.value),goal=self.perturb_goal.value)

        return para

    def clear_cache(self):
        """
        remove cache pictures to less than 10.
        """
        file_list = sorted(glob.glob(path.join(cache_loc,'*')),key=lambda x: path.getmtime(x))
        if len(file_list)>10:
            os.remove(file_list[0])
        return len(file_list)

    def predict_cb(self,):
        """
        main entrance for predict button.
        """
        name=self.name.value
        backend=self.plotbackend
        mode=self.tool_mode
        try:
            self.clear_cache()
            sequence=self.parsesequence()

            para=self.parsepara()
            ct=para.copy()
            ct.update(sequence=sequence,name=name,backend=backend,mode=mode)

            if ct == self.fold_status:
                # self.plot.text="""
                # <img src="foldojo/static/cache/{}"  hspace='20' height='{:.0f}' width='{:.0f}'>
                # """.format(*self.last_predict)
                return 0

            # only creaet new structure if sequence and key parameters changed.
            diff=[]
            for k,i in ct.items():
                if i != self.fold_status.get(k,None):
                    diff.append(k)
            plotnew = False
            if set(diff)<=set(['window','name','cluster','center','maxstr']):
                rna=self.structure
                rna.name=name
            else:
                plotnew=True

            #pop out unncessary parameters before pass to fold.
            window=para.pop('window',4)
            cluster = para.pop('cluster','hamming')
            center = para.pop('center','energy')
            maxstr = para.pop('maxstr',8)

            if plotnew:
                lengthlist=[len(i) for i in sequence]
                if mode == 'cofold':
                    self.fold_status=ct
                    return self.update_cofold(sequence,para)
                elif mode == 'default':
                    assert max(lengthlist) == min(lengthlist), ('input sequence not same length')
                    self.sequence.value='\n'.join(sequence)
                    align = Alignment(sequence,name=name)

                    rna=Structure(align,name,save_loc=cache_loc).fold(**para)

                elif mode == 'plot':
                    assert max(lengthlist) == min(lengthlist), ('input sequence not same length')
                    self.sequence.value='\n'.join(sequence)
                    ntseq=[]
                    for i in sequence:
                        if '.' in i or '(' in i:
                            dotbracket = i
                        else: ntseq.append(i)
                    rna=Structure(name=name,save_loc=cache_loc)
                    rna.plot_dot_bracket(dotbracket,seq=ntseq,energy=float(self.plot_mode_energy.value),**para)
                elif mode =='exclusion':
                    self.sequence.value='\n'.join(sequence[0])+'\n/\n'+'\n'.join(sequence[1])
                    align1 = Alignment(sequence[0])
                    align2 = Alignment(sequence[1])
                    exclusionpara=para.pop('exclusion',{})
                    rna=Structure(align1,name,save_loc=cache_loc).fold(**para)
                    b=Structure(align2,name,save_loc=cache_loc).fold(**para)
                    rna.subtract(b,**exclusionpara)
                elif mode in ['single','perturb','multi']:
                    title ={'single':'Single Strand Design',"perturb":"Structure Perturbation",'multi':"Multi-Strand Design"}[mode]
                    self.sequence.value='\n'.join(sequence)
                    seq,target=sequence
                    cls = {'single':SingleStructureDesign,'perturb':StructurePerturbation,'multi':MultiStructureDesign}[mode]
                    ssd=cls(seed=seq,target=target,**para)
                    _=ssd.generate(**para)
                    self.text.text="""
                    <table style="width:100%">
                    <caption style="text-align:center;font-family:cursive;font-size:150%">{} Results: ({}/{:.1e})</caption>
                    {}
                    """.format(title,len(ssd.result),ssd.totalmutation,ssd.to_html())
                    rna=Structure(ssd.result[0][0],name,save_loc=cache_loc).fold(**para)
                self.structure = rna


            save = name +'_'+ datetime.datetime.now().strftime("%m%d_%H%M%S")
            rna.restrict_fold(window,cluster,center)

            if mode not in ['single','perturb','multi']: # avoid update text display in other modes
                self.text.text="""
                <table style="width:100%">
                <caption style="text-align:center;font-family:cursive;font-size:150%">Structure Prediction Results: ({})</caption>
                {}
                """.format(len(rna.dot),rna.print())

            rna.init_dotgraph(maxstr)
            h,w=rna.plot_fold(save=save,plotbackend=backend,showpara=(mode!='plot'))
            figh,figw= 800*h/(max(h,w)),800*w/(max(h,w))
            self.plot.text="""
            <img src="foldojo/static/cache/{}"  hspace='20' height='{:.0f}' width='{:.0f}'>
            """.format(save+backend,figh,figw)
            self.last_predict=(save+backend,figh,figw)
            self.fold_status=ct
        except Exception as e:
            self.plot.text=str(e)

    def update_cofold(self,sequence,para):
        """
        predict button falls to this function call when co-fold mode is active.
        """
        ms=Multistrand(*sequence)
        ms.fold(**para)
        title=' '.join(['S'+str(i+1)+':'+"{:.1e}".format(j) for i,j in enumerate(sequence[1])])
        self.text.text="""
        <table style="width:100%">
        <caption style="text-align:center;font-family:cursive;font-size:150%">Co-Fold Structure: {}</caption>
        {}
        """.format(title,ms.to_html())
        self.plot.text="""
        <table style="width:100%">
        <caption style="text-align:center;font-family:cursive;font-size:150%">Co-Fold Concentration: {}</caption>
        {}
        """.format(title,ms.to_html('complex_df'))

# holds help text for different modes
helptext=dict(
default="""
<h2>Default Mode Help</h2>
<p><b>Enter Sequence</b> Only enter oligo sequence. Case doesn't matter. Enter multiple sequences in new line. Length of sequence,
ATGC count and GC content will be updated once sequence entered.</p>

<p>Set basic prediction parameters on left side of the page. Including: Sequence Name, Algorithm, Backbone, Temperature.<br>
<b>Max % suboptimal</b> is the maximum % difference in free energy in suboptimal structures from the lowest free
energy structure. The higher the number, more suboptimal structures will be predicted. <br>
<b>Window</b> is a parameter that specifies how different the suboptimal
structures should be from each other (larger integers require structures to be more different). <br>
<b>Max Structure NO</b> is the maximum number of suboptimal structures to generate.<br>
<b>Force Single Strand</b> Force one or more nucleotide to be single stranded. format: 1,4,38 <br>
<b>Force Double Strand</b> Force one or more nucleotide to be double stranded. format: 1,4,38 <br>
<b>Force Pair</b> Force a pair between two nucleotides. format: 1-39,2-38,3-37 <br>
<b>Force No Pair</b> Prohibit a pair between two nucleotides. format: save as above.<br></p>

<p>Click <b>Predict</b> will use current paramters to predict secondary structures. Letters outside of <b>"ATGCUWSMKRYBDHVN-(.){}*+"</b> will be filtered out.<br>
Click <b>Align</b> will align the sequences. Letters outside of <b>"ATGCU"</b> will be filtered out.<br>
Click <b>Tools - Reset</b> will reset all parameters.</p>

<p>Click <b>Settings</b> will change the figure format: SVG is vector image format, PNG is rasterized image.</p>
<p>If <b>Mutiple Sequences</b> are entered and aligned, then Predict will show structures common to all the sequences.</p>
<p><b>Parameters Tab settings explained:</b></p>
<p><b>Align gap penalty, Align GapExt Penalty</b>: penalty for alignment.<br>
<b>Structure Filter Method, Structure Pick Method:</b>The method used to filter out similar structures. This setting
combined with "Window" determine how different predicted structures are. Structure Pick method is within similar structures,
which structure is used to represent the common structure.</p>
<p>If using Nupack algorithm, additional settings show up.<br> <b>RNA parameters</b>: choose parameters from a certain literature
to use for prediction.<br><b>Dangle Energy</b>: Check nupack.org for details about dangle energy treatment.<br>
<b>Allow Pseudo Knot:</b> Check this will allow pseudo knot structures be predicted.<br>
<b>Sodium Concentration (M)/Magnesium Concentration (M):</b> Ion concentrations entered will only affect DNA prediction. Unit in Molar.</p>
<p><b>Caution:</b> Any values changed here will also affect Nupack predictions in other modes. Also, the Align and Structure filter
parameters is also applied to other modes.</p>
""",
plot="""
<h2>Plot Mode Help</h2>
<p>Enter <b>Sequence and Dotbracket structure</b> in the input box and click <b>Predict</b> to plot the structure you entered.</p>
<p>If a real sequence is entered, the predicted folding energy and ensemble defect of that structure
is also calculated in the result.</p>
<p>If no proper sequence is entered, the ploted dG is taken from parameters tab, [Enter Energy Value] box.</p>
""",
exclusion="""
<h2>Structure Exclusion Mode Help</h2>
<p>If we know a sequence works and another mutation of it didn't, we can exclude structures that is available to the mutant
and the structures unique to the positive sequence are more likely to be correct.</p>
<p>The sequences above <b>"/"</b> will be considerred positive sequences, the sequences below will be considerred negative.</p>
<p>Click <b>Predict</b> will return the unique structures to positive sequences, and reject structures of negative sequences.</p>
<p><b>Parameters Tab settings explained:</b></p>
<p><b>Exclude structure threshold:</b> fold difference threshold for a structure to be excluded. default is 10. Normally,
if a structure only presented in positive sequence, it will be retained in the result. However, if a structure
showed up in both positive and negative sequence structure ensemble, it doesn't necessarily mean this structure isn't
valid. Its ratio difference in positive and negative sequence ensemble is considerred in this case. If Structure
X consist 10% of positive sequence structure ensemble, and negative sequence structure ensemble have 2% of it.
Because 10%/2% = 5 < 10, structure X will be excluded. However, if X only consist 1%, structure X will be retained.</p>
<p><b>Structure Match Method , Structure Match Threshold</b>: determines how we call two structures identical. Can choose
exact match or other distance measurements. Structures with distance below certain threshold will be considered equal, and
will be subjected to exclusion removal comparison.</p>
""",
single="""
<h2>Single Strand Design Mode Help</h2>
<p>Enter <b>IPUAC notation denoted sequence</b> in the first line, the degenerate sequence is used as template for sequence generation.
In a second line, enter <b>dotbracket structure</b> you want to design.</p>
<p>By design, "*" can be used in dotbracket structure to match paired or unpaired sites. However, use it with caution.
Because this will casue foldojo slow down exponetially when more iterations are tried.</p>
<p>Click <b>Predict</b>, different sequences that match the degenerate sequence will be predict and ordered according to
their deltaG, ratio and Ensemble Defect in the "Output2" tab. the most favorable sequence and its secondary structure will
 be predicted and showed in "Output1" tab.</p>
<p><b>Which Algorithm To Use?</b> Use ViennaRNA or Nupack is preferred due to their speed. RNAstructure is much slower.
However, sequences from Nupack will not always follow the degenerate sequence you provided. (Nupack use the provided
sequence as a "seed" instead of using it as a boundary.)</p>
<p><b>Parameters Tab settings explained:</b></p>
<p><b>Maximum Iterations</b>: how many total random different sequences to test. This will only affect
RNAstructure or ViennaRNA algorithm.</p>
<p><b>Show Top</b>: how many result sequences will be reported. If using Nupack algorithm, only half
the amount entered in "Show Top" will be reported. This is due to different ways foldojo interact with different algorithms.</p>
<p><b>Structure Match Method, Structure Match Threshold</b> When using RNAstructure algorithm, the method and threshold
selected here will be used to match the predicted structure of a random sequence to the desired structure. If using ViennaRNA
 algorithm and "*" is used in structure, method is default to "Star Match".</p>
""",
multi="""
<h2>Multi-Strand Design Mode Help</h2>
<p>This mode is used to design <b>multiple strands that can hybridize into a given structure</b>. Only <b>Nupack</b> algorithm
is supported in this mode.</p>
<p>Enter <b>IPUAC notation denoted sequence</b> in the first line, the degenerate sequence is used as template for sequence generation.
In a second line, enter <b>dotbracket structure</b> you want to design. Separate sequences and structures
in different strands by "+".</p>
<p>Click <b>Predict</b>, different sequences that match the degenerate sequence will be predict and ordered according to
their deltaG, ratio and Ensemble Defect in the "Output2" tab. the most favorable sequence and its secondary structure will
 be predicted and showed in "Output1" tab. The black "+" in secondary structure plot indicate a strand break.</p>
<p><b>Parameters Tab settings explained:</b></p>
<p><b>Show Top</b>/2 is the number of sequences that will be generated.</p>
<p>Refer to help in <b>Default mode</b> for explanation of other parameters for Nupack algorithm.</p>
""",
perturb="""
<h2>Structure Perturbation Mode</h2>
<p>This mode is used to try and test mutate all possible sites in a sequence, to identify mutattions that
either <b>promote</b> or <b>inhibit</b> the ratio of a given structure in predicted ensemble. </p>
<p>Only <b>ViennaRNA</b> and <b>Nupack</b> algorithm is supported in this mode.</p>
<p>Enter Sequence in first line followed by Structre in dotbracket format in second line.</p>
<p>In <b>Parameters</b> tab, choose options.</p>
<p><b>Perturbation Goal</b>: can be inhibit or promote.</p>
<p><b>Mutation Region</b>: select the nucleotide region you want to target the mutation. Limit region can reduce
the search space and make search more thorough. format is 1-5,8-10 : this means n.t. 1 to 5 and 8 to 10 are allowed
mutations sites.</p>
<p><b>Total mutation sites</b>: maximum number of mutations allowed.</p>
<p><b>Maximum Iterations</b>: maximum number of random sequences to try. If total possible permutation is less
than twice the number here, foldojo will try all possible sequences. Otherwise, sequences are randomly generated until
reach the max limit.</p>
<p>Click <b>Predict</b>, different sequences ranked according to the perturbation goal are listed in the "Output2" tab.
The most favorable sequence and its secondary structure will
 be predicted and showed in "Output1" tab.</p>
""",
cofold="""
<h2>Co-Fold Mode</h2>
<p>This mode is used to predict oligo complex concentrations in the equilibrium solution. Only <b>Nupack</b> algorithm is supported
in this mode.</p>
<p>Enter oligo strands in separate lines, each sequence is followed by "-concentration". Molar concentration should be used (pM/nM/uM etc.).</p>
<p>In <b>Parameters</b> tab, enter Max Complex Strands: the maximum number of oligo strands allowed to form in one single complex.</p>
<p>Refer to help in <b>Default mode</b> for explanation of other parameters for Nupack algorithm.</p>
<p>Click <b>Predict</b>, In Output1 tab, the complex species, their ensemble deltaG and their equilibrium concentration
are listed, ranked by their concentrations. In Output2 tab, the Minimum Free Energy structure of each complex species
are denoted in dotbracket format. Their MFE is also shown.</p>
""",
)
