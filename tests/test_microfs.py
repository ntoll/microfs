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
    If a micro:bit is connected (according to PySerial) return the port and
    serial number.
    """

    class FakePort:
        """
        Pretends to be a representation of a port in PySerial.
        """

        def __init__(self, port_info, serial_number):
            self.port_info = port_info
            self.serial_number = serial_number

        def __getitem__(self, key):
            return self.port_info[key]

    serial_number = "9900023431864e45000e10050000005b00000000cc4d28bd"
    port_info = [
        "/dev/ttyACM3",
        "MBED CMSIS-DAP",
        "USB_CDC USB VID:PID=0D28:0204 "
        "SER=9900023431864e45000e10050000005b00000000cc4d28bd "
        "LOCATION=4-1.2",
    ]
    port = FakePort(port_info, serial_number)
    ports = [
        port,
    ]
    with mock.patch("microfs.list_serial_ports", return_value=ports):
        result = microfs.find_microbit()
        assert result == ("/dev/ttyACM3", serial_number)


def test_find_micro_bit_no_device():
    """
    If there is no micro:bit connected (according to PySerial) return None.
    """
    port = [
        "/dev/ttyACM3",
        "MBED NOT-MICROBIT",
        "USB_CDC USB VID:PID=0D29:0205 "
        "SER=9900023431864e45000e10050000005b00000000cc4d28de "
        "LOCATION=4-1.3",
    ]
    ports = [
        port,
    ]
    with mock.patch("microfs.list_serial_ports", return_value=ports):
        result = microfs.find_microbit()
        assert result == (None, None)


def test_raw_on():
    """
    Check the expected commands are sent to the device to put MicroPython into
    raw mode.
    """
    mock_serial = mock.MagicMock()
    mock_serial.inWaiting.return_value = 0
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n",
        b"raw REPL; CTRL-B to exit\r\n>",
    ]
    mock_serial.read_until.side_effect = data
    microfs.raw_on(mock_serial)
    assert mock_serial.inWaiting.call_count == 2
    assert mock_serial.write.call_count == 6
    assert mock_serial.write.call_args_list[0][0][0] == b"\x02"
    assert mock_serial.write.call_args_list[1][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[2][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[3][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[4][0][0] == b"\r\x01"
    assert mock_serial.write.call_args_list[5][0][0] == b"\x04"
    assert mock_serial.read_until.call_count == 3
    assert mock_serial.read_until.call_args_list[0][0][0] == data[0]
    assert mock_serial.read_until.call_args_list[1][0][0] == data[1]
    assert mock_serial.read_until.call_args_list[2][0][0] == data[2]

    mock_serial.reset_mock()
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n",
        b"foo\r\n",
        b"raw REPL; CTRL-B to exit\r\n>",
    ]
    mock_serial.read_until.side_effect = data
    microfs.raw_on(mock_serial)
    assert mock_serial.inWaiting.call_count == 2
    assert mock_serial.write.call_count == 7
    assert mock_serial.write.call_args_list[0][0][0] == b"\x02"
    assert mock_serial.write.call_args_list[1][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[2][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[3][0][0] == b"\r\x03"
    assert mock_serial.write.call_args_list[4][0][0] == b"\r\x01"
    assert mock_serial.write.call_args_list[5][0][0] == b"\x04"
    assert mock_serial.write.call_args_list[6][0][0] == b"\r\x01"
    assert mock_serial.read_until.call_count == 4
    assert mock_serial.read_until.call_args_list[0][0][0] == data[0]
    assert mock_serial.read_until.call_args_list[1][0][0] == data[1]
    assert mock_serial.read_until.call_args_list[2][0][0] == data[3]
    assert mock_serial.read_until.call_args_list[3][0][0] == data[3]


def test_raw_on_failures():
    """
    Check problem data results in an IO error.
    """
    mock_serial = mock.MagicMock()
    mock_serial.inWaiting.side_effect = [5, 3, 2, 1, 0]
    data = [
        b"raw REPL; CTRL-B to exit\r\n> foo",
    ]
    mock_serial.read_until.side_effect = data
    with pytest.raises(IOError) as ex:
        microfs.raw_on(mock_serial)
    assert ex.value.args[0] == "Could not enter raw REPL."
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n foo",
    ]
    mock_serial.read_until.side_effect = data
    mock_serial.inWaiting.side_effect = [5, 3, 2, 1, 0]
    with pytest.raises(IOError) as ex:
        microfs.raw_on(mock_serial)
    assert ex.value.args[0] == "Could not enter raw REPL."
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n",
        b"foo",
        b"foo",
    ]
    mock_serial.read_until.side_effect = data
    mock_serial.inWaiting.side_effect = None
    mock_serial.inWaiting.return_value = 0
    with pytest.raises(IOError) as ex:
        microfs.raw_on(mock_serial)
    assert ex.value.args[0] == "Could not enter raw REPL."


def test_raw_on_failures_command_line_flag_on():
    """
    If the COMMAND_LINE_FLAG is True, ensure the last data received is output
    via the print statemen for debugging purposes.
    """
    with mock.patch("builtins.print") as mock_print, mock.patch(
        "microfs.COMMAND_LINE_FLAG", True
    ):
        mock_serial = mock.MagicMock()
        mock_serial.inWaiting.side_effect = [5, 3, 2, 1, 0]
        data = [
            b"raw REPL; CTRL-B to exit\r\n> foo",
        ]
        mock_serial.read_until.side_effect = data
        with pytest.raises(IOError) as ex:
            microfs.raw_on(mock_serial)
        mock_print.assert_called_once_with(data[0])
        assert ex.value.args[0] == "Could not enter raw REPL."
        mock_print.reset_mock()

        data = [
            b"raw REPL; CTRL-B to exit\r\n>",
            b"soft reboot\r\n foo",
        ]
        mock_serial.read_until.side_effect = data
        mock_serial.inWaiting.side_effect = [5, 3, 2, 1, 0]
        with pytest.raises(IOError) as ex:
            microfs.raw_on(mock_serial)
        mock_print.assert_called_once_with(data[1])
        assert ex.value.args[0] == "Could not enter raw REPL."
        mock_print.reset_mock()
        data = [
            b"raw REPL; CTRL-B to exit\r\n>",
            b"soft reboot\r\n",
            b"foo",
            b"foo",
        ]
        mock_serial.read_until.side_effect = data
        mock_serial.inWaiting.side_effect = None
        mock_serial.inWaiting.return_value = 0
        with pytest.raises(IOError) as ex:
            microfs.raw_on(mock_serial)
        mock_print.assert_called_once_with(data[3])
        assert ex.value.args[0] == "Could not enter raw REPL."


def test_raw_off():
    """
    Check that the expected commands are sent to the device to take
    MicroPython out of raw mode.
    """
    mock_serial = mock.MagicMock()
    microfs.raw_off(mock_serial)
    assert mock_serial.write.call_count == 1
    assert mock_serial.write.call_args_list[0][0][0] == b"\x02"


def test_get_serial():
    """
    Ensure that if a port is found then PySerial is used to create a connection
    to the device.
    """
    mock_serial = mock.MagicMock()
    mock_result = (
        "/dev/ttyACM3",
        "9900000031864e45003c10070000006e0000000097969901",
    )
    with mock.patch(
        "microfs.find_microbit", return_value=mock_result
    ), mock.patch("microfs.Serial", return_value=mock_serial):
        result = microfs.get_serial(1)
        assert result == mock_serial


def test_get_serial_no_port():
    """
    An IOError should be raised if no micro:bit is found.
    """
    with mock.patch("microfs.find_microbit", return_value=(None, None)):
        with pytest.raises(IOError) as ex:
            microfs.get_serial()
    assert ex.value.args[0] == "Could not find micro:bit."


def test_execute():
    """
    Ensure that the expected communication happens via the serial connection
    with the connected micro:bit to facilitate the execution of the passed
    in command.
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(
        side_effect=[b"OK\x04\x04>", b"OK[]\x04\x04>"]
    )
    commands = [
        "import os",
        "os.listdir()",
    ]
    with mock.patch(
        "microfs.get_serial", return_value=mock_serial
    ), mock.patch("microfs.raw_on", return_value=None) as raw_mon, mock.patch(
        "microfs.raw_off", return_value=None
    ) as raw_moff:
        out, err = microfs.execute(commands, mock_serial)
        # Check the result is correctly parsed.
        assert out == b"[]"
        assert err == b""
        # Check raw_on and raw_off were called.
        raw_mon.assert_called_once_with(mock_serial)
        raw_moff.assert_called_once_with(mock_serial)
        # Check the writes are of the right number and sort (to ensure the
        # device is put into the correct states).
        assert mock_serial.write.call_count == 4
        encoded0 = commands[0].encode("utf-8")
        encoded1 = commands[1].encode("utf-8")
        assert mock_serial.write.call_args_list[0][0][0] == encoded0
        assert mock_serial.write.call_args_list[1][0][0] == b"\x04"
        assert mock_serial.write.call_args_list[2][0][0] == encoded1
        assert mock_serial.write.call_args_list[3][0][0] == b"\x04"


def test_execute_err_result():
    """
    Ensure that if there's a problem reported via stderr on the Microbit, it's
    returned as such by the execute function.
    """
    mock_serial = mock.MagicMock()
    mock_serial.inWaiting.return_value = 0
    data = [
        b"raw REPL; CTRL-B to exit\r\n>",
        b"soft reboot\r\n",
        b"raw REPL; CTRL-B to exit\r\n>",
        b"OK\x04Error\x04>",
    ]
    mock_serial.read_until.side_effect = data
    command = "import os; os.listdir()"
    with mock.patch("microfs.get_serial", return_value=mock_serial):
        out, err = microfs.execute(command, mock_serial)
        # Check the result is correctly parsed.
        assert out == b""
        assert err == b"Error"


def test_execute_no_serial():
    """
    Ensure that if there's no serial object passed into the execute method, it
    attempts to get_serial().
    """
    mock_serial = mock.MagicMock()
    mock_serial.read_until = mock.MagicMock(
        side_effect=[b"OK\x04\x04>", b"OK[]\x04\x04>"]
    )
    commands = [
        "import os",
        "os.listdir()",
    ]
    with mock.patch(
        "microfs.get_serial", return_value=mock_serial
    ) as p, mock.patch("microfs.raw_on", return_value=None), mock.patch(
        "microfs.raw_off", return_value=None
    ):
        out, err = microfs.execute(commands)
        p.assert_called_once_with(1)
        mock_serial.close.assert_called_once_with()


def test_clean_error():
    """
    Check that given some bytes (derived from stderr) are turned into a
    readable error message: we're only interested in getting the error message
    from the exception, so it's important to strip away all the potentially
    confusing stack trace if it exists.
    """
    msg = (
        b"Traceback (most recent call last):\r\n "
        b'File "<stdin>", line 2, in <module>\r\n'
        b'File "<stdin>", line 2, in <module>\r\n'
        b'File "<stdin>", line 2, in <module>\r\n'
        b"OSError: file not found\r\n"
    )
    result = microfs.clean_error(msg)
    assert result == "OSError: file not found"


def test_clean_error_no_stack_trace():
    """
    Sometimes stderr may not conform to the expected stacktrace structure. In
    which case, just return a string version of the message.
    """
    msg = b"This does not conform!"
    assert microfs.clean_error(msg) == "This does not conform!"


def test_clean_error_but_no_error():
    """
    Worst case, the function has been called with empty bytes so return a
    vague message.
    """
    assert microfs.clean_error(b"") == "There was an error."


def test_ls():
    """
    If a list is returned as a result in stdout, ensure that the equivalent
    Python list is returned from ls.
    """
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.execute", return_value=(b"[ 'a.txt']\r\n", b"")
    ) as execute:
        result = microfs.ls(mock_serial)
        assert result == ["a.txt"]
        execute.assert_called_once_with(
            [
                "import os",
                "print(os.listdir())",
            ],
            mock_serial,
            1
        )


def test_ls_width_delimiter():
    """
    If a delimiter is provided, ensure that the result from stdout is
    equivalent to the list returned by Python.
    """
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.execute", return_value=(b"[ 'a.txt','b.txt']\r\n", b"")
    ) as execute:
        result = microfs.ls(mock_serial)
        delimitedResult = ";".join(result)
        assert delimitedResult == "a.txt;b.txt"
        execute.assert_called_once_with(
            [
                "import os",
                "print(os.listdir())",
            ],
            mock_serial,
            1
        )


def test_ls_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", return_value=(b"", b"error")):
        with pytest.raises(IOError) as ex:
            microfs.ls(mock_serial)
    assert ex.value.args[0] == "error"


def test_rm():
    """
    Given a filename and nothing in stderr from the micro:bit, return True.
    """
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", return_value=(b"", b"")) as execute:
        assert microfs.rm("foo", mock_serial)
        execute.assert_called_once_with(
            [
                "import os",
                "os.remove('foo')",
            ],
            mock_serial,
            1
        )


def test_rm_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", return_value=(b"", b"error")):
        with pytest.raises(IOError) as ex:
            microfs.rm("foo", mock_serial)
    assert ex.value.args[0] == "error"


def test_put_python3():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True.
    """
    path = "tests/fixture_file.txt"
    target = "remote.txt"
    mock_serial = mock.MagicMock()
    with open(path, "r") as fixture_file:
        content = fixture_file.read()
        with mock.patch("microfs.execute", return_value=(b"", b"")) as execute:
            with mock.patch("microfs.PY2", False):
                with mock.patch.object(
                    builtins, "repr", return_value="b'{}'".format(content)
                ):
                    assert microfs.put(path, target, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format("remote.txt"),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial, 1)


def test_put_no_target_python3():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True.
    """
    path = "tests/fixture_file.txt"
    mock_serial = mock.MagicMock()
    with open(path, "r") as fixture_file:
        content = fixture_file.read()
        with mock.patch("microfs.execute", return_value=(b"", b"")) as execute:
            with mock.patch("microfs.PY2", False):
                with mock.patch.object(
                    builtins, "repr", return_value="b'{}'".format(content)
                ):
                    assert microfs.put(path, None, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format("fixture_file.txt"),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial, 1)


def test_put_python2():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True when running on Python 2.
    """
    path = "tests/fixture_file.txt"
    target = "remote.txt"
    mock_serial = mock.MagicMock()
    with open(path, "r") as fixture_file:
        content = fixture_file.read()
        with mock.patch("microfs.execute", return_value=(b"", b"")) as execute:
            with mock.patch("microfs.PY2", True):
                with mock.patch.object(
                    builtins, "repr", return_value="'{}'".format(content)
                ):
                    assert microfs.put(path, target, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format("remote.txt"),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial, 1)


def test_put_no_target_python2():
    """
    Ensure a put of an existing file results in the expected calls to the
    micro:bit and returns True when running on Python 2.
    """
    path = "tests/fixture_file.txt"
    mock_serial = mock.MagicMock()
    with open(path, "r") as fixture_file:
        content = fixture_file.read()
        with mock.patch("microfs.execute", return_value=(b"", b"")) as execute:
            with mock.patch("microfs.PY2", True):
                with mock.patch.object(
                    builtins, "repr", return_value="'{}'".format(content)
                ):
                    assert microfs.put(path, None, mock_serial)
            commands = [
                "fd = open('{}', 'wb')".format("fixture_file.txt"),
                "f = fd.write",
                "f(b'{}')".format(content),
                "fd.close()",
            ]
            execute.assert_called_once_with(commands, mock_serial, 1)


def test_put_non_existent_file():
    """
    Raise an IOError if put attempts to work with a non-existent file on the
    local file system.
    """
    mock_serial = mock.MagicMock()
    with pytest.raises(IOError) as ex:
        microfs.put("tests/foo.txt", mock_serial)
    assert ex.value.args[0] == "No such file."


def test_put_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", return_value=(b"", b"error")):
        with pytest.raises(IOError) as ex:
            microfs.put("tests/fixture_file.txt", mock_serial)
    assert ex.value.args[0] == "error"


def test_get():
    """
    Ensure a successful get results in the expected file getting written on
    the local file system with the expected content.
    """
    mock_serial = mock.MagicMock()
    commands = [
        "\n".join(
            [
                "try:",
                " from microbit import uart as u",
                "except ImportError:",
                " try:",
                "  from machine import UART",
                "  u = UART(0, {})".format(microfs.SERIAL_BAUD_RATE),
                " except Exception:",
                "  try:",
                "   from sys import stdout as u",
                "  except Exception:",
                "   raise Exception('Could not find UART module in device.')",
            ]
        ),
        "f = open('{}', 'rb')".format("hello.txt"),
        "r = f.read",
        "result = True",
        "\n".join(
            [
                "while result:",
                " result = r(32)",
                " if result:",
                "  u.write(repr(result))",
            ]
        ),
        "f.close()",
    ]
    with mock.patch("microfs.execute", return_value=(b"b'hello'", b"")) as exe:
        mo = mock.mock_open()
        with mock.patch("microfs.open", mo, create=True):
            assert microfs.get("hello.txt", "local.txt", mock_serial)
            exe.assert_called_once_with(commands, mock_serial, 1)
            mo.assert_called_once_with("local.txt", "wb")
            handle = mo()
            handle.write.assert_called_once_with(b"hello")


def test_get_no_target():
    """
    Ensure a successful get results in the expected file getting written on
    the local file system with the expected content. In this case, since no
    target is provided, use the name of the remote file.
    """
    commands = [
        "\n".join(
            [
                "try:",
                " from microbit import uart as u",
                "except ImportError:",
                " try:",
                "  from machine import UART",
                "  u = UART(0, {})".format(microfs.SERIAL_BAUD_RATE),
                " except Exception:",
                "  try:",
                "   from sys import stdout as u",
                "  except Exception:",
                "   raise Exception('Could not find UART module in device.')",
            ]
        ),
        "f = open('{}', 'rb')".format("hello.txt"),
        "r = f.read",
        "result = True",
        "\n".join(
            [
                "while result:",
                " result = r(32)",
                " if result:",
                "  u.write(repr(result))",
            ]
        ),
        "f.close()",
    ]
    with mock.patch("microfs.execute", return_value=(b"b'hello'", b"")) as exe:
        mo = mock.mock_open()
        with mock.patch("microfs.open", mo, create=True):
            assert microfs.get("hello.txt")
            exe.assert_called_once_with(commands, None, 1)
            mo.assert_called_once_with("hello.txt", "wb")
            handle = mo()
            handle.write.assert_called_once_with(b"hello")


def test_get_with_error():
    """
    Ensure an IOError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", return_value=(b"", b"error")):
        with pytest.raises(IOError) as ex:
            microfs.get("foo.txt", mock_serial)
    assert ex.value.args[0] == "error"


def test_version_good_output():
    """
    Ensure the version method returns the expected result when the response
    from the device is the expected bytes.
    """
    response = (
        b"(sysname='microbit', nodename='microbit', "
        b"release='1.0', "
        b"version=\"micro:bit v1.0-b'e10a5ff' on 2018-6-8; "
        b'MicroPython v1.9.2-34-gd64154c73 on 2017-09-01", '
        b"machine='micro:bit with nRF51822')\r\n"
    )
    mock_serial = mock.MagicMock()
    with mock.patch(
        "microfs.execute", return_value=(response, b"")
    ) as execute:
        result = microfs.version(mock_serial)
        assert result["sysname"] == "microbit"
        assert result["nodename"] == "microbit"
        assert result["release"] == "1.0"
        assert result["version"] == (
            "micro:bit v1.0-b'e10a5ff' on "
            "2018-6-8; "
            "MicroPython v1.9.2-34-gd64154c73 on "
            "2017-09-01"
        )
        assert result["machine"] == "micro:bit with nRF51822"
        execute.assert_called_once_with(
            [
                "import os",
                "print(os.uname())",
            ],
            mock_serial,
            1,
        )


def test_version_with_std_err_output():
    """
    Ensure a ValueError is raised if stderr returns something.
    """
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", return_value=(b"", b"error")):
        with pytest.raises(ValueError) as ex:
            microfs.version(mock_serial)
    assert ex.value.args[0] == "error"


def test_version_encountered_unknown_problem_when_executing_commands():
    """
    Ensure a ValueError is raised if some other error was encountered when
    trying to connect to the device and read the output of os.uname.
    """
    mock_serial = mock.MagicMock()
    with mock.patch("microfs.execute", side_effect=IOError("boom")):
        with pytest.raises(ValueError):
            microfs.version(mock_serial)


def test_main_no_args():
    """
    If no args are passed, simply display help.
    """
    with mock.patch(
        "sys.argv",
        [
            "ufs",
        ],
    ):
        mock_parser = mock.MagicMock()
        with mock.patch(
            "microfs.argparse.ArgumentParser", return_value=mock_parser
        ):
            microfs.main()
        mock_parser.print_help.assert_called_once_with()


def test_main_ls():
    """
    If the ls command is issued, check the appropriate function is called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch(
        "microfs.ls", return_value=["foo", "bar"]
    ) as mock_ls, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ), mock.patch.object(
        builtins, "print"
    ) as mock_print:
        microfs.main(argv=["ls"])
        mock_ls.assert_called_once_with(1)
        mock_print.assert_called_once_with("foo bar")


def test_main_ls_with_timeout():
    """
    If the ls command is issued, check the appropriate function is called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch(
        "microfs.ls", return_value=["foo", "bar"]
    ) as mock_ls, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ), mock.patch.object(
        builtins, "print"
    ) as mock_print:
        microfs.main(argv=["ls", "-t", "3"])
        mock_ls.assert_called_once_with(3)
        mock_print.assert_called_once_with("foo bar")


def test_main_ls_no_files():
    """
    If the ls command is issued and no files exist, nothing is printed.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.ls", return_value=[]) as mock_ls, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ), mock.patch.object(builtins, "print") as mock_print:
        microfs.main(argv=["ls"])
        mock_ls.assert_called_once_with(1)
        assert mock_print.call_count == 0


def test_main_rm():
    """
    If the rm command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.rm", return_value=True) as mock_rm, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ):
        microfs.main(argv=["rm", "foo"])
        mock_rm.assert_called_once_with("foo", 1)


def test_main_rm_with_timeout():
    """
    If the rm command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.rm", return_value=True) as mock_rm, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ):
        microfs.main(argv=["rm", "foo", "-t", "3"])
        mock_rm.assert_called_once_with("foo", 3)


def test_main_rm_no_filename():
    """
    If rm is not called with an associated filename, then print an error
    message.
    """
    with mock.patch("microfs.rm", return_value=True) as mock_rm:
        with mock.patch.object(builtins, "print") as mock_print, pytest.raises(
            SystemExit
        ) as pytest_exc:
            microfs.main(argv=["rm"])
    assert mock_print.call_count == 1
    assert mock_rm.call_count == 0
    assert pytest_exc.type == SystemExit
    assert pytest_exc.value.code == 2


def test_main_put():
    """
    If the put command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.put", return_value=True) as mock_put, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ):
        microfs.main(argv=["put", "foo"])
        mock_put.assert_called_once_with("foo", None, 1)


def test_main_put_with_timeout():
    """
    If the put command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.put", return_value=True) as mock_put, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ):
        microfs.main(argv=["put", "foo", "-t", "3"])
        mock_put.assert_called_once_with("foo", None, 3)


def test_main_put_no_filename():
    """
    If put is not called with an associated filename, then print an error
    message.
    """
    with mock.patch("microfs.put", return_value=True) as mock_put:
        with mock.patch.object(builtins, "print") as mock_print, pytest.raises(
            SystemExit
        ) as pytest_exc:
            microfs.main(argv=["put"])
    assert mock_print.call_count == 1
    assert mock_put.call_count == 0
    assert pytest_exc.type == SystemExit
    assert pytest_exc.value.code == 2


def test_main_get():
    """
    If the get command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.get", return_value=True) as mock_get, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ):
        microfs.main(argv=["get", "foo"])
        mock_get.assert_called_once_with("foo", None, 1)


def test_main_get_with_timeout():
    """
    If the get command is correctly issued, check the appropriate function is
    called.
    """
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.get", return_value=True) as mock_get, mock.patch(
        "microfs.get_serial", return_value=mock_class
    ):
        microfs.main(argv=["get", "foo", "-t", "3"])
        mock_get.assert_called_once_with("foo", None, 3)


def test_main_get_no_filename():
    """
    If get is not called with an associated filename, then print an error
    message.
    """
    with mock.patch("microfs.get", return_value=True) as mock_get:
        with mock.patch.object(builtins, "print") as mock_print, pytest.raises(
            SystemExit
        ) as pytest_exc:
            microfs.main(argv=["get"])
    assert mock_print.call_count == 1
    assert mock_get.call_count == 0
    assert pytest_exc.type == SystemExit
    assert pytest_exc.value.code == 2


def test_main_handle_exception():
    """
    If an exception is raised, then it gets printed.
    """
    ex = ValueError("Error")
    mock_serial = mock.MagicMock()
    mock_class = mock.MagicMock()
    mock_class.__enter__.return_value = mock_serial
    with mock.patch("microfs.get", side_effect=ex), mock.patch(
        "microfs.get_serial", return_value=mock_class
    ), mock.patch.object(builtins, "print") as mock_print, pytest.raises(
        SystemExit
    ) as pytest_exc:
        microfs.main(argv=["get", "foo"])
    mock_print.assert_called_once_with(ex)
    assert pytest_exc.type == SystemExit
    assert pytest_exc.value.code == 1
