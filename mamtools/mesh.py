import logging

import maya.cmds as cmds
from maya.api.OpenMaya import MFn

import mampy

logger = logging.getLogger(__name__)


@mampy.history_chunk()
def extrude():
    s = mampy.selected()
    for comp in s.itercomps():
        cmds.select(list(comp))
        try:
            func = {
                MFn.kMeshPolygonComponent: cmds.polyExtrudeFacet,
                MFn.kMeshEdgeComponent: cmds.polyExtrudeEdge,
                MFn.kMeshVertComponent: cmds.polyExtrudeVertex,
            }[comp.type]
            func(divisions=1)
        except KeyError:
            return logger.warn('{} is not support for extrude'.format(comp.type))
        finally:
            cmds.select(list(s))
    cmds.select(list(s))


def bridge():
    pass


def bevel():
    pass


@mampy.history_chunk()
def detach(extract=False):
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing selected.')

    new = mampy.SelectionList()
    for comp in s.itercomps():
        if not comp.is_face():
            continue

        # Duplicate
        trans = mampy.DagNode.from_object(comp.dagpath.transform())
        name = trans.name + ('_ext' if extract else '_dup')
        dupdag = cmds.duplicate(str(comp.dagpath), n=name).pop(0)

        # Delete children transforms
        children = cmds.listRelatives(dupdag, type='transform', f=True)
        if children is not None:
            cmds.delete(children)

        # Delete unused faces
        if extract:
            cmds.polyDelFacet(list(comp))

        dcomp = mampy.MeshPolygon.create(dupdag)
        dcomp.add(comp.indices)
        cmds.polyDelFacet(list(dcomp.toggle()))

        # Select
        cmds.hilite(str(dcomp.dagpath))
        new.append(dcomp.get_complete())

    cmds.select(list(new), r=True)


if __name__ == '__main__':
    detach()
