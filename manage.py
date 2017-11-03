#!/usr/bin/env python

from pillar import cli
from runserver import app

cli.manager.app = app
cli.manager.run()
