"""
"""
import logging
import collections
from functools import partial

import maya.cmds as cmds
from maya.api.OpenMaya import MFn

import mampy
from mampy.core.datatypes import Line3D
from mampy.utils import undoable, repeatable
from mampy.core.exceptions import NothingSelected, InvalidSelection
from mampy.core.components import (SingleIndexComponent, MeshVert,
                                   get_outer_and_inner_edges_from_edge_loop)
from mampy.core.selectionlist import ComponentList


logger = logging.getLogger(__name__)


__all__ = ['delete', 'history', 'collapse', 'merge_faces', 'merge_verts',
           'transforms', 'unbevel']


@undoable()
@repeatable
def delete(cv=False):
    """Custom delete using 'right' delete function depending on selection."""
    selected = mampy.complist() or mampy.daglist()
    if not selected:
        return logger.warn('Nothing to delete.')

    for each in selected:
        if isinstance(each, SingleIndexComponent):
            # Try to delete supported types if that fails uss default delete in
            # maya
            try:
                {
                    MFn.kMeshEdgeComponent: partial(cmds.polyDelEdge, each.cmdslist(), cv=cv),
                    MFn.kMeshVertComponent: partial(cmds.polyDelVertex, each.cmdslist()),
                    MFn.kMeshPolygonComponent: partial(cmds.polyDelFacet, each.cmdslist()),
                }[each.type]()
            except KeyError:
                cmds.delete(each.cmdslist())
        else:
            cmds.delete(str(each))
    cmds.select(cl=True)


@repeatable
def history():
    """Delete history on selected objects, works on hilited objects."""
    with undoable():
        for each in mampy.daglist():
            cmds.delete(str(each.transform), ch=True)


@undoable()
@repeatable
def collapse():
    selected = mampy.complist()
    if not selected:
        return logger.warn('Invalid component selection.')

    for comp in selected:
        if comp.type == MFn.kMeshEdgeComponent:
            for comp in comp.get_connected_components():
                for edge in comp.indices:
                    vert = MeshVert.create(comp.dagpath).add(comp.vertices[edge])
                    vert.translate(t=list(comp.bbox.center)[:3], ws=True)
        else:
            vert = comp.to_vert()
            vert.translate(t=list(vert.bbox.center)[:3], ws=True)
        cmds.polyMergeVertex(comp.cmdslist(), distance=0.001)
    cmds.select(cl=True)


@undoable()
@repeatable
def merge_faces():
    """Removes edges inside of face selection."""
    selected = mampy.complist()
    if not selected:
        raise NothingSelected()

    control_object = next(iter(selected))
    if not control_object.type == MFn.kMeshPolygonComponent or not len(control_object) > 1:
        raise InvalidSelection('Must have at least two connected faces selected.')

    new_faces = ComponentList()
    for face in selected:
        # We must first collect all necessary elements before we operate on them.
        # This is to avoid getting uncertain information due to indices changing
        # when performing the delete function.
        border_vertices = ComponentList()
        internal_edges = ComponentList()
        for connected_face in face.get_connected_components():
            border_vertices.append(connected_face.to_vert(border=True))
            internal_edges.append(connected_face.to_edge(internal=True))

        # We only delete once per object to perserve as much information as
        # possible.
        cmds.polyDelEdge(internal_edges.cmdslist())
        # Collect the most shared face on the border vertices to get new faces
        # from the delete operation.
        for border_vert in border_vertices:
            counter = collections.Counter()
            for idx in border_vert.indices:
                f = border_vert.new().add(idx).to_face()
                counter.update(f.indices)
            new_faces.append(face.new().add(counter.most_common(1).pop()[0]))
    # Select and be happy!
    cmds.select(new_faces.cmdslist())


@undoable()
@repeatable
def merge_verts(move):
    """Merges verts to first selection."""
    ordered_selection = mampy.complist(os=True)
    if move or len(ordered_selection) == 2:
        if not move:
            v1, v2 = ordered_selection
            pos = v1.bbox.expand(v2.bbox).center
        else:
            pos = ordered_selection.pop().bbox.center
        cmds.xform(ordered_selection.cmdslist(), t=list(pos)[:3], ws=True)
        cmds.polyMergeVertex(ordered_selection.cmdslist(), distance=0.001, ch=True)


@undoable()
@repeatable
def transforms(translate=False, rotate=False, scale=False):
    """Small function to control transform freezes."""
    transforms = [str(dp.transform) for dp in mampy.daglist()]
    cmds.makeIdentity(transforms, t=translate, r=rotate, s=scale, apply=True)


@undoable()
@repeatable
def unbevel():
    """
    Unbevel beveled edges.

    Select Edges along a bevel you want to unbevel. Make sure the edge is not
    connected to another edge from another bevel. This will cause the script
    to get confused.
    """
    selected = mampy.complist()
    for edge in selected:

        # cmds.select(edge.cmdslist(), r=True)
        merge_list = ComponentList()
        for each in edge.get_connected_components():
            outer_edges, inner_verts = get_outer_and_inner_edges_from_edge_loop(each)

            edge1, edge2 = outer_edges
            line1 = Line3D(edge1[0].bbox.center, edge1[1].bbox.center)
            line2 = Line3D(edge2[0].bbox.center, edge2[1].bbox.center)
            intersection = line1.shortest_line_to_other(line2)
            inner_verts.translate(t=intersection.sum() * 0.5, ws=True)
            merge_list.append(inner_verts)

        # Merge components on object after all operation are done. Mergin
        # before will change vert ids and make people sad.
        cmds.polyMergeVertex(merge_list.cmdslist(), distance=0.001)


if __name__ == '__main__':
    pass
