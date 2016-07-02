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


__all__ = ['ls', 'rm', 'put', 'get']


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
    serial.write(b'\x03')  # Send CTRL-C to break out of loop.
    serial.read_until(b'\n>')  # Flush buffer until prompt.
    serial.write(b'\x01')  # Go into raw mode.
    serial.read_until(b'\r\n>OK')  # Flush buffer until raw mode prompt.


def raw_off(serial):
    """
    Takes the device out of raw mode.
    """
    serial.write(b'\x02')  # Send CTRL-B to get out of raw mode.


def execute(commands):
    """
    Sends the command to the connected micro:bit and returns the result.

    For this to work correctly, a particular sequence of commands needs to be
    sent to put the device into a good state to process the incoming command.

    Returns the stdout and stderr output from the micro:bit.
    """
    port = find_microbit()
    result = b''
    if port is None:
        raise IOError('Could not find micro:bit.')
    with Serial(port, 115200, timeout=1, parity='N') as serial:
        raw_on(serial)
        # Write the actual command and send CTRL-D to evaluate.
        for command in commands:
            command_bytes = command.encode('utf-8')
            for i in range(0, len(command_bytes), 32):
                serial.write(command_bytes[i:min(i + 32, len(command_bytes))])
                time.sleep(0.01)
            serial.write(b'\x04')
            response = bytearray()
            while not response.endswith(b'\x04>'):  # Read until prompt.
                response.extend(serial.read_all())
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
        except:
            return decoded
    return 'There was an error.'


def ls():
    """
    Returns a list of the files on the connected device or raises an IOError if
    there's a problem.
    """
    out, err = execute([
        'import os',
        'print(os.listdir())',
    ])
    if err:
        raise IOError(clean_error(err))
    return ast.literal_eval(out.decode('utf-8'))


def rm(filename):
    """
    Removes a referenced file on the micro:bit.

    Returns True for success or raises an IOError if there's a problem.
    """
    commands = [
        "import os",
        "os.remove('{}')".format(filename),
    ]
    out, err = execute(commands)
    if err:
        raise IOError(clean_error(err))
    return True


def put(filename):
    """
    Puts a referenced file on the LOCAL file system onto the file system on
    the BBC micro:bit.

    Returns True for success or raises an IOError if there's a problem.
    """
    if not os.path.isfile(filename):
        raise IOError('No such file.')
    with open(filename, 'rb') as local:
        content = local.read()
    filename = os.path.basename(filename)
    commands = [
        "fd = open('{}', 'wb')".format(filename),
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
    out, err = execute(commands)
    if err:
        raise IOError(clean_error(err))
    return True


def get(filename):
    """
    Gets a referenced file on the device's file system and copies it to the
    current working directory.

    Returns True for success or raises an IOError if there's a problem.
    """
    commands = [
        "f = open('{}', 'rb')".format(filename),
        "r = f.read",
        "result = True",
        "while result:\n    result = r(32)\n    if result:\n        "
        "uart.write(result)\n",
        "f.close()",
    ]
    out, err = execute(commands)
    if err:
        raise IOError(clean_error(err))
    # Recombine the bytes while removing "b'" from start and "'" from end.
    with open(filename, 'wb') as f:
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
                put(args.path)
            else:
                print('put: missing filename. (e.g. "ufs put foo.txt")')
        elif args.command == 'get':
            if args.path:
                get(args.path)
            else:
                print('get: missing filename. (e.g. "ufs get foo.txt")')
        else:
            # Display some help.
            parser.print_help()
    except Exception as ex:
        # The exception of no return. Print exception information.
        print(ex)
