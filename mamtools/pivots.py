import math
import logging
from maya.api import OpenMaya as api

from maya import cmds

import mampy
from mampy.utils import undoable

logger = logging.getLogger(__name__)


def set_pivot_center():
    cmds.xform(cp=True)


def set_pivot(vector=(0, 0, 0)):
    vec = api.MVector(vector)
    for each in mampy.ls(sl=True, tr=True, l=True).iterdags():
        try:
            each.get_transform().set_pivot(vec)
        except RuntimeError():
            raise mampy.InvalidSelection('{} is not valid for function.'
                                         .format(each.typestr))


@undoable
def match_pivot_to_object():
    """
    Match secondary selection pivots to first object selected.
    """
    s, hl = mampy.ordered_selection(tr=True, l=True), mampy.ls(hl=True)
    if len(s) == 0:
        if len(hl) > 0:
            s = hl
        else:
            return logger.warn('Nothing Selected.')

    # check driver information
    dag = s.pop(0)
    trns = dag.get_transform()
    piv = trns.get_scale_pivot()

    # set pivot for driven objects
    for each in s.iterdags():
        print each, type(each)
        trns = each.get_transform().set_pivot(piv)


@undoable
def bake_pivot():
    """
    Bake modified manipulator pivot onto object.
    """
    s = mampy.ordered_selection(tr=True, l=True)
    dag = s.pop(len(s) - 1)
    out_idx = mampy.get_outliner_index(dag)
    parent = dag.get_parent()

    # Get manipulator information
    pos = cmds.manipMoveContext('Move', q=True, p=True)
    rot = cmds.manipMoveContext('Move', q=True, oa=True)
    rot = tuple(math.degrees(i) for i in rot)

    # Create dummpy parent
    space_locator = cmds.spaceLocator(name='bake_dummy_loc', p=pos)[0]
    cmds.xform(space_locator, cp=True)
    cmds.xform(space_locator, rotation=rot, ws=True)

    dag.set_parent(space_locator)
    cmds.makeIdentity(dag.name, rotate=True, translate=True, apply=True)

    dag.set_parent(parent)
    cmds.delete(space_locator)
    cmds.reorder(dag.name, f=True); cmds.reorder(dag.name, r=out_idx)
    cmds.select(list(s), r=True); cmds.select(dag.name, add=True)


def get_pane_size(pane):
    """
    Return pane size of given pane.
    """
    return [cmds.control(pane, q=True, **{p: True}) for p in ['w', 'h']]

if __name__ == '__main__':
    pass
    # select_mode_toggle()
    # print get_pane_size(cmds.getPanel(underPointer=True))


# def uvShellHardEdges():
#     '''
#     Sets uv border edges on a mesh has hard, and everythign else as soft.
#     '''
#     objList = cmds.ls(sl=True, o=True)
#     finalBorder = []

#     for subObj in objList:
#         cmds.select(subObj, r=True)
#         cmds.polyNormalPerVertex(ufn=True)
#         cmds.polySoftEdge(subObj, a=180, ch=1)
#         cmds.select(subObj + '.map[*]', r=True)

#         polySelectBorderShell(borderOnly=True)

#         uvBorder = cmds.polyListComponentConversion(te=True, internal=True)
#         uvBorder = cmds.ls(uvBorder, fl=True)

#         for curEdge in uvBorder:
#             edgeUVs = cmds.polyListComponentConversion(curEdge, tuv=True)
#             edgeUVs = cmds.ls(edgeUVs, fl=True)

#             if len(edgeUVs) > 2:
#                 finalBorder.append(curEdge)

#         cmds.polySoftEdge(finalBorder, a=0, ch=1)

#     cmds.select(objList)
