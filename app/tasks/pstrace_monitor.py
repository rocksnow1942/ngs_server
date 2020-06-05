import time
import os
import re
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path
from datetime import datetime
import requests
import logging
from logging.handlers import RotatingFileHandler
import hashlib
import csv 
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from multiprocessing import Process
import subprocess 
import multiprocessing as mp 
from collections import deque
print(plt.get_backend())

SERVER_POST_URL = 'http://127.0.0.1:5000/api/add_echem_pstrace'
SERVER_GET_URL = "http://127.0.0.1:5000/api/get_plojo_data"
MAX_SCAN_GAP = 8 # in seconds
PRINT_MESSAGES = True
PLOT_TRACE = True


class ProcessPlotter:
    ROW = 3
    COL = 4
    def __init__(self):
        self.index = deque(maxlen=self.ROW * self.COL)

    def terminate(self):
        plt.close('all')

    def call_back(self):
        while self.pipe.poll():
            index = self.pipe.recv()
            if index is None:
                self.terminate()
                return False
            else:
                self.index.appendleft(index)
        r = requests.get(url=SERVER_GET_URL, json={'keys': list(self.index)})
        data = r.json()
        for k,ax in zip(self.index,self.axes):
            ax.clear()
            c = data.get(k,{}).get('concentration',[0])
            s = data.get(k, {}).get('signal', [0])
            ax.plot(c,s,color='b',marker='o',linestyle='',markersize=3,markerfacecolor='w')
            ax.set_title(f'{k} curve',fontsize=8)
            ax.set_xlabel('Time / Minutes')
            ax.set_ylabel('Singal / nA')

        self.fig.canvas.draw()
        return True

    def __call__(self, pipe):
        print('starting plotter...')
        # plt.ion()
        params = {
                  
                  'axes.labelsize': 6,
                  'axes.titlesize': 6,
                  'xtick.labelsize': 6,
                  'ytick.labelsize':6,}
                 


        plt.rcParams.update(params)
        self.pipe = pipe
        self.fig, axes = plt.subplots(self.ROW,self.COL,figsize=(self.COL*2,self.ROW*1.6))
        self.fig.subplots_adjust(top=0.95,bottom=0.1,left=0.1,right=0.9)
        # self.fig.canvas.layout.width = '500px'
        # self.fig.canvas.layout.height = '500px'
        self.axes = [i for j in axes for i in j]
       
        timer = self.fig.canvas.new_timer(interval=5000)
        timer.add_callback(self.call_back)
        timer.start()
        plt.tight_layout()
        print('...done')
        plt.show()


class PlotMessenger:
    def __init__(self):
        self.plot_pipe, plotter_pipe = mp.Pipe()
        self.plotter = ProcessPlotter()
        self.plot_process = mp.Process(
            target=self.plotter, args=(plotter_pipe,), daemon=True)
        self.plot_process.start()

    def plot(self,index=None,finished=False):
        send = self.plot_pipe.send
        if finished:
            send(None)
        else:          
            send(index)



class PSS_Handler(PatternMatchingEventHandler):
    """
    watchdog event listner. 
    """
    def __init__(self, logger):
        super().__init__(patterns=["*.pss",], ignore_patterns=["*~$*", "*Conflict*"],
                         ignore_directories=False, case_sensitive=True)
        self.logger = logger
        self.info = logger.info

    def on_created(self, event):
        self.info(f"Watchdog: Create {event.src_path}")
        self.logger.create(event.src_path)

    def on_deleted(self, event):
        self.info(f"Watchdog: Delete {event.src_path}")
        # self.logger.delete(event.src_path)

    def on_modified(self, event):
        self.info(f"Watchdog: Modify {event.src_path}")
        self.logger.create(event.src_path)

    def on_moved(self, event):
        self.info(
            f"Watchdog: Rename {event.src_path} to {event.dest_path}")

class PSS_Logger():
    def __init__(self, target_folder="", ploter=None, loglevel='INFO'): 
        "target_folder: the folder to watch, "
        self.pstraces = {}
        self.target_foler = target_folder
        self.ploter = ploter
        

        level = getattr(logging, loglevel.upper(), 20)
        logger = logging.getLogger('Monitor')
        logger.setLevel(level)
        fh = RotatingFileHandler(os.path.join(target_folder,'plojo_upload_log.txt'), maxBytes=1024000, backupCount=2)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y/%m/%d %I:%M:%S %p'
        ))
        logger.addHandler(fh)
        self.logger = logger

        def wrapper(func):
            def wrap(msg):
                print(msg)
                return func(msg) 
            return wrap

        for i in ['debug', 'info', 'warning', 'error', 'critical']:
            if PRINT_MESSAGES:
                setattr(self, i, wrapper(getattr(self.logger, i)))
            else:
                setattr(self, i,getattr(self.logger, i))

    def get_md5(self,data):
        hasher = hashlib.md5()
        hasher.update(data.encode('utf-16'))
        return hasher.hexdigest()

    def init(self):
        for root,dirs,files in os.walk(self.target_foler):
            files = [os.path.join(root,file) for file in files if file.endswith('.pss') and (
                'conflict' not in file.lower()) and (not file.startswith('~$'))]
            files = sorted(files,key = lambda x: os.path.getmtime(x))
            for file in files:
                self.create(file)

    def create(self,file):
        ".pss file"
        self.debug(f'Created {file}')
        filepath = Path(file)
        psmethod = file[0:-1] + 'method'
        folder = str(filepath.parent)

        if folder not in self.pstraces:
            self.pstraces[folder] = {'time':[datetime(2000,1,1)],'key':None,'needtoskip':0,'starttime':None,'keys':[]} 
        
        lasttime = self.pstraces[folder]['time'][-1]

        with open(psmethod,'rt',encoding='utf-16') as f:
            psmethoddata = f.read()
            timestring = psmethoddata.split('\n')[2][1:] 
            time = datetime.strptime(timestring, '%Y-%m-%d %H:%M:%S')
        
        
        # if need to skip , skip this file.
        if self.pstraces[folder]['needtoskip'] > 0:
            self.pstraces[folder]['needtoskip'] -= 1
            self.pstraces[folder]['time'].append(time)
            return 
        
        
        with open(file,'rt') as f:
            data =f.read().strip()
            data = data.split('\n')
            voltage = [float(i.split()[0]) for i in data[1:]]
            amp = [float(i.split()[1]) for i in data[1:]]

        data_tosend = dict(potential=voltage,amp=amp,filename=file,date=timestring,)
        
        if (time - lasttime).seconds > MAX_SCAN_GAP:
            if self.pstraces[folder]['key']:
                self.pstraces[folder]['keys'].append(self.pstraces[folder]['key'])
            self.pstraces[folder]['key'] = None 
            self.pstraces[folder]['needtoskip'] = 0 
            self.pstraces[folder]['starttime'] = time 
            
            md5 = self.get_md5(psmethoddata)
            data_tosend.update(md5=md5,time=0)
        else:
            starttime = self.pstraces[folder]['starttime']
            data_tosend.update(time=(time-starttime).seconds/60,key=self.pstraces[folder]['key'])
        
        self.pstraces[folder]['time'].append(time)

        try:
            response = requests.post(url=SERVER_POST_URL, json=data_tosend)
            if response.status_code == 200:
                result = response.text 
            else:
                self.error(f"Error - respons code: {response.status_code}, datapacket: {data_tosend}") 
                return 
        except Exception as e:
            self.error(f"Error - {e}")
            return 

        result = result.split('-')

        if result[0] == 'Add':
            self.pstraces[folder]['key'] = result[1] 
            if PLOT_TRACE:
                
                # self.plot_process=[i for i in self.plot_process if i.is_alive()]
                # self.to_plot.add(result[1]) 
                self.ploter.plot(index=result[1])


                # self.plot_process.append(plottrace(result[1])) 

            self.debug(f'Add - {result[1]} {file}')
        elif result[0] == 'Exist':
            self.pstraces[folder]['key'] = result[1]
            
            self.pstraces[folder]['needtoskip'] = int(result[2]) -1
            self.debug(f'Exist - {result[1]} {file}')
        elif result[0] == 'OK':
            self.debug(f"OK - {self.pstraces[folder]['key']} {file}")
        else:
            self.error(f"API-Error - {'-'.join(result)}") 

    def write_csv(self):
        for folder,item in self.pstraces.items():
            keys = item['keys']
            self.debug(f"Write CSV {','.join(keys)}")
            try:
                response = requests.get(
                    url=SERVER_GET_URL, json={'keys':keys})
                if response.status_code == 200:
                    result = response.json()
                else:
                    raise ValueError(f"Error Get data - respons code: {response.status_code}, datapacket: {keys}")
                
                csvname = str(Path(folder).parent) + '.csv'
                with open(csvname, 'at') as f:
                    writer = csv.writer(f,delimiter=',')
                    for key in keys:
                        if key in result:
                            time = result[key]['concentration']
                            signal = result[key]['signal']
                            writer.writerow([key + '_time'] + time )
                            writer.writerow([key + '_signal'] +signal)
                        else:
                            self.error(f"Error Write CSV - Key missing {key}")
            except Exception as e:
                self.error(f"Error Write CSV- {e}")           
            item['keys'] = []
        

        
def start_monitor(target_folder,loglevel='DEBUG'): 
    # p = Process(target=animateplot, args=('ams1001',))
    # p.start()
    if PLOT_TRACE:
        Ploter = PlotMessenger()
    observer = Observer()
    logger = PSS_Logger(target_folder=target_folder,ploter=Ploter)
    logger.info('*****PSS monitor started*****')
    logger.init()
    logger.info('****Init Done.****')
    observer.schedule(PSS_Handler(logger=logger),target_folder,recursive=True)
    observer.start()
   
    logger.info(f'****Monitor Started <{target_folder}>.****')
    print('PID=', os.getpid())
    try:
       
        while True:
           
            time.sleep(60)
            # while logger.to_plot:
            #     print('PID= Here', os.getpid())
            #     top = logger.to_plot.pop()
            #     print(top)
            #     # subprocess.run(['python','plot_window.py',top])
            #     p = Process(target=animateplot, args=('ams1001',), daemon=True)
            #     p.start()
                # print(p)
                # logger.plot_process.append(p)
            logger.write_csv()
    except KeyboardInterrupt:
        for folder in logger.pstraces:
            if logger.pstraces[folder]['key']:
                logger.pstraces[folder]['keys'].append(logger.pstraces[folder]['key'])
        logger.write_csv()
        logger.info(f'****Monitor Stopped****')
        observer.stop()
        observer.join() 
    finally:
        Ploter.plot(finished=True)

if __name__ == "__main__":
    targetfolder = input('Enter folder to monitor:\n').strip()
    targetfolder = '/Users/hui/Downloads/test echem folder'
    if os.path.exists(targetfolder):
        start_monitor(targetfolder,loglevel='DEBUG')
    else:
        print(f"{targetfolder} doesn't exist.")
