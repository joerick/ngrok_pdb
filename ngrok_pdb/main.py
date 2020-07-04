import socketserver
from pdb import Pdb
from pathlib import Path
import queue
import threading
import sys
import os
import subprocess

input_queue = queue.Queue(1)
output_queue = queue.Queue(1)

def ngrok_executable():
    resources_dir = Path(__file__).parent / 'resources'
    if sys.platform == 'darwin':
        return resources_dir / 'ngrok-darwin'
    elif sys.platform == 'win32':
        return resources_dir / 'ngrok-windows.exe'
    elif sys.platform.startswith('linux'):
        return resources_dir / 'ngrok-linux'
    else:
        raise Exception('unknown platform')

class MyTCPHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        self.is_connected = True
        output_thread = threading.Thread(target=self.relay_output, daemon=True)
        output_thread.start()

        try:
            while True:
                data_in = self.rfile.readline()
                input_queue.put(str(data_in, encoding='utf8'))
        finally:
            input_queue.put('continue')
            self.is_connected = False
            output_thread.join()
    
    def relay_output(self):
        while self.is_connected:
            try:
                data_out = output_queue.get(block=True, timeout=0.5)
                if data_out is not None:
                    self.wfile.write(bytes(data_out, encoding='utf8'))
            except queue.Empty:
                pass


def server_thread_start(timeout):
    HOST, PORT = "localhost", 7952
    # open the ngrok tunnel
    subprocess.run([
        ngrok_executable(), 'authtoken', os.environ['NGROK_AUTH']
    ], check=True)
    ngrok_process = subprocess.Popen([
        ngrok_executable(), 'tcp', str(PORT), '--log=stdout',
    ])

    try:
        with socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler) as server:
            server.timeout = timeout
            # handle one connection, then finish
            server.serve_forever()
    finally:
        ngrok_process.terminate()


def set_trace(timeout=5*60):
    server_thread = threading.Thread(target=server_thread_start, kwargs={'timeout': timeout}, daemon=True)
    server_thread.start()

    class DebuggerInput:
        def readline(self):
            return input_queue.get()
    
    class DebuggerOutput:
        def write(self, string):
            output_queue.put(string)
        def flush(self):
            pass

    debugger = Pdb(
        stdin=DebuggerInput(),
        stdout=DebuggerOutput(),
        skip=['ngrok_pdb'],
        nosigint=True,
    )
    debugger.set_trace(frame=sys._getframe().f_back)

