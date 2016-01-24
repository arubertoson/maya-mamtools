"""
The mamtools api is just a bunch of functions that will decide what
operation to use depending on certain variables.

For instance, the detach function in mesh will only work on meshes but
if you use the detach from api it will work on uvs aswell.
"""
import logging
from functools import partial

from maya import cmds, mel
import maya.api.OpenMaya as api

import mampy

from mamtools import mesh, delete, uv, contexts

logger = logging.getLogger(__name__)


__all__ = ['merge', 'detach']


def bevel():
    """
    Bevel is a collection of functions usually performed when certain states
    are fulfilled, such as: selection, border edge etc.
    """
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing Selected.')

    for comp in s.itercomps():
        cmds.select(list(comp))

        if comp.type == api.MFn.kMeshEdgeComponent:
            if comp.is_border(comp.index):
                contexts.extrude()
            else:
                contexts.bevel()
        elif comp.type == api.MFn.kMeshPolygonComponent:
            contexts.extrude()
        elif comp.type == api.MFn.kMeshVertComponent:
            contexts.extrude()


def merge():
    """
    Dispatches function call depending on selection type
    """
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing Selected.')

    obj = s[0]
    t = obj.type
    if obj.type in [api.MFn.kTransform]:
        t = obj.get_shape().type

    try:
        {
            api.MFn.kMeshVertComponent: partial(delete.merge_verts, True),
            api.MFn.kMeshPolygonComponent: delete.merge_faces,
            api.MFn.kMesh: mesh.combine_separate,
        }[t]()
    except KeyError:
        logger.warn('{} is not a valid type'.format(t))


def detach(extract=False):
    """
    Dispatches function call depening on selection type or type of panel
    under cursor.
    """
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing Selected.')

    focused_panel = cmds.getPanel(wf=True)
    if focused_panel.startswith('polyTexturePlacementPanel'):
        uv.tear_off()
    elif focused_panel.startswith('modelPanel'):
        s = s[0]
        if s.type == api.MFn.kMeshPolygonComponent:
            mesh.detach_mesh(extract)
        elif s.type in [api.MFn.kTransform]:
            cmds.duplicate(rr=True)  # parentOnly=hierarchy)


if __name__ == '__main__':
    merge()
