# -*- coding: utf-8 -*-
"""
This module contains functions for running remote commands on the BBC micro:bit
relating to file system based operations.

You may:

* ls - list files on the device. Based on the equivalent Unix command.
* rm - remove a named file on the device. Based on the Unix command.
* put - copy a named local file onto the device a la equivalent FTP command.
* get - copy a named file from the device to the local file system a la FTP.
"""
from __future__ import print_function
import ast
import argparse
import sys
import os
import time
import os.path
from serial.tools.list_ports import comports as list_serial_ports
from serial import Serial


PY2 = sys.version_info < (3,)


__all__ = ['ls', 'rm', 'put', 'get', 'get_serial']


#: The help text to be shown when requested.
_HELP_TEXT = """
Interact with the basic filesystem on a connected BBC micro:bit device.
You may use the following commands:

'ls' - list files on the device (based on the equivalent Unix command);
'rm' - remove a named file on the device (based on the Unix command);
'put' - copy a named local file onto the device just like the FTP command; and,
'get' - copy a named file from the device to the local file system a la FTP.

For example, 'ufs ls' will list the files on a connected BBC micro:bit.
"""


def find_microbit():
    """
    Finds the port to which the device is connected.
    """
    ports = list_serial_ports()
    for port in ports:
        if "VID:PID=0D28:0204" in port[2].upper():
            return port[0]
    return None


def raw_on(serial):
    """
    Puts the device into raw mode.
    """
    attempts_left = 3
    while attempts_left:
        serial.write(b'\x03')    # Send CTRL-C to break out of loop.
        if serial.read_until(b'\n>>>').endswith(b'\n>>>'):
            break
        attempts_left -= 1
    else:
        raise IOError('Could not enter REPL mode.')
    serial.write(b'\x01')        # Go into raw mode.
    serial.read_until(b'\r\n>')  # Flush buffer until raw mode prompt.


def raw_off(serial):
    """
    Takes the device out of raw mode.
    """
    serial.write(b'\x02')  # Send CTRL-B to get out of raw mode.


def get_serial():
    """
    Detect if a micro:bit is connected and return a serial object to talk to
    it.
    """
    port = find_microbit()
    if port is None:
        raise IOError('Could not find micro:bit.')
    return Serial(port, 115200, timeout=1, parity='N')


def execute(commands, serial=None):
    """
    Sends the command to the connected micro:bit via serial and returns the
    result. If no serial connection is provided, attempts to autodetect the
    device.

    For this to work correctly, a particular sequence of commands needs to be
    sent to put the device into a good state to process the incoming command.

    Returns the stdout and stderr output from the micro:bit.
    """
    if serial is None:
        serial = get_serial()
    result = b''
    raw_on(serial)
    # Write the actual command and send CTRL-D to evaluate.
    for command in commands:
        command_bytes = command.encode('utf-8')
        for i in range(0, len(command_bytes), 32):
            serial.write(command_bytes[i:min(i + 32, len(command_bytes))])
            time.sleep(0.01)
        serial.write(b'\x04')
        response = serial.read_until(b'\x04>')       # Read until prompt.
        out, err = response[2:-2].split(b'\x04', 1)  # Split stdout, stderr
        result += out
        if err:
            return b'', err
    raw_off(serial)
    return result, err


def clean_error(err):
    """
    Take stderr bytes returned from MicroPython and attempt to create a
    non-verbose error message.
    """
    if err:
        decoded = err.decode('utf-8')
        try:
            return decoded.split('\r\n')[-2]
        except Exception:
            return decoded
    return 'There was an error.'


def ls(serial=None):
    """
    List the files on the micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns a list of the files on the connected device or raises an IOError if
    there's a problem.
    """
    out, err = execute([
        'import os',
        'print(os.listdir())',
    ], serial)
    if err:
        raise IOError(clean_error(err))
    return ast.literal_eval(out.decode('utf-8'))


def rm(filename, serial=None):
    """
    Removes a referenced file on the micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns True for success or raises an IOError if there's a problem.
    """
    commands = [
        "import os",
        "os.remove('{}')".format(filename),
    ]
    out, err = execute(commands, serial)
    if err:
        raise IOError(clean_error(err))
    return True


def put(filename, target=None, serial=None):
    """
    Puts a referenced file on the LOCAL file system onto the
    file system on the BBC micro:bit.

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns True for success or raises an IOError if there's a problem.
    """
    if not os.path.isfile(filename):
        raise IOError('No such file.')
    with open(filename, 'rb') as local:
        content = local.read()
    filename = os.path.basename(filename)
    if target is None:
        target = filename
    commands = [
        "fd = open('{}', 'wb')".format(target),
        "f = fd.write",
    ]
    while content:
        line = content[:64]
        if PY2:
            commands.append('f(b' + repr(line) + ')')
        else:
            commands.append('f(' + repr(line) + ')')
        content = content[64:]
    commands.append('fd.close()')
    out, err = execute(commands, serial)
    if err:
        raise IOError(clean_error(err))
    return True


def get(filename, target=None, serial=None):
    """
    Gets a referenced file on the device's file system and copies it to the
    target (or current working directory if unspecified).

    If no serial object is supplied, microfs will attempt to detect the
    connection itself.

    Returns True for success or raises an IOError if there's a problem.
    """
    if target is None:
        target = filename
    commands = [
        "from microbit import uart",
        "f = open('{}', 'rb')".format(filename),
        "r = f.read",
        "result = True",
        "while result:\n    result = r(32)\n    if result:\n        "
        "uart.write(result)\n",
        "f.close()",
    ]
    out, err = execute(commands, serial)
    if err:
        raise IOError(clean_error(err))
    # Recombine the bytes while removing "b'" from start and "'" from end.
    with open(target, 'wb') as f:
        f.write(out)
    return True


def main(argv=None):
    """
    Entry point for the command line tool 'ufs'.

    Takes the args and processes them as per the documentation. :-)

    Exceptions are caught and printed for the user.
    """
    if not argv:
        argv = sys.argv[1:]
    try:
        parser = argparse.ArgumentParser(description=_HELP_TEXT)
        parser.add_argument('command', nargs='?', default=None,
                            help="One of 'ls', 'rm', 'put' or 'get'.")
        parser.add_argument('path', nargs='?', default=None,
                            help="Use when a file needs referencing.")
        parser.add_argument('target', nargs='?', default=None,
                            help="Use to specify a target filename.")
        args = parser.parse_args(argv)
        if args.command == 'ls':
            list_of_files = ls()
            if list_of_files:
                print(' '.join(list_of_files))
        elif args.command == 'rm':
            if args.path:
                rm(args.path)
            else:
                print('rm: missing filename. (e.g. "ufs rm foo.txt")')
        elif args.command == 'put':
            if args.path:
                put(args.path, args.target)
            else:
                print('put: missing filename. (e.g. "ufs put foo.txt")')
        elif args.command == 'get':
            if args.path:
                get(args.path, args.target)
            else:
                print('get: missing filename. (e.g. "ufs get foo.txt")')
        else:
            # Display some help.
            parser.print_help()
    except Exception as ex:
        # The exception of no return. Print exception information.
        print(ex)
