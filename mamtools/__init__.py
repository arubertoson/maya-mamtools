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
__version__ = "0.4.4"
__license__ = "MIT"


import traceback
import maya
from maya import cmds
import mampy
from mamtools import camera, delete, display, mesh, sort_outliner

optionVar = mampy.optionVar()


def mel(command):
    try:
        if all([
            maya.mel.eval('exists {}'.format(cmd.lstrip().split(' ')[0]))
            for cmd in command.split(';')
        ]):
            maya.mel.eval('{};'.format(command))
        else:
            for cmd in [i for i in command.split(';') if i]:
                maya.mel.eval('dR_DoCmd("{}");'.format(cmd.lstrip()))
    except (RuntimeError, SyntaxError):
        traceback.print_exc()
        print('failed to execute: {}'.format(command))


def translate_map(angle):
    sel = mampy.selected().itercomps().next().to_map()
    cen = sel.bounding_box.center
    sel.translate(r=True, pu=cen.u, pv=cen.v, angle=angle)


def lasso():
    tool = 'MAM_LASSO'
    if cmds.lassoContext(tool, q=True, exists=True):
        cmds.setToolTo(tool)
    else:
        cmds.lassoContext(tool)


def dragger_press(tool):
    optionVar['MAM_CURRENT_CTX'] = cmds.currentCtx()
    {
        'lasso': lasso,
    }[tool]()


def dragger_release():
    cmds.setToolTo(optionVar['MAM_CURRENT_CTX'])
    cmds.refresh(f=True)
