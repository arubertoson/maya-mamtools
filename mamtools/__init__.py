"""
Mamtools Maya scripts.

mamtools is a toolbox created for Autodesk Maya. Supports custom
extensions and contains various improvements to basic tools in
maya.

:copyright: (c) 2016 by Marcus Albertsson
:license: MIT, see LICENSE for details
"""

__author__ = "Marcus Albertsson <marcus.arubertoson@gmail.com>"
__copyright__ = 'Copyright 2016 Marcus Albertsson'
__url__ = "http://github.com/arubertoson/mamtools"
__version__ = "0.4.1"
__license__ = "MIT"


from mamtools import camera, delete, display, mesh


def mel(command):
    print(command)
    from maya import mel
    mel.eval("{}".format(command))
