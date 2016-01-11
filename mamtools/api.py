"""
The mamtools api is just a bunch of functions that will decide what
operation to use depending on certain variables.

For instance, the detach function in mesh will only work on meshes but
if you use the detach from api it will work on uvs aswell.
"""
import logging

from maya import cmds
import maya.api.OpenMaya as api

import mampy

from mamtools.uv import tear_off
from mamtools.mesh import detach_mesh

logger = logging.getLogger(__name__)


def detach(hierarchy=False, extract=False):
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing Selected.')

    focused_panel = cmds.getPanel(wf=True)
    if focused_panel.startswith('polyTexturePlacementPanel'):
        tear_off()
    elif focused_panel.startswith('modelPanel'):
        s = s[0]
        if s.type == api.MFn.kMeshPolygonComponent:
            detach_mesh(extract)
        elif s.type in [api.MFn.kTransform]:
            cmds.duplicate(rr=True)  # parentOnly=hierarchy)


if __name__ == '__main__':
    detach()
