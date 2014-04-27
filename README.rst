===================================
FUCT - FreeEMS Unified Console Tool
===================================

``fuct`` is a command line tool used to operate FreeEMS firmware files.

Install
-------

.. code-block:: bash

    $ python setup.py install

Dependencies
------------

* pyserial >=2.7
* colorlog >=2.0.0

Features
--------

* Check device for correct MCU and serial monitor
* Validate S19 firmware file
* Load S19 firmware file with or without verification
* Rip S19 firmware from device
* Erase device

Examples
--------

To check if your device is compatible with the FreeEMS firmware run the ``device`` command with serial port ``-s`` option:

.. code-block:: bash

    $ fuct -s /dev/tty.usbserial device

It will first check if the device ID is supported. Other commands that communicate with the device will perform
this same task before going further.

If the device is supported the serial monitor is ripped from the device and compared to a support list. If the serial
monitor is supported the name and version will be printed. If the serial monitor is unknown you can use debugging
``-d`` option to get more information.

To validate firmware files without having the device connected you can use the ``check`` command:

.. code-block:: bash

    $ fuct check MyFirmware.S19

This will parse all the S-records and print information.

To load the firmware into the device run the ``load`` or ``fastload`` command with serial port ``-s`` option:

.. code-block:: bash

    $ fuct -s /dev/tty.usbserial load MyFirmware.S19

The ``load`` will verify every memory page that is written to the device. With ``fastload`` the verification is skipped
 and therefore is faster.

To rip the present firmware from the device run the ``rip`` command with serial port ``-s`` option:

.. code-block:: bash

    $ fuct -s /dev/tty.usbserial rip MyRippedFirmware.s19

The memory pages from the device are ripped and stored into the specified file in S-record format.

To erase the memory pages in the device use the ``erase`` command with serial port ``-s`` option:

.. code-block:: bash

    $ fuct -s /dev/tty.usbserial erase

The memory range used by the firmware is cleaned page by page. The serial monitor itself will remain in the device and
is not erased.

