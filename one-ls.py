import socket
import os
import sys
import signal
import subprocess
import servicemanager
import win32event
import win32service
import win32serviceutil
import threading
import pathlib
from _thread import *


HOST = "0.0.0.0"
PORT = 60000
LS_PATH = os.environ['ONE_LS_PATH']
ROOT_PATH = str(pathlib.Path(LS_PATH).parent.absolute())


class LanguageServer:

    lsproc = {}
    lsexec = {}
    lscomms = {}
    is_running = False
    server_socket = None
    kill_func = None
    log_func = None
    os_name = "linux"
    os_ext = ".sh"
    os_shell = "sh"

    def __init__(self,kill,log,os_name):
        self.kill_func = kill
        self.log_func = log
        self.os_name = os_name
        if os_name == "win":
            self.os_ext = ".ps1"
            self.os_shell = "powershell.exe"

    def __read(self,fname,split=lambda s: s):
        try:
            d = {}
            with open(os.path.join(LS_PATH,fname)) as f:
                for line in f:
                    l = line.strip()
                    if not l or l[0] == '#': continue
                    (key,val) = l.split('=')
                    d[key.strip()] = split(val.strip())
        except:
            pass
        return d
        
    def stop(self):
        self.is_running = False
        if self.server_socket:
            try: self.server_socket.close()
            except: pass

    def run(self):
        self.server_socket = socket.socket()
        self.server_socket.bind((HOST,PORT))
        self.server_socket.listen(5)

        self.is_running = True
        while self.is_running:
            try:
                conn,address = self.server_socket.accept()
                start_new_thread(self.start,(conn,address))
            except:
                pass

        try: conn.close()
        except: pass
        self.kill()
        
    def kill(self,sig=signal.SIGTERM):
        self.log_func(f"Killing all language servers.")
        for proc in self.lsproc.values():
            self.kill_func(proc)
                    
    def start(self,conn,addr):
        init_msg = conn.recv(256).decode()
        if not init_msg: return
        
        data = init_msg.lower().split(':')
        if len(data) != 3:
            self.log_func(f"Invalid init message ({data}).")
            return
        n,host,port = data

        self.lsexec = self.__read("exec.conf")
                
        if self.lsexec.get(n):
            self.log_func(f"Language Server {addr}: {n}.")
        else:
            self.log_func(f"No server {n} found in conf file.")
            return

        # for pipe, last instance will be killed when socket is closed
        if port and self.lsproc.get((n,port)):
            self.log_func(f"Killing existing (pid={self.lsproc[(n,port)].pid}) {n}.")
            self.kill_func(self.lsproc[(n,port)])


        self.lscomms = self.__read("connection.conf",
                                   lambda s: list(map(str.strip,s.split(","))))
        
        ioargs = {}
        is_pipe = False
        params = [ROOT_PATH,self.lsexec[n]]
        if 's' in self.lscomms[n] and not host and port:
            params += ['',port]
            conn.close()
        elif 'c' in self.lscomms[n] and host and port:
            params += [host,port]
            conn.close()
        elif 'p' in self.lscomms[n] and not host and not port:
            is_pipe = True
            ioargs = {"stdout":subprocess.PIPE, "stdin":subprocess.PIPE}
        else:
            self.log_func(f"Configuration not supported for {data}.")
            return

        script = os.path.join(LS_PATH,self.os_name,n) + self.os_ext
        #print(script)
        #print(params)
        self.lsproc[(n,port)] = subprocess.Popen([self.os_shell,script]+params,shell=False,**ioargs)
        #print(self.lsproc[(n,port)].pid)
        if is_pipe:
            start_new_thread(self.write_client,(conn,self.lsproc[(n,port)]))
            start_new_thread(self.read_client,(conn,self.lsproc[(n,port)]))

    # You can use socket.makefile() to create a file object from a socket, but on windows the file object isn't a
    # proper file descriptor. So we have to do this manually.
    def write_client(self,conn,proc):
        while self.is_running:
            try:
                buf = os.read(proc.stdout.fileno(),4096)
                print("++ " + buf.decode())
                if not buf: break
                conn.send(buf)
            except:
                break
        #print("end write")
        self.close_connections(conn,proc)

    def read_client(self,conn,proc):
        while self.is_running:
            try:
                buf = conn.recv(4096)
                print("-- " + buf.decode())
                if not buf: break
                proc.stdin.write(buf)
                proc.stdin.flush()
            except:
                break
        #print("end read")
        self.close_connections(conn,proc)
        self.kill_func(proc)

    def close_connections(self,conn,proc):
        try: conn.close()
        except: pass
        try: proc.stdout.close()
        except: pass
        try: proc.stdin.close()
        except: pass
        
        
class LsServiceWin(win32serviceutil.ServiceFramework):

    _svc_name_ = "LsService"
    _svc_display_name_ = "Language Server Service"
    _svc_description_ = "Starts language servers based on client request."
    #_exe_name_ = "C:\\software\\python\\pythonservice.exe"

    ls = None
    cli = False
    
    def __init__(self,args):
        if args == "cli":
            self.cli = True
            signal.signal(signal.SIGINT,self.exit_signal_handler)
            signal.signal(signal.SIGTERM,self.exit_signal_handler)
            signal.signal(signal.SIGBREAK,self.exit_signal_handler)
        else:
            win32serviceutil.ServiceFramework.__init__(self,args)
            self.hWaitStop = win32event.CreateEvent(None,0,0,None)

        self.ls = LanguageServer(self.kill,self.log,"win")

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.run()
        
    def run(self):
        self.ls.run()

    def stop(self):
        self.ls.stop()
        
    def exit_signal_handler(self,sig,frame):
        self.ls.kill(sig)
        sys.exit()

    def kill(self,proc):
        try:
            subprocess.Popen(f"TASKKILL /F /PID {proc.pid} /T".split())
        except:
            pass

    def log(self,msg):
        if self.cli:
            print(msg)
        else:
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  0xF000,(msg,''))

        
class LsService():

    ls = None
    cli = False
    
    def __init__(self,cli):
        if args == "cli":
            self.cli = True
            signal.signal(signal.SIGINT,self.exit_signal_handler)
            signal.signal(signal.SIGTERM,self.exit_signal_handler)
            signal.signal(signal.SIGKILL,self.exit_signal_handler)
        else:
            raise NotImplementedError
        
        self.ls = LanguageServer(self.kill,self.log,"linux")

    def stop(self):
        self.ls.stop();
        
    def run(self):
        self.ls.run()
        
    def exit_signal_handler(self,sig,frame):
        self.ls.kill(sig)
        sys.exit()
        
    def kill(self,proc):
        try: proc.send_signal(sig)
        except: pass
        try: proc.kill()
        except: pass

    def log(self,msg):
        print(msg)


def cli(service):
    res = None
    while res != 'Q' and res != 'q':
        res = input("Enter 'q' to quit: ")
    service.stop()

    
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        if os.name == "nt":
            service = LsServiceWin(sys.argv[1])
        else:
            service = LsService(sys.argv[1])
        start_new_thread(cli,(service,))
        service.run()
    else:
        win32serviceutil.HandleCommandLine(LsServiceWin)
