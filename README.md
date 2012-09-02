multistart
==========

Command concurrently connected clients

multistart is a client-server system for concurrent command
execution across multiple clients. You start a server, then
connect one or more clients to it. After that, a connection
through `nc' (or the commander.py script) can be used to send
commands which are executed on each client, as close to
concurrently as possible.

The commander script will wait for a specified number of
clients to send a return status before issuing the next
command, so these scripts can be used to run automated tests
across many hosts.

The basic mechanism of action uses the asyncore and asynchat
Python standard library modules to define a line-oriented
protocol for sending commands and returning exit statuses.

The commands are synchronised by having the server issue the
command to each host, and timing how long it takes to complete
transmission of the command to all hosts. A start command is
then sent, with a start time some multiple of the time taken
to send commands to clients. If the client clocks are
synchronised (e.g. with NTP), this means the command will
be started at approximately the same time on each host.

This is most suited for tasks which take a long time to complete,
relative to the transmission time, though obviously it can
also be used to perform start-up and tear-down steps before
or after a test.
