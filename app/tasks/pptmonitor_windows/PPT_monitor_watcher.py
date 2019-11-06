from datetime import datetime
import time
import sys
import psutil
import subprocess
import gc
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


class FileLogger():
    def __init__(self, running_log=""):
        self.running_log = running_log

    @property
    def time(self):
        return datetime.now().strftime('%y/%m/%d %H:%M:%S')

    def write_log(self, content):
        with open(self.running_log, 'a') as f:
            f.write(f"{self.time} - " + content+'\n')

def start_script():
    result = subprocess.Popen(
        [sys.executable, monitor_script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.pid

def main():
    logger = FileLogger(running_log=running_log)
    logger.write_log('Monitor Service Started.')
    monitorpid = start_script()
    logger.write_log(f'Started ppt monitor script PID= [{monitorpid}].')
    while 1:
        pids = [p.pid for p in psutil.process_iter()]
        if monitorpid not in pids:
            logger.write_log(f'Detected PPT monitor script stopped.')
            monitorpid = None
            try:
                monitorpid = start_script()
                logger.write_log(f'Re-Started ppt monitor PID= [{monitorpid}].')
            except Exception as e:
                logger.write_log(f'Start ppt monitor failed. Reason: {e}')
        time.sleep(30) # check every 30 seconds if the monitor service is running.
        gc.collect()

    logger.write_log('Monitor Service Stopped.')

if __name__ == '__main__':
    main()
