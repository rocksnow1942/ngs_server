import time
import os
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from pathlib import Path,PureWindowsPath
from datetime import datetime
import requests
import logging
from logging.handlers import RotatingFileHandler
import hashlib
import matplotlib.pyplot as plt
import multiprocessing as mp
from collections import deque
import sys
from itertools import zip_longest




SERVER_POST_URL = 'http://192.168.86.200/api/add_echem_pstrace'
SERVER_GET_URL = "http://192.168.86.200/api/get_plojo_data"


MAX_SCAN_GAP = 8 # mas interval to be considerred as two traces in seconds
PRINT_MESSAGES = True # whether print message
PLOT_TRACE = True
INITIATE = True # INITIATE all folder, if already ran alot, this will use a tone of bandwith.
LOG_LEVEL = 'INFO'
PROJECT_FOLDER = 'Echem_Scan'


DEQUE_MAXLENGTH = 3 # how many files in lag to avoid file conflict

# SERVER_POST_URL = 'http://127.0.0.1:5000/api/add_echem_pstrace'
# SERVER_GET_URL = "http://127.0.0.1:5000/api/get_plojo_data"


if 'win' in sys.platform:
    Path = PureWindowsPath

class ProcessPlotter:
    ROW = 3
    COL = 4
    def __init__(self):
        # index is a q of (ams101,chanel name)
        self.index = deque(maxlen=self.ROW * self.COL)

    def terminate(self):
        plt.close('all')

    def call_back(self):
        while self.pipe.poll():
            msg = self.pipe.recv()
            if msg is None:
                self.terminate()
                return False
            else:
                self.index.appendleft(msg)
        r = requests.get(url=SERVER_GET_URL, json={'keys': [i[0] for i in self.index]})
        data = r.json()
        for (k,chanel),ax in zip(self.index,self.axes):
            ax.clear()
            c = data.get(k,{}).get('concentration',[0])
            s = data.get(k, {}).get('signal', [0])
            ax.plot(c,s,color='b',marker='o',linestyle='',markersize=3,markerfacecolor='w')
            ax.set_title(f'{k}-{chanel}')
            ax.set_xlabel('Time / Minutes')
            ax.set_ylabel('Singal / nA')

        self.fig.canvas.draw()
        return True

    def __call__(self, pipe):
        params = {'axes.labelsize': 6,
                  'axes.titlesize': 6,
                  'xtick.labelsize': 6,
                  'ytick.labelsize':6,}
        plt.rcParams.update(params)
        self.pipe = pipe
        self.fig, axes = plt.subplots(self.ROW,self.COL,figsize=(self.COL*2,self.ROW*1.6))
        self.fig.subplots_adjust(top=0.95,bottom=0.1,left=0.1,right=0.9)
        self.axes = [i for j in axes for i in j]
        timer = self.fig.canvas.new_timer(interval=5000)
        timer.add_callback(self.call_back)
        timer.start()
        plt.tight_layout()
        plt.show()


class PlotMessenger:
    def __init__(self):
        self.plot_pipe, plotter_pipe = mp.Pipe()
        self.plotter = ProcessPlotter()
        self.plot_process = mp.Process(
            target=self.plotter, args=(plotter_pipe,), daemon=True)
        self.plot_process.start()

    def plot(self,index=None,chanel = 'Unknown', finished=False):
        send = self.plot_pipe.send
        if finished:
            send(None)
        else:
            send((index, chanel))


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
        pass


    def on_modified(self, event):
        pass


    def on_moved(self, event):
        pass

class PSS_Logger():
    def __init__(self, target_folder="", ploter=None, loglevel='INFO'):
        "target_folder: the folder to watch, "
        self.pstraces = {}
        self.target_foler = target_folder
        self.ploter = ploter

        level = getattr(logging, loglevel.upper(), 20)
        logger = logging.getLogger('Monitor')
        logger.setLevel(level)
        fh = RotatingFileHandler(os.path.join(target_folder,'plojo_upload_log.txt'), maxBytes=10240000000, backupCount=2)
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

        _log_level = ['debug', 'info', 'warning', 'error', 'critical']
        _log_index = _log_level.index(loglevel.lower())
        
        for i in _log_level:
            setattr(self, i,getattr(self.logger, i))
        
        if PRINT_MESSAGES: # if print message, only print for info above that level.
            for i in _log_level[_log_index:]:
                setattr(self, i, wrapper(getattr(self.logger, i)))
            

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
        self.debug(f'Call Created File {file}')
        # self.debug(f"PS traces: {str(self.pstraces)}")
        filepath = Path(file)
        folder = str(filepath.parent)

        if folder not in self.pstraces:
            self.debug(f'Created Folder {folder}')
            self.pstraces[folder] = {'time':[datetime(2000,1,1)],'key':None,'md5':None,
                                    'needtoskip':0,'starttime':None,'keys':[],'deque':deque()}

        if len(self.pstraces[folder]['deque']) >= DEQUE_MAXLENGTH:
            self.pstraces[folder]['deque'].append(file)
            file = self.pstraces[folder]['deque'].popleft()
            self.debug(f'Actually Created File {file}')
        else:
            self.pstraces[folder]['deque'].append(file)
            self.debug(f'Deque length < {DEQUE_MAXLENGTH}, not created.')
            return

        psmethod = file[0:-1] + 'method'
        lasttime = self.pstraces[folder]['time'][-1]
        chanel = Path(file).parts[-3]

        with open(psmethod,'rt',encoding='utf-16') as f:
            psmethoddata = f.read()

        timestring = psmethoddata.split('\n')[2][1:]
        time = datetime.strptime(timestring, '%Y-%m-%d %H:%M:%S')

        # if need to skip , skip this file.
        if self.pstraces[folder]['needtoskip'] > 0:
            self.pstraces[folder]['needtoskip'] -= 1
            self.pstraces[folder]['time'].append(time)
            self.debug(f'Need to skip, still have {self.pstraces[folder]["needtoskip"]} files to skip.')
            return

        # read pss data
        with open(file,'rt') as f:
            pssdata =f.read()

        data = pssdata.strip().split('\n')
        voltage = [float(i.split()[0]) for i in data[1:]]
        amp = [float(i.split()[1]) for i in data[1:]]

        data_tosend = dict(potential=voltage, amp=amp,project = PROJECT_FOLDER,
                           filename=file, date=timestring, chanel=chanel)

        # determine if the data is a new scan or is continued from pervious and handle it.
        if (time - lasttime).seconds > MAX_SCAN_GAP:
            self.debug(f'MAX_SCAN_GAP reached, {(time - lasttime).seconds} seconds.')
            if self.pstraces[folder]['key']:
                self.debug(f'Previous Key stored in keys to save: {self.pstraces[folder]["key"]}.')
                self.pstraces[folder]['keys'].append(
                    (self.pstraces[folder]['key'],datetime.now()))
            self.pstraces[folder]['key'] = None
            self.pstraces[folder]['needtoskip'] = 0
            self.pstraces[folder]['starttime'] = time
            md5 = self.get_md5(pssdata)
            self.pstraces[folder]['md5'] = md5
            data_tosend.update(md5=md5,time=0)
        else:
            self.debug(f'Continuous from previous scan, {(time - lasttime).seconds} seconds, Key={self.pstraces[folder]["key"]}.')
            starttime = self.pstraces[folder]['starttime']
            md5 = self.pstraces[folder]['md5']
            data_tosend.update(time=(time-starttime).seconds/60,key=self.pstraces[folder]['key'],md5=md5)

        self.pstraces[folder]['time'].append(time)

        try:
            response = requests.post(url=SERVER_POST_URL, json=data_tosend)
            if response.status_code == 200:
                result = response.text
                self.debug(f'Response {result} datapack: Filename: {data_tosend["filename"]} Key: {data_tosend.get("key",None)}')
            else:
                self.error(f"Post Data Error - respons code: {response.status_code}, datapacket: {data_tosend}")
                return
        except Exception as e:
            self.error(f"Error - {e}")
            return

        result = result.split('-')

        # depend on the response from server, handle result differently
        if result[0] == 'Add': # if it is starting a new trace
            self.pstraces[folder]['key'] = result[1]
            if PLOT_TRACE:
                self.ploter.plot(index=result[1], chanel = chanel )
            self.info(f'Added - {result[1]} {file}')
        elif result[0] == 'Exist':  # if it's a existing trace.
            self.pstraces[folder]['key'] = result[1]
            self.pstraces[folder]['needtoskip'] = int(result[2]) -1
            self.info(f'Exist - {result[1]} {file}')
        elif result[0] == 'OK':  # if it's continue from a known trace.
            self.info(f"OK - {self.pstraces[folder]['key']} {file}")
        else:
            self.error(f"API-Error - {'-'.join(result)}")

    def wrap_up(self):
        'cleanup stuff'
        for folder in self.pstraces:
            if self.pstraces[folder]['deque']:
                self.debug(f'Wrap Up folder {folder}, deque = {self.pstraces[folder]["deque"]}')
                for file in self.pstraces[folder]['deque']:
                    self.create(file)
            if self.pstraces[folder]['key']:
                self.debug(f'Wrap Up folder {folder}, add key to keys:{self.pstraces[folder]["key"]}')
                self.pstraces[folder]['keys'].append(
                    (self.pstraces[folder]['key'],datetime.now()))
        # sleep 10 seconds before writting.
        time.sleep(10)
        self.write_csv()
        for folder, item in self.pstraces.items():
            keys = item['keys']
            keysstring = ','.join(f"{i[0]}-{i[1].strftime('%Y%m%d %H:%M:%S')}" for i in keys)
            self.info(
                f"Keys in folder {folder} after wrap up: keys = {keysstring}")

    def write_csv(self):
        for folder,item in self.pstraces.items():
            keys = item['keys']
            self.debug(f"Write CSV for {folder}, keys={','.join(i[0] for i in keys)}")
            try:
                # only read the data that was generated at least 10 seconds ago.
                response = requests.get(
                    url=SERVER_GET_URL, json={'keys': [i[0] for i in keys if (datetime.now() - i[1]).seconds >= 10]})
                if response.status_code == 200:
                    result = response.json()
                else:
                    raise ValueError(f"Error Get data - respons code: {response.status_code}, datapacket: {keys}")

                csvname = str(Path(folder).parent) + '.csv'

                # gather data to write in csv
                datatowrite = []
                for key, timestamp in keys:
                    if key in result:
                        time = result[key].get('concentration', None)
                        signal = result[key].get('signal', None)
                        if time and signal:
                            self.debug(
                                f"write time and signal for {key}, time length = {len(time)}, signal length = {len(signal)}")
                            datatowrite.append([key + '_time'] + [str(i) for i in time])
                            datatowrite.append([key + '_signal'] + [str(i) for i in signal])
                        else:
                            self.warning(
                                f"No time or signal in {key},time={time},signal ={signal}")
                    else:
                        self.error(f"Error Write CSV - Key missing {key}")

                with open(csvname, 'wt') as f:
                    for i in zip_longest(*datatowrite,fillvalue=""):
                        f.write(','.join(i))
                        f.write('\n')
            except Exception as e:
                self.error(f"Error Write CSV- {e}")
            # item['keys'] = [i for i in item['keys'] if i not in result]



def start_monitor(target_folder,loglevel='DEBUG'):
    try:
        if PLOT_TRACE:
            Ploter = PlotMessenger()
        else:
            Ploter = None
        observer = Observer()
        logger = PSS_Logger(target_folder=target_folder,ploter=Ploter,loglevel=loglevel)
        logger.info('*****PSS monitor started*****')
        if INITIATE:
            logger.info('****Start initiation.****')
            logger.init()
            logger.info('****Init Done.****')

        observer.schedule(PSS_Handler(logger=logger),target_folder,recursive=True)
        observer.start()
        logger.info(f'****Monitor Started <{target_folder}>.****')
        try:
            while True:
                time.sleep(300)
                logger.write_csv()
        except KeyboardInterrupt:
            logger.wrap_up()
            logger.info(f'****Monitor Stopped****')
            observer.stop()
            observer.join()
        finally:
            Ploter.plot(finished=True)
    except Exception as e:
        logger.error(f'Error during monitoring {e}')



if __name__ == "__main__":
    while 1:
        print('='*20)
        targetfolder = input('Enter folder to monitor:\n').strip()
        PROJECT_FOLDER = input(
            'Enter Project Folder to upload data to: (Default "Echem_Scan")').strip() or PROJECT_FOLDER
        # targetfolder = '/Users/hui/Downloads/test echem folder'
        if os.path.exists(targetfolder):
            start_monitor(targetfolder,loglevel=LOG_LEVEL)
        else:
            print(f"{targetfolder} doesn't exist.\n"+"="*20)
