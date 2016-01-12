import logging
import collections
from functools import partial

import maya.cmds as cmds
import maya.api.OpenMaya as api

import mampy
import mamtools

logger = logging.getLogger(__name__)


__all__ = ['delete', 'history', 'collapse', 'merge_faces', 'merge_verts',
           'transforms']


@mampy.history_chunk()
def delete(cv=False):
    """Custom delete using 'right' delete function depending on selection."""
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing to delete.')

    for comp in s.itercomps():
        if not comp:
            cmds.delete(str(comp.dagpath))

        elif comp.is_face():
            cmds.polyDelFacet(list(comp), ch=False)
        elif comp.is_edge():
            cmds.polyDelEdge(list(comp), ch=False, cv=cv)
        elif comp.is_vert():
            cmds.polyDelVertex(list(comp), ch=False)
        else:
            cmds.delete(str(comp), ch=False)


def history():
    """Delete history on selected objects, works on hilited objects."""
    s = mampy.selected()
    h = mampy.ls(hl=True, dag=True)
    if h: s.extend(h)

    cmds.delete(list(s), ch=True)


@mampy.history_chunk()
def collapse():
    s = mampy.selected()
    if not s or next(s.itercomps(), None) is None:
        return logger.warn('Invalid component selection.')

    cmds.select(cl=True)
    for comp in s.itercomps():
        vert = comp.to_vert()
        cmds.xform(list(vert), ws=True, t=list(vert.bounding_box.center)[:3])
        cmds.polyMergeVertex(list(comp), distance=0.001)


@mampy.history_chunk()
def merge_faces():
    """Removes edges inside of face selection."""
    s = mampy.selected()
    if (not s or not isinstance(next(s.itercomps()), mampy.MeshPolygon) or
            not len(s[0]) > 1):
        return logger.warn('Invalid Selection, must have 2 or more polygons'
                           'selected.')

    faces = mampy.SelectionList()
    for comp in s.itercomps():
        border_verts = comp.to_vert(border=True)
        internal_edges = comp.to_edge(internal=True)
        cmds.polyDelEdge(list(internal_edges), cv=False, ch=False)

        # Find new face
        face = collections.Counter()
        for vert in cmds.ls(list(border_verts), fl=True):
            f = cmds.polyListComponentConversion(vert, tf=True)
            face.update(cmds.ls(f, fl=True))
        faces.append(face.most_common(1).pop()[0])

    cmds.select(list(faces))


@mampy.history_chunk()
def merge_verts(move):
    """
    Merges verts to first selection.
    """
    if move:
        s = mampy.ordered_selection(fl=True)
        pos = s[0].points[0]

        cmds.xform(list(s), ws=True, t=list(pos)[:3])
    else:
        s = mampy.selected()
    cmds.polyMergeVertex(list(s), distance=0.001, ch=True)


def transforms(translate=False, rotate=False, scale=False):
    """Small function to control transform freezes."""
    s, h = mampy.selected(tr=True, l=True), mampy.ls(hl=True, dag=True)
    if h:
        s = h

    transforms = [str(dp) for dp in s.iterdags() if dp.type == api.MFn.kTransform]
    cmds.makeIdentity(transforms, t=translate, r=rotate, s=scale, apply=True)


if __name__ == '__main__':
    merge_faces()

