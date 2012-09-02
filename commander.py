#!/usr/bin/env python

# commander.py
# Copyright (C) 2012 Andrew J. Bennieston
# Released under the BSD license; see LICENSE file for details

import asyncore, asynchat, socket
import math
import sys

class Commander(asynchat.async_chat):
    def __init__(self, host, port, command_list, nclients):
        asynchat.async_chat.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_terminator('\n')
        self.input_buffer = [ ]
        self.num_clients = nclients
        self.n_returned = 0
        self.command_list = list(reversed(command_list))
        self.connect((host, port))
        self.push('NOTIFY\n')
        self.send_command()

    def collect_incoming_data(self, data):
        self.input_buffer.append(data)

    def found_terminator(self):
        input_str = ''.join(self.input_buffer)
        self.input_buffer = [ ]
        self.process_input(input_str)

    def handle_close(self):
        sys.exit(0)
    
    def send_command(self):
        if len(self.command_list):
            self.n_returned = 0
            cmd = self.command_list.pop()
            print 'Sending command: %s' % cmd
            self.push('COMMAND %s\n' % cmd)
            self.push('START\n')

    def process_input(self, input_str):
        parts = input_str.split(' ', 1)
        if len(parts) > 1:
            req = parts[0]
            rest = parts[1]
        else:
            req = parts[0]
            rest = None
        if req == 'RETURN':
            self.n_returned += 1
            if self.n_returned == self.num_clients:
                print 'All clients returned'
                if len(self.command_list):
                    self.send_command()
                else:
                    print 'No more commands, stopping multistart'
                    self.push('SHUTDOWN\n')

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print 'Usage: %s host port commandfile nclients' % sys.argv[0]
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    f = open(sys.argv[3], 'r')
    commands = [l.strip() for l in f.readlines()]
    nclients = int(sys.argv[4])
    commander = Commander(host, port, commands, nclients)
    asyncore.loop()

