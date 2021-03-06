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
from mamtools import camera, delete, display, mesh, sort_outliner, pivots

import maya.OpenMaya as OpenMaya

optionVar = mampy.optionVar()


lasso_callback = None


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
    global lasso_callback
    lasso_callback = OpenMaya.MEventMessage.addEventCallback("SelectionChanged", lasso_release)
    tool = 'MAM_LASSO'
    if not cmds.lassoContext(tool, q=True, exists=True):
        cmds.lassoContext(tool)
    cmds.setToolTo(tool)


def lasso_release(*args):
    try:
        OpenMaya.MEventMessage.removeCallback(lasso_callback)
    except RuntimeError:
        pass
    cmds.setToolTo('selectSuperContext')


def dolly():
    tool = 'MAM_DOLLY'
    if not cmds.dollyCtx(tool, q=True, exists=True):
        cmds.dollyCtx(tool, ac=True, ld=True, cd=False, dtc=True)
    cmds.setToolTo(tool)


def dolly_release(*args):
    # import maya.mel as mel
    # mel.eval('SelectToolOptionsMarkingMenu')
    cmds.setToolTo('selectSuperContext')


def track():
    tool = 'MAM_TRACK'
    if not cmds.trackCtx(tool, q=True, exists=True):
        cmds.trackCtx(tool)
    cmds.setToolTo(tool)


def track_release():
    print('yeaaah')
    # cmds.setToolTo('selectSuperContext')
    # mel('dR_updateToolSettings')


def dragger_press(tool):
    optionVar['MAM_CURRENT_CTX'] = cmds.currentCtx()
    {
        'lasso': lasso,
        'dolly': dolly,
        'track': track,
    }[tool]()


def dragger_release():
    # OpenMaya.MEventMessage.removeCallback(optionVar['MAM_CALLBACK'])
    cmds.setToolTo(optionVar['MAM_CURRENT_CTX'])


if __name__ == '__main__':
    pass

