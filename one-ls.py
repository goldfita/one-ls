# Run 'python.exe one-ls.py cli' to test from command line. Make sure to clear out ls-workspace before and
# after testing. When running as a service, dependencies end up in C:\Windows\System32\config\systemprofile,
# and it will fail trying to access that path when you run as your own user.

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
    child_func = None
    log_func = None
    os_name = "linux"
    os_ext = ".sh"
    os_shell = "sh"
    END_OF_INIT_MESSAGE = 'EONELS\n\n\n\n'

    def __init__(self,kill,child,log,os_name):
        self.kill_func = kill
        self.child_func = child
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
        for proc in list(self.lsproc.values()):
            self.kill_func(proc)
                    
    def start(self,conn,addr):
        init_msg = conn.recv(8192)
        if not init_msg:
            self.log_func(f"No data")
            return

        init_data = init_msg[:256].decode().split(self.END_OF_INIT_MESSAGE)
        data = init_data[0].lower().split(':')
        init_data_len = len(init_data[0]) + len(self.END_OF_INIT_MESSAGE)
        if len(data) != 3 or not init_msg[:init_data_len].decode().endswith(self.END_OF_INIT_MESSAGE):
            self.log_func(f"Invalid init message: ({init_msg[:init_data_len]})")
            return

        start_buf = init_msg[init_data_len:]
        n,host,port = data
        if port and not port.isdecimal():
            self.log_func(f"Invalid port: {port}")
            return
        
        self.lsexec = self.__read("exec.conf")
                
        if self.lsexec.get(n):
            self.log_func(f"Language Server {addr}: {n}\nExec: {self.lsexec.get(n)}\nLS_PATH: {LS_PATH}\nShell: {self.os_shell}\nInit: {data}")
        else:
            self.log_func(f"No server {n} found in conf file.")
            return

        # for pipe, last instance will be killed when socket is closed
        if port and self.lsproc.get((n,port)):
            self.log_func(f"Killing existing (pid={self.lsproc[(n,port)].pid}) {n}.")
            self.kill_func(self.lsproc[(n,port)])
            self.lsproc.pop((n,port),None)


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
            ioargs = {"stdout":subprocess.PIPE, "stderr":subprocess.PIPE, "stdin":subprocess.PIPE}
        else:
            self.log_func(f"Configuration not supported for {data}.")
            return

        script = os.path.join(LS_PATH,self.os_name,n) + self.os_ext
        self.lsproc[(n,port)] = subprocess.Popen([self.os_shell,script]+params,shell=False,**ioargs)
        self.lsproc[(n,port)].child_pids = []
        if is_pipe:
            start_new_thread(self.write_client,(conn,self.lsproc[(n,port)]))
            start_new_thread(self.read_client,(conn,(n,port),start_buf))

        
    # You can use socket.makefile() to create a file object from a socket, but on windows the file object isn't a
    # proper file descriptor. So we have to do this manually.
    def write_client(self,conn,proc):
        while self.is_running:
            try:
                buf = os.read(proc.stdout.fileno(),8192)
                #self.log_func(f"Write: {buf}")
                if not buf:
                    err = os.read(proc.stderr.fileno(),8192)
                    if err: self.log_func(err.decode())
                    break
                conn.send(buf)
            except:
                self.log_func(f"Write exception: {proc.args}")
                break
        self.close_connections(conn,proc)
        #self.log_func(f"Write end {proc.args}")

    def read_client(self,conn,key,start_buf):
        # It should be possible to pipe socket output directly into subprocess stdin, but this fails with bad
        # file handle. Gemini says the flag WSA_FLAG_OVERLAPPED needs to be omitted, but there doesn't appear
        # to be any way to do this.
        proc = self.lsproc[key]
        lastbuf = start_buf
        buf = b''
        while self.is_running:
            try:
                # Feeble attempt at making sure we send only complete messages to the language server. This is
                # not guaranteed to work. Note that the init message needs to be passed to the server
                # immediately or everything will be blocked.
                if lastbuf or self.exactly_one_message_received(buf):
                    proc.stdin.write(lastbuf+buf)
                    proc.stdin.flush()
                    lastbuf = b''
                else:
                    #self.log_func(f"LS received incomplete client message: {buf}")
                    lastbuf = buf
                buf = conn.recv(8192)
                #self.log_func(f"Read ({key}): {buf}")
                # attempt to get the child process before it terminates so we can kill the grandchildren
                if not proc.child_pids:
                    proc.child_pids = self.child_func(proc.pid)
                if not buf: break
            except:
                self.log_func(f"Read exception: {proc.args}")
                break
        self.close_connections(conn,proc)
        self.kill_func(proc)
        self.lsproc.pop(key,None)
        #self.log_func(f"Read end {proc.args}")

    def exactly_one_message_received(self,buf):
        try:
            buflines = buf.splitlines(keepends=True)
            clen = 0
            for l in buflines:
                if l.decode().startswith('Content-Length'):
                    clen = int(l.split()[1])
                    break
            ind = buflines.index(b'\r\n')
            rlen = len(''.join([s.decode() for s in buflines[ind+1:]]))
            if clen == rlen:
                return True
        except:
            pass
        return False
        
    def close_connections(self,conn,proc):
        try: conn.close()
        except: pass
        # close hangs
        #for std in [proc.stderr,proc.stdout]:
        #    try: std.close()
        #    except: pass
  
        
class LsServiceWin(win32serviceutil.ServiceFramework):

    _svc_name_ = "Language Server Service"
    _svc_display_name_ = "Language Server Service"
    _svc_description_ = "Starts language servers based on client request."
    #_exe_name_ = os.path.join(os.environ['ONE_LS_PATH'],'pythonservice.exe')

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

        self.ls = LanguageServer(self.kill,self.get_children_pids,self.log,"win")

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

    # There are two scenarios for killing processes: (1) If the client shuts down unexpectedly, the socket
    # will close. In this scenario, the shell and the language server will still be running. Killing the shell
    # doesn't kill the grandchildren; you have to get child pid and kill it to kill the grandchildren. (2) If
    # the client sends a shutdown message, the shell and the language server will quit. The language server
    # should kill its children, but at least for eclipse, it doesn't. You have to get the grandchildren and
    # kill them. The problem is they've been orphaned. To solve that problem, you have to get the child pid
    # while the child is still running. So this needs to have already happened. The process argument should
    # have a 'child_pids' member tacked on containing a list of children of the shell (should just be one).
    def kill(self,proc):
        self.log(f"Killing process: {proc.pid}")
        child_pids = proc.child_pids
        if not child_pids:
            child_pids = self.get_children_pids(proc.pid)
        self.kill_by_pids(child_pids)
        self.kill_children_by_pids(child_pids)
        self.kill_by_pids([proc.pid])

    def log(self,msg):
        if self.cli:
            print(msg)
        else:
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, 0xF000,(msg,''))

    def get_children_pids(self,pid):
        child_pids = []
        try:
            pid_proc = subprocess.Popen(
                f"cmd.exe /C wmic process where (ParentProcessId={pid}) get Caption,ProcessId",
                stdout=subprocess.PIPE)
            stdout,_ = pid_proc.communicate()
            child_pids = [int(l.split()[1]) for l in stdout.splitlines()[1:] if l]
            pid_proc.close()
        except:
            pass
        if child_pids:
            self.log(f"Found children pids: {child_pids}")
        return child_pids

    def kill_by_pids(self,pids):
        for pid in pids:
            try:
                ioargs = {"stdout":subprocess.PIPE, "stderr":subprocess.PIPE}
                kill_proc = subprocess.Popen(f"TASKKILL /F /PID {pid} /T".split(),**ioargs)
                stdout,stderr = kill_proc.communicate()
                kill_proc.close()
            except:
                pass

    def kill_children_by_pids(self,pids):
        for pid in pids:
            children_pids = self.get_children_pids(pid)
            self.kill_by_pids(children_pids)
        
        
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
        
        self.ls = LanguageServer(self.kill,self.get_children_pids,self.log,"linux")

    def stop(self):
        self.ls.stop();
        
    def run(self):
        self.ls.run()
        
    def exit_signal_handler(self,sig,frame):
        self.ls.kill(sig)
        sys.exit()
        
    def kill(self,proc):
        self.log(f"Killing process: {proc.pid}")
        try: proc.send_signal(sig)
        except: pass
        try: proc.kill()
        except: pass

    def log(self,msg):
        print(msg)

    def get_children_pids(self,pid):
        return []


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
