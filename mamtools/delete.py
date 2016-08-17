import logging
import collections

import maya.cmds as cmds
import maya.api.OpenMaya as api

import mampy
from mampy._old.datatypes import Line3D
from mampy._old.containers import SelectionList
from mampy._old.utils import undoable, repeatable
from mampy._old.comps import MeshPolygon
from mampy._old.computils import get_outer_edges_in_loop

logger = logging.getLogger(__name__)


__all__ = ['delete', 'history', 'collapse', 'merge_faces', 'merge_verts',
           'transforms']


@undoable
@repeatable
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
    cmds.select(cl=True)


@repeatable
def history():
    """Delete history on selected objects, works on hilited objects."""
    s = mampy.selected()
    h = mampy.ls(hl=True, dag=True)
    if h:
        s.extend(h)

    cmds.delete(list(s), ch=True)


@undoable
@repeatable
def collapse():
    s = mampy.selected()
    if not s or next(s.itercomps(), None) is None:
        return logger.warn('Invalid component selection.')

    cmds.select(cl=True)
    for comp in s.itercomps():
        vert = comp.to_vert()
        cmds.xform(list(vert), ws=True, t=list(vert.bounding_box.center)[:3])
        cmds.polyMergeVertex(list(comp), distance=0.001)


@undoable
@repeatable
def merge_faces():
    """Removes edges inside of face selection."""
    s = mampy.selected()
    if (not s or not isinstance(next(s.itercomps()), MeshPolygon) or
            not len(s[0]) > 1):
        return logger.warn('Invalid Selection, must have 2 or more polygons'
                           'selected.')

    faces = SelectionList()
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


@undoable
@repeatable
def merge_verts(move):
    """Merges verts to first selection."""
    s = mampy.ordered_selection(fl=True)
    if move or len(s) == 2:
        if not move:
            v1, v2 = s.itercomps()
            pos = (v1.points.pop() + api.MVector(v2.points.pop())) / len(s)
        else:
            pos = s[0].points[0]
        cmds.xform(list(s), ws=True, t=list(pos)[:3])
    cmds.polyMergeVertex(list(s), distance=0.001, ch=True)


@undoable
@repeatable
def transforms(translate=False, rotate=False, scale=False):
    """Small function to control transform freezes."""
    s, h = mampy.ls(tr=True, l=True), mampy.ls(hl=True, dag=True)
    if h:
        s = h

    transforms = [str(dp) for dp in s.iterdags() if dp.type == api.MFn.kTransform]
    cmds.makeIdentity(transforms, t=translate, r=rotate, s=scale, apply=True)


@undoable
@repeatable
def unbevel():
    """
    Unbevel beveled edges.

    Select Edges along a bevel you want to unbevel. Make sure the edge is not
    connected to another edge from another bevel. This will cause the script
    to get confused.
    """
    s = mampy.selected()
    for comp in s.itercomps():

        cmds.select(list(comp), r=True)
        merge_list = SelectionList()

        for c in comp.get_connected():
            outer_edges, rest = get_outer_edges_in_loop(c)

            edge1, edge2 = list(outer_edges.itercomps())
            line1 = Line3D(edge1[0].points[0], edge1[1].points[0])
            line2 = Line3D(edge2[0].points[0], edge2[1].points[0])
            intersection_line = line1.shortest_line_to_other(line2)

            rest.translate(t=intersection_line.sum() * 0.5, ws=True)
            merge_list.append(rest)

        # Merge components on object after all operation are done. Mergin
        # before will change vert ids and make the script break
        cmds.polyMergeVertex(list(merge_list), distance=0.001, ch=False)

    # Restore selection
    cmds.selectMode(component=True)
    cmds.hilite([str(i) for i in s.iterdags()], r=True)
    cmds.select(cl=True)


if __name__ == '__main__':
    unbevel()
