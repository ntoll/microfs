# -*- coding: utf-8 -*-
"""
Tests for the microfs module.
"""
import sys
import microfs
import pytest


try:
    from unittest import mock
except ImportError:
    import mock


if sys.version_info.major == 2:
    import __builtin__ as builtins
else:
    import builtins


def test_find_micro_bit():
    """
    If a micro:bit is connected (according to PySerial) return the port.
    """
    port = ['/dev/ttyACM3',
            'MBED CMSIS-DAP',
            'USB_CDC USB VID:PID=0D28:0204 ' +
            'SER=9900023431864e45000e10050000005b00000000cc4d28bd ' +
            'LOCATION=4-1.2']
    ports = [port, ]
    with mock.patch('microfs.list_serial_ports', return_value=ports):
        result = microfs.find_microbit()
        assert result == '/dev/ttyACM3'


def test_find_micro_bit_no_device():
    """
    If there is no micro:bit connected (according to PySerial) return None.
    """
    port = ['/dev/ttyACM3',
            'MBED NOT-MICROBIT',
            'USB_CDC USB VID:PID=0D29:0205 ' +
            'SER=9900023431864e45000e10050000005b00000000cc4d28de ' +
            'LOCATION=4-1.3']
    ports = [port, ]
    with mock.patch('microfs.list_serial_ports', return_value=ports):
        result = microfs.find_microbit()
        assert result is None


def test_raw_on():
    """
    Check the expected commands are sent to the device to put MicroPython into
    raw mode.
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(side_effect=[b'\r\n>',
                                                         b'\r\n>OK'])
    microfs.raw_on(mock_serial)
    assert mock_serial.write.call_count == 2
    assert mock_serial.write.call_args_list[0][0][0] == b'\x03'
    assert mock_serial.write.call_args_list[1][0][0] == b'\x01'
    assert mock_serial.read_until.call_count == 2
    assert mock_serial.read_until.call_args_list[0][0][0] == b'\n>'
    assert mock_serial.read_until.call_args_list[1][0][0] == b'\r\n>OK'


def test_raw_off():
    """
    Check that the expected commands are sent to the device to take
    MicroPython out of raw mode.
    """
    mock_serial = mock.MagicMock()
    microfs.raw_off(mock_serial)
    mock_serial.write.assert_called_once_with(b'\x02')


def test_get_serial():
    """
    Ensure that if a port is found then PySerial is used to create a connection
    to the device.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.find_microbit', return_value='/dev/ttyACM3'), \
            mock.patch('microfs.Serial', return_value=mock_serial):
        result = microfs.get_serial()
        assert result == mock_serial


def test_get_serial_no_port():
    """
    An IOError should be raised if no micro:bit is found.
    """
    with mock.patch('microfs.find_microbit', return_value=None):
        with pytest.raises(IOError) as ex:
            microfs.get_serial()
    assert ex.value.args[0] == 'Could not find micro:bit.'


def test_execute():
    """
    Ensure that the expected communication happens via the serial connection
    with the connected micro:bit to facilitate the execution of the passed
    in command.
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(side_effect=[b'\r\n>',
                                                         b'\r\n>OK'])
    mock_serial.read_all = mock.MagicMock(side_effect=[b'OK\x04\x04>',
                                                       b'OK[]\x04\x04>'])
    commands = ['import os', 'os.listdir()', ]
    with mock.patch('microfs.get_serial', return_value=mock_serial), \
            mock.patch('microfs.raw_on', return_value=None) as raw_mon, \
            mock.patch('microfs.raw_off', return_value=None) as raw_moff:
        out, err = microfs.execute(commands, mock_serial)
        # Check the result is correctly parsed.
        assert out == b'[]'
        assert err == b''
        # Check raw_on and raw_off were called.
        raw_mon.assert_called_once_with(mock_serial)
        raw_moff.assert_called_once_with(mock_serial)
        # Check the writes are of the right number and sort (to ensure the
        # device is put into the correct states).
        assert mock_serial.write.call_count == 4
        encoded0 = commands[0].encode('utf-8')
        encoded1 = commands[1].encode('utf-8')
        assert mock_serial.write.call_args_list[0][0][0] == encoded0
        assert mock_serial.write.call_args_list[1][0][0] == b'\x04'
        assert mock_serial.write.call_args_list[2][0][0] == encoded1
        assert mock_serial.write.call_args_list[3][0][0] == b'\x04'


def test_execute_err_result():
    """
    Ensure that if there's a problem reported via stderr on the Microbit, it's
    returned as such by the execute function.
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(side_effect=[b'\r\n>',
                                                         b'\r\n>OK'])
    mock_serial.read_all = mock.MagicMock(return_value=b'OK\x04Error\x04>')
    command = 'import os; os.listdir()'
    with mock.patch('microfs.get_serial', return_value=mock_serial):
        out, err = microfs.execute(command, mock_serial)
        # Check the result is correctly parsed.
        assert out == b''
        assert err == b'Error'


def test_execute_no_serial():
    """
    Ensure that if there's no serial object passed into the execute method, it
    attempts to get_serial().
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(side_effect=[b'\r\n>',
                                                         b'\r\n>OK'])
    mock_serial.read_all = mock.MagicMock(return_value=b'OK\x04Error\x04>')
    command = 'import os; os.listdir()'
    with mock.patch('microfs.get_serial', return_value=mock_serial) as p:
        out, err = microfs.execute(command)
        p.assert_called_once_with()


def test_clean_error():
    """
    Check that given some bytes (derived from stderr) are turned into a
    readable error message: we're only interested in getting the error message
    from the exception, so it's important to strip away all the potentially
    confusing stack trace if it exists.
    """
    msg = (b'Traceback (most recent call last):\r\n '
           b'File "<stdin>", line 2, in <module>\r\n'
           b'File "<stdin>", line 2, in <module>\r\n'
           b'File "<stdin>", line 2, in <module>\r\n'
           b'OSError: file not found\r\n')
    result = microfs.clean_error(msg)
    assert result == "OSError: file not found"


def test_clean_error_no_stack_trace():
    """
    Sometimes stderr may not conform to the expected stacktrace structure. In
    which case, just return a string version of the message.
    """
    msg = b'This does not conform!'
    assert microfs.clean_error(msg) == 'This does not conform!'


def test_clean_error_but_no_error():
    """
    Worst case, the function has been called with empty bytes so return a
    vague message.
    """
    assert microfs.clean_error(b'') == 'There was an error.'


def test_ls():
    """
    If a list is returned as a result in stdout, ensure that the equivalent
    Python list is returned from ls.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.execute', return_value=(b'[ \'a.txt\']\r\n',
                                                     b'')) as execute:
        result = microfs.ls(mock_serial)
        assert result == ['a.txt']
        execute.assert_called_once_with(['import os',
                                        'print(os.listdir())', ], mock_serial)


def test_ls_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.execute', return_value=(b'', b'error')):
        with pytest.raises(IOError) as ex:
            microfs.ls(mock_serial)
    assert ex.value.args[0] == 'error'


def test_rm():
    """
    Given a filename and nothing in stderr from the micro:bit, return True.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.execute', return_value=(b'', b'')) as execute:
        assert microfs.rm('foo', mock_serial)
        execute.assert_called_once_with(["import os", "os.remove('foo')", ],
                                        mock_serial)


def test_rm_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.execute', return_value=(b'', b'error')):
        with pytest.raises(IOError) as ex:
            microfs.rm('foo', mock_serial)
    assert ex.value.args[0] == 'error'


def test_put_python3():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True.
    """
    path = 'tests/fixture_file.txt'
    target = 'remote.txt'
    mock_serial = mock.MagicMock()
    with open(path, 'r') as fixture_file:
        content = fixture_file.read()
        with mock.patch('microfs.execute', return_value=(b'', b'')) as execute:
            with mock.patch('microfs.PY2', False):
                with mock.patch.object(builtins, 'repr',
                                       return_value="b'{}'".format(content)):
                    assert microfs.put(path, target, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format('remote.txt'),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial)


def test_put_no_target_python3():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True.
    """
    path = 'tests/fixture_file.txt'
    mock_serial = mock.MagicMock()
    with open(path, 'r') as fixture_file:
        content = fixture_file.read()
        with mock.patch('microfs.execute', return_value=(b'', b'')) as execute:
            with mock.patch('microfs.PY2', False):
                with mock.patch.object(builtins, 'repr',
                                       return_value="b'{}'".format(content)):
                    assert microfs.put(path, None, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format('fixture_file.txt'),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial)


def test_put_python2():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True when running on Python 2.
    """
    path = 'tests/fixture_file.txt'
    target = 'remote.txt'
    mock_serial = mock.MagicMock()
    with open(path, 'r') as fixture_file:
        content = fixture_file.read()
        with mock.patch('microfs.execute', return_value=(b'', b'')) as execute:
            with mock.patch('microfs.PY2', True):
                with mock.patch.object(builtins, 'repr',
                                       return_value="'{}'".format(content)):
                    assert microfs.put(path, target, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format('remote.txt'),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial)


def test_put_no_target_python2():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True when running on Python 2.
    """
    path = 'tests/fixture_file.txt'
    mock_serial = mock.MagicMock()
    with open(path, 'r') as fixture_file:
        content = fixture_file.read()
        with mock.patch('microfs.execute', return_value=(b'', b'')) as execute:
            with mock.patch('microfs.PY2', True):
                with mock.patch.object(builtins, 'repr',
                                       return_value="'{}'".format(content)):
                    assert microfs.put(path, None, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format('fixture_file.txt'),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial)


def test_put_non_existent_file():
    """
    Raise an IOError if put attempts to work with a non-existent file on the
    local file system.
    """
    mock_serial = mock.MagicMock()
    with pytest.raises(IOError) as ex:
        microfs.put('tests/foo.txt', mock_serial)
    assert ex.value.args[0] == 'No such file.'


def test_put_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.execute', return_value=(b'', b'error')):
        with pytest.raises(IOError) as ex:
            microfs.put('tests/fixture_file.txt', mock_serial)
    assert ex.value.args[0] == 'error'


def test_get():
    """
    Ensure a successful get results in the expected file getting written on
    the local file system with the expected content.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.execute', return_value=(b'hello', b'')) as exe:
        mo = mock.mock_open()
        with mock.patch('microfs.open', mo, create=True):
            assert microfs.get('hello.txt', 'local.txt', mock_serial)
            commands = [
                "from microbit import uart",
                "f = open('{}', 'rb')".format('hello.txt'),
                "r = f.read",
                "result = True",
                "while result:\n    result = r(32)\n    if result:\n        "
                "uart.write(result)\n",
                "f.close()",
            ]
            exe.assert_called_once_with(commands, mock_serial)
            mo.assert_called_once_with('local.txt', 'wb')
            handle = mo()
            handle.write.assert_called_once_with(b'hello')


def test_get_no_target():
    """
    Ensure a successful get results in the expected file getting written on
    the local file system with the expected content. In this case, since no
    target is provided, use the name of the remote file.
    """
    with mock.patch('microfs.execute', return_value=(b'hello', b'')) as exe:
        mo = mock.mock_open()
        with mock.patch('microfs.open', mo, create=True):
            assert microfs.get('hello.txt')
            commands = [
                "from microbit import uart",
                "f = open('{}', 'rb')".format('hello.txt'),
                "r = f.read",
                "result = True",
                "while result:\n    result = r(32)\n    if result:\n        "
                "uart.write(result)\n",
                "f.close()",
            ]
            exe.assert_called_once_with(commands, None)
            mo.assert_called_once_with('hello.txt', 'wb')
            handle = mo()
            handle.write.assert_called_once_with(b'hello')


def test_get_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch('microfs.execute', return_value=(b'', b'error')):
        with pytest.raises(IOError) as ex:
            microfs.get('foo.txt', mock_serial)
    assert ex.value.args[0] == 'error'


def test_main_no_args():
    """
    If no args are passed, simply display help.
    """
    with mock.patch('sys.argv', ['ufs', ]):
        mock_parser = mock.MagicMock()
        with mock.patch('microfs.argparse.ArgumentParser',
                        return_value=mock_parser):
            microfs.main()
        mock_parser.print_help.assert_called_once_with()


def test_main_ls():
    """
    If the ls command is issued, check the appropriate function is called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch('microfs.ls', return_value=['foo', 'bar']) as mock_ls, \
            mock.patch('microfs.get_serial', return_value=mock_class), \
            mock.patch.object(builtins, 'print') as mock_print:
        microfs.main(argv=['ls'])
        mock_ls.assert_called_once_with()
        mock_print.assert_called_once_with('foo bar')


def test_main_ls_no_files():
    """
    If the ls command is issued and no files exist, nothing is printed.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch('microfs.ls', return_value=[]) as mock_ls, \
            mock.patch('microfs.get_serial', return_value=mock_class), \
            mock.patch.object(builtins, 'print') as mock_print:
            microfs.main(argv=['ls'])
            mock_ls.assert_called_once_with()
            assert mock_print.call_count == 0


def test_main_rm():
    """
    If the rm command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch('microfs.rm', return_value=True) as mock_rm, \
            mock.patch('microfs.get_serial', return_value=mock_class):
        microfs.main(argv=['rm', 'foo'])
        mock_rm.assert_called_once_with('foo')


def test_main_rm_no_filename():
    """
    If rm is not called with an associated filename, then print an error
    message.
    """
    with mock.patch('microfs.rm', return_value=True) as mock_rm:
        with mock.patch.object(builtins, 'print') as mock_print:
            microfs.main(argv=['rm'])
            assert mock_print.call_count == 1
            assert mock_rm.call_count == 0


def test_main_put():
    """
    If the put command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch('microfs.put', return_value=True) as mock_put, \
            mock.patch('microfs.get_serial', return_value=mock_class):
        microfs.main(argv=['put', 'foo'])
        mock_put.assert_called_once_with('foo', None)


def test_main_put_no_filename():
    """
    If put is not called with an associated filename, then print an error
    message.
    """
    with mock.patch('microfs.put', return_value=True) as mock_put:
        with mock.patch.object(builtins, 'print') as mock_print:
            microfs.main(argv=['put'])
            assert mock_print.call_count == 1
            assert mock_put.call_count == 0


def test_main_get():
    """
    If the get command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch('microfs.get', return_value=True) as mock_get, \
            mock.patch('microfs.get_serial', return_value=mock_class):
        microfs.main(argv=['get', 'foo'])
        mock_get.assert_called_once_with('foo', None)


def test_main_get_no_filename():
    """
    If get is not called with an associated filename, then print an error
    message.
    """
    with mock.patch('microfs.get', return_value=True) as mock_get:
        with mock.patch.object(builtins, 'print') as mock_print:
            microfs.main(argv=['get'])
            assert mock_print.call_count == 1
            assert mock_get.call_count == 0


def test_main_handle_exception():
    """
    If an exception is raised, then it gets printed.
    """
    ex = ValueError('Error')
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch('microfs.get', side_effect=ex), \
            mock.patch('microfs.get_serial', return_value=mock_class), \
            mock.patch.object(builtins, 'print') as mock_print:
        microfs.main(argv=['get', 'foo'])
        mock_print.assert_called_once_with(ex)
