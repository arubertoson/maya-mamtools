"""
Helper functions to give more control over selection masks.
"""
import logging
from collections import namedtuple

from maya import cmds

import mampy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MaskPreset = namedtuple('MaskPreset', 'masks')

# Personal mask presets can be created with named tuples
VERT = MaskPreset(('vertex', 'controlVertex', 'latticePoint'))
EDGE = MaskPreset(('edge', 'surfaceEdge'))
FACE = MaskPreset(('facet', 'surfaceFace'))
MAP = MaskPreset(('polymeshUV', 'surfaceUV'))


def exit_tool_and_mask():
    """Exit current tool or toggle selection mode.

    When working with other contexts in maya use this function to exit the current
    context and return to selection context; if you are using base tools ('select',
    move, rotate, scale) toggle selection mode instead.

    Usage:

        tool_select()

    """
    base_tools = ['{}SuperContext'.format(i) for i in ('select', 'move', 'rotate', 'scale')]
    if cmds.currentCtx() not in base_tools:
        cmds.setToolTo('selectSuperContext')
    else:
        if cmds.selectMode(q=True, object=True):
            hilited = mampy.ls(hl=True)
            if hilited:
                cmds.hilite(list(hilited), toggle=True)
                cmds.select(list(hilited))
            else:
                cmds.selectMode(component=True)
        else:
            cmds.selectMode(object=True)


def set_mask(*masks):
    """Set selection masks in maya.

    if the current mask is the given mask toggle object component mode. This is the
    default mode maya uses when switching selection masks. You will be able to continue
    selecting components but also select other objects as maya objects.

    Usage:

        set_mask('vertex', 'controlVertex', 'latticePoint')
        set_mask('meshComponents')

    """
    print masks
    component_masks = {mask: True for mask in masks}
    if (cmds.selectMode(q=True, component=True) and
            any(cmds.selectType(q=True, **{mask: True}) for mask in component_masks.iterkeys())):
        cmds.selectMode(object=True)
        cmds.selectType(ocm=True, alc=False)
        cmds.selectType(ocm=True, **component_masks)
        cmds.selectType(**component_masks)
        cmds.hilite(list(mampy.selected()))
    else:
        cmds.selectMode(component=True)
        cmds.selectType(allComponents=False)
        cmds.selectType(**component_masks)


def vert_mask(*point_masks):
    """Helper function for setting point mask in viewport."""
    set_mask(*point_masks + VERT.masks)


def edge_mask(*edge_masks):
    """Helper function for setting edge mask in viewport."""
    set_mask(*edge_masks + EDGE.masks)


def face_mask(*face_masks):
    """Helper function for setting face mask in viewport."""
    set_mask(*face_masks + FACE.masks)


def map_mask(*map_masks):
    """Helper function for setting map (uv points) mask in viewport."""
    set_mask(*map_masks + MAP.masks)


def multi_component_mask():
    """Helper function for setting multi compontent mask in viewport."""
    set_mask('meshComponents')


if __name__ == '__main__':
    pass
