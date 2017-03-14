#!/usr/bin/env python

from pillar import PillarServer
from dillo import DilloExtension

dillo = DilloExtension()

app = PillarServer('.')
app.load_extension(dillo, None)
app.process_extensions()

if __name__ == '__main__':
    app.run('::0', 5000, debug=True)
