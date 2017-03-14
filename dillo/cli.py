"""Commandline interface for Pistacchio."""

import logging

from flask import current_app
from flask_script import Manager

from pillar.cli import manager

log = logging.getLogger(__name__)

manager_dillo = Manager(current_app, usage="Perform Dillo operations")

manager.add_command("dillo", manager_dillo)
