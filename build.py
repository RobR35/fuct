from pybuilder.core import Author, init, use_plugin

use_plugin("python.core")
use_plugin('python.install_dependencies')
use_plugin("python.distutils")
use_plugin("python.pycharm")

name = 'fuct'
url = 'https://github.com/MrOnion/fuct'
description = 'Please visit {0} for more information!'.format(url)

authors = [Author('Ari Karhu', 'ari@baboonplanet.com')]
license = 'Apache License, Version 2.0'
summary = 'Unified commandline loader and logger for FreeEMS.'
version = '0.9.0-SNAPSHOT'

default_task = ['install_dependencies', 'publish']

@init
def set_properties(project):
  project.depends_on("pyserial", ">=2.7")
  project.depends_on("colorlog", ">=2.0.0")

