#!/usr/bin/env python

# multistart.py
# Copyright (C) 2012 Andrew J. Bennieston
# Released under the BSD license; see LICENSE file for details

import asyncore, asynchat, socket
import math
import subprocess
import sys
import threading
import time

class Handler(asynchat.async_chat):
    def __init__(self, sock, address, listener):
        asynchat.async_chat.__init__(self, sock=sock)
        self.listener = listener
        self.address = address
        self.set_terminator("\n")
        self.input_buffer = []
    
    def collect_incoming_data(self, data):
        self.input_buffer.append(data)

    def found_terminator(self):
        request_string = "".join(self.input_buffer)
        self.input_buffer = [ ]
        self.process_request(request_string.strip())

    def handle_close(self):
        try:
            self.close()
        except:
            pass
        self.listener.remove_connection(self)

    def process_request(self, request):
        parts = request.split(' ', 1)
        if len(parts) > 1:
            req = parts[0]
            args = parts[1]
        else:
            req = parts[0]
            args = None
        if req == 'COMMAND':
            self.listener.set_command(args)
        elif req == 'START':
            self.listener.start_client_commands(args)
        elif req == 'SHUTDOWN':
            self.listener.shutdown(args)
        elif req == 'REGISTER':
            self.listener.add_client(self)
        elif req == 'NOTIFY':
            self.listener.add_user(self)
        elif req == 'RETURN':
            self.listener.client_returned(self, args)
        else:
            pass

    def send_command(self, command):
        self.push('COMMAND %s\n' % command)

    def send_start_time(self, time):
        self.push('START %d\n' % time)

    def send_return(self, host, port, rval):
        r_string = 'RETURN %s:%d %d\n' % (host, port, rval)
        self.push(r_string)

    def shutdown(self):
        self.push('SHUTDOWN\n')

class Listener(asyncore.dispatcher):
    def __init__(self, port):
        asyncore.dispatcher.__init__(self)
        # Local stuff
        self.client_handlers = [ ]
        self.active_connections = [ ]
        self.user_connections = [ ]
        self.command = None
        # Socket stuff
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('', port))
        self.listen(5)

    def shutdown(self, args):
        print 'SHUTDOWN received.'
        for client in self.client_handlers:
            client.shutdown()
        sys.exit(0)
    
    def client_returned(self, client, args):
        rval = int(args)
        print 'Client %s:%d returned: %d' % (client.address[0],
                client.address[1], rval)
        for user in self.user_connections:
            user.send_return(client.address[0], client.address[1], rval)

    def remove_connection(self, conn):
        print 'Connection from %s:%d closed.' % (conn.address[0],
                conn.address[1])
        self.active_connections.remove(conn)
        if conn in self.client_handlers:
            print 'Removing client %s:%d' % (conn.address[0],
                    conn.address[1])
            self.client_handlers.remove(conn)
        elif conn in self.user_connections:
            print 'Removing user %s:%d' % (conn.address[0],
                    conn.address[1])
            self.user_connections.remove(conn)

    def set_command(self, command):
        print 'Setting command: %s' % command
        self.command = command
    
    def add_client(self, client):
        print 'Adding client %s:%d' % (client.address[0],
                client.address[1])
        self.client_handlers.append(client)

    def add_user(self, client):
        print 'Adding user %s:%d' % (client.address[0],
                client.address[1])
        self.user_connections.append(client)

    def start_client_commands(self, start_time):
        print 'Starting command on clients'
        # First, send command to each client
        # and time how long it took
        t0 = time.time()
        for client in self.client_handlers:
            client.send_command(self.command)
        t1 = time.time()
        tdiff = t1 - t0
        offset = 5.0 * tdiff
        if start_time is None:
            start_time = time.time()
        start_time += offset
        start_time = int(math.ceil(start_time))
        for client in self.client_handlers:
            client.send_start_time(start_time)

    def handle_accept(self):
        pair = self.accept()
        if pair is None:
            pass
        else:
            sock, addr = pair
            print 'Incoming connection from %s:%d' % (addr[0], addr[1])
            self.active_connections.append(Handler(sock, addr, self))

class Worker(asynchat.async_chat):
    def __init__(self, host, port):
        asynchat.async_chat.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_terminator('\n')
        self.input_buffer = [ ]
        self.command = None
        self.timer = None
        self.connect((host, port))
        self.push('REGISTER\n')

    def collect_incoming_data(self, data):
        self.input_buffer.append(data)

    def found_terminator(self):
        request_string = "".join(self.input_buffer)
        self.input_buffer = [ ]
        self.process_request(request_string)

    def handle_close(self):
        sys.exit(0)

    def run_command(self):
        print 'In run_command()'
        if self.command is not None:
            print 'Running: %s' % self.command
            rv = subprocess.call(self.command, shell=True)
            self.push('RETURN %d\n' % rv)

    def process_request(self, request):
        parts = request.split(' ', 1)
        if len(parts) > 1:
            req = parts[0]
            args = parts[1]
        else:
            req = parts[0]
            args = None

        if req == 'SHUTDOWN':
            print 'Shutting down.'
            self.close()
            sys.exit(0)
        elif req == 'COMMAND':
            print 'Received command: %s' % args
            self.command = args
        elif req == 'START':
            print 'Received start instruction.'
            start_time = int(args)
            dt = start_time - time.time()
            print 'Job starts in %f seconds' % dt
            self.timer = threading.Timer(dt, self.run_command)
            self.timer.start()
        else:
            pass

def usage():
    print 'Usage:\n  %s -s\n  %s -c host port' % (sys.argv[0],
            sys.argv[0])
    print '    -c  Start in client mode'
    print '    -s  Start in server mode'
    print '\nTo control, connect to the server via `nc\' and issue'
    print 'commands from the following list:\n'
    print '  COMMAND string'
    print '    Set command to string'
    print '  START [time]'
    print '    Start commands at time (as soon as possible if'
    print '    no time is given)'
    print '  SHUTDOWN'
    print '    Send shutdown messages to all clients, then quit'
    print '  NOTIFY'
    print '     (Optional) Propagate return status of each client'
    print '     back to the user'

if __name__ == '__main__':
    
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    mode = sys.argv[1]
    if mode == '-s':
        # Start in server mode
        port = 4101
        server = Listener(port)
    elif mode == '-c':
        # Start in client mode
        if len(sys.argv) != 4:
            usage()
            sys.exit(1)
        host = sys.argv[2]
        port = int(sys.argv[3])
        client = Worker(host, port)
    asyncore.loop()

