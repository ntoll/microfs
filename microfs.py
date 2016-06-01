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
import ast
import argparse
import sys
import os
import time
import os.path
from serial.tools.list_ports import comports as list_serial_ports
from serial import Serial


__all__ = ['get_version', 'ls', 'rm', 'put', 'get']


#: MAJOR, MINOR, RELEASE, STATUS [alpha, beta, final], VERSION
_VERSION = (1, 0, 0)


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


def get_version():
    """
    Returns a string representation of the version information of this project.
    """
    return '.'.join([str(i) for i in _VERSION])


def find_microbit():
    """
    Finds the port to which the device is connected.
    """
    ports = list_serial_ports()
    for port in ports:
        if "VID:PID=0D28:0204" in port[2].upper():
            return port[0]
    return None


def execute(command):
    """
    Sends the command to the connected micro:bit and returns the result.

    For this to work correctly, a particular sequence of commands needs to be
    sent to put the device into a good state to process the incoming command.

    Returns the stdout and stderr output from the micro:bit.
    """
    port = find_microbit()
    if port is None:
        raise IOError('Could not find micro:bit.')
    with Serial(port, 115200, timeout=1, parity='N') as serial:
        serial.write(b'\x04')  # Send CTRL-D for soft reset.
        time.sleep(0.1)
        serial.write(b'\x03')  # Send CTRL-C to break out of potential loop.
        time.sleep(0.1)
        serial.read_until(b'\r\n>')  # Flush buffer until prompt.
        time.sleep(0.1)
        serial.write(b'\x01')  # Go into raw mode.
        time.sleep(0.1)
        serial.read_until(b'\r\n>OK')  # Flush buffer until raw mode prompt.
        time.sleep(0.1)
        # Write the actual command and send CTRL-D to evaluate.
        serial.write(command.encode('utf-8') + b'\x04')
        result = bytearray()
        while not result.endswith(b'\x04>'):  # Read until prompt.
            time.sleep(0.1)
            result.extend(serial.read_all())
        print(result)
        out, err = result[2:-2].split(b'\x04', 1)  # Split stdout, stderr
        serial.write(b'\x02')  # Send CTRL-B to get out of raw mode.
        time.sleep(0.1)
        serial.write(b'\x04')  # Finally, send CTRL-D for soft reset.
        time.sleep(0.1)
        return out, err


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
    out, err = execute('import os;\nprint(os.listdir())')
    if err:
        raise IOError(clean_error(err))
    return ast.literal_eval(out.decode('utf-8'))


def rm(filename):
    """
    Removes a referenced file on the micro:bit.

    Returns True for success or raises an IOError if there's a problem.
    """
    command = "import os;\nos.remove('{}')".format(filename)
    out, err = execute(command)
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
    with open(filename) as local:
        content = local.read()
    filename = os.path.basename(filename)
    command = "with open('{}', 'w') as f:\n    f.write('''{}''')"
    out, err = execute(command.format(filename, content))
    if err:
        raise IOError(clean_error(err))
    return True


def get(filename):
    """
    Gets a referenced file on the device's file system and copies it to the
    current working directory.

    Returns True for success or raises an IOError if there's a problem.
    """
    command = "with open('{}') as f:\n  print(f.read())"
    out, err = execute(command.format(filename))
    if err:
        raise IOError(clean_error(err))
    with open(filename, 'w') as f:
        f.write(out.decode('utf-8'))
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
