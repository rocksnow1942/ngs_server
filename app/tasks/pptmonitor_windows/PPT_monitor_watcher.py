from datetime import datetime
import time
import sys
import psutil
import subprocess
import gc
import requests
import logging 
from logging.handlers import RotatingFileHandler
#
# start by batch file
# @echo off
# set root=C:\Users\aptitude\Anaconda3
# call %root%\Scripts\activate.bat %root%
# C:\Users\aptitude\Anaconda3\pythonw.exe "C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor\PPT_monitor_watcher.py"
#
# To auto start on log on:
# use task schedular

running_log = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor\monitor_service_log.txt"
monitor_script = r"C:\Users\aptitude\Aptitude-Cloud\R&D\Users\Hui Kang\Scripts\ppt_monitor\ppt_monitor_windows.py"
post_url = 'http://192.168.86.200/pptmonitor_port'


class FileLogger():
    def __init__(self, running_log="",level="INFO"):
        level = getattr(logging, level.upper(),20)
        logger=logging.getLogger('Monitor')
        logger.setLevel(level)
        fh = RotatingFileHandler(running_log,maxBytes=102400,backupCount=2)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y/%m/%d %I:%M:%S %p'
        ))
        logger.addHandler(fh) 
        self.logger=logger 

        for i in ['debug','info','warning','error','critical']:
            setattr(self,i,getattr(self.logger,i))

    @property
    def time(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        
    def post(self):
        try:
            answer = requests.post(url=post_url, json={
                                   'time': self.time, 'msg': 'monitor'}, timeout=(10, 30))
            self.debug(f'Post answer is : {answer.text}')
            if answer.text == 'restart':
                return True
        except Exception as e:
            self.debug(f'Post failed: {e}')
        return False


def start_script():
    result = subprocess.Popen(
        [sys.executable, monitor_script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result


def main(loglevel='INFO'):
    logger = FileLogger(running_log=running_log , level=loglevel)
    logger.info('Monitor Service Started.')
    monitorpid = start_script()
    logger.info(f'Started ppt monitor script PID= [{monitorpid.pid}].')
    
    while 1:
        try:
            pids = [p.pid for p in psutil.process_iter()]
            if monitorpid.pid not in pids:  # restart if process is gone.
                logger.warning(f'Detected PPT monitor script stopped.')
                try:
                    monitorpid = start_script()
                    logger.info(
                        f'Re-Started ppt monitor PID= [{monitorpid.pid}].')
                except Exception as e:
                    logger.error(f'Start ppt monitor failed. Reason: {e}')

            # check every 600 seconds if the monitor service is running.
            time.sleep(600)

            if logger.post():
                logger.warning(
                    'Detected PPT monitor script not sending post signal.')
                try:
                    monitorpid.kill()
                except Exception as e:
                    logger.error(f"Stop PPT monitor script failed: {e}")
            gc.collect()
        except Exception as e:
            logger.critical(f'Monitor Loop Break: {e}')
            time.sleep(600)
            continue 


if __name__ == '__main__':
    # DEBUG to get more info
    main(loglevel='INFO')
