from os.path import abspath, dirname
import sys

my_path = dirname(abspath(__file__))
sys.path.append(my_path)

from pillar import PillarServer
from dillo import DilloExtension

dillo = DilloExtension()

application = PillarServer(my_path)
application.load_extension(dillo, None)
application.process_extensions()

if __name__ == '__main__':
    application.run(debug=False)
