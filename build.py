import subprocess
from pybuilder.core import Author, init, use_plugin, task, before, after

use_plugin("filter_resources")
use_plugin("python.core")
use_plugin("python.install_dependencies")
use_plugin("python.distutils")
use_plugin("python.pycharm")

name = "fuct"
url = "https://github.com/MrOnion/fuct"
description = "Visit {0} for more information.".format(url)

authors = [Author("Ari Karhu", "ari@baboonplanet.com")]
license = "Apache License, Version 2.0"
summary = "Unified commandline loader and logger for FreeEMS."

default_task = ["install_dependencies", "publish"]


@init
def set_properties(project, logger):
    project.get_property("filter_resources_glob").append("**/fuct/__init__.py")
    project.depends_on("pyserial", ">=2.7")
    project.depends_on("colorlog[windows]", ">=2.0.0")
    logger.info("Executing git describe")
    project.version = subprocess.check_output(
        ["git", "describe", "--tags", "--always"]).rstrip("\n")
    project.set_property("git", subprocess.check_output(
        ["git", "describe", "--tags", "--always", "--long", "--dirty"]).rstrip("\n"))
    project.set_property("dir_dist", "$dir_target/dist/{0}-{1}".format(project.name, project.version))