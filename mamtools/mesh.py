import sys
import logging
import collections

import maya.cmds as cmds
import maya.api.OpenMaya as api

import mampy

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


EPS = sys.float_info.epsilon


@mampy.history_chunk()
def bevel():
    s = mampy.selected()
    for comp in s.itercomps():
        cmds.select(list(comp))
        try:
            func = {
                api.MFn.kMeshPolygonComponent: cmds.polyExtrudeFacet,
                api.MFn.kMeshEdgeComponent: cmds.polyExtrudeEdge,
                api.MFn.kMeshVertComponent: cmds.polyExtrudeVertex,
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
def detach_mesh(extract=False):
    """
    Extracts or duplicat selected polygon faces.
    """
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


@mampy.history_chunk()
def combine_separate():
    """
    Depending on selection will combine or separate objects.

    Script will try to retain the transforms and outline position of the
    first object selected.

    """
    def clean_up_object(dag):
        """
        Cleans up after `polyUnite` / `polySeparate`
        """
        if dag.get_parent() is not None:
            dag.set_parent(parent)
        trns = dag.get_transform()

        cmds.reorder(dag.name, f=True)
        cmds.reorder(dag.name, r=outliner_index)
        trns.set_pivot(pivot)

        dag.rotate.set(*src_trns.rotate)
        dag.scale.set(*src_trns.scale)
        return dag.name

    s, hl = mampy.ordered_selection(tr=True, l=True), mampy.ls(hl=True)
    if len(s) == 0:
        if len(hl) > 0:
            s = hl
        else:
            return logger.warn('Nothing Selected.')

    dag = s.pop()
    logger.debug(dag)
    parent = dag.get_parent()

    # Get origin information from source object
    trns = dag.get_transform()
    src_trns = trns.get_transforms()
    pivot = trns.get_rotate_pivot()

    if s:
        logger.debug('Combining Objects.')
        for i in s.iterdags():
            if dag.is_child_of(i):
                raise mampy.InvalidSelection('Cannot parent an object to one '
                                             'of its children')
            if dag.is_parent_of(i):
                continue
            i.set_parent(dag)

    # Now we can check source objects position in outliner and
    # un-rotate/un-scale
    outliner_index = mampy.get_outliner_index(dag)
    dag.rotate.set(0, 0, 0)
    dag.scale.set(1, 1, 1)

    # Perform combine or separate and clean up objects and leftover nulls.
    if s:
        new_dag = mampy.DagNode(cmds.polyUnite(dag.name, list(s), ch=False)[0])
        cmds.select(cmds.rename(clean_up_object(new_dag), dag.name), r=True)
    else:
        logger.debug('Separate Objects.')
        new_dags = mampy.SelectionList(cmds.polySeparate(dag.name, ch=False))
        for i in new_dags.copy().iterdags():
            cmds.rename(clean_up_object(i), dag.name)
        cmds.delete(dag.name)  # Delete leftover group.
        cmds.select(list(new_dags), r=True)


@mampy.history_chunk()
def unbevel():
    """
    Unbevel beveled edges.

    Select Edges along a bevel you want to unbevel. Make sure the edge is not
    connected to another edge from another bevel. This will cause the script
    to get confused.
    """
    def get_object_edge_indices_map():
        """
        Map selected verts to mesh dagpath.
        """
        obj_edge_indices = collections.defaultdict(set)
        for comp in s.itercomps():
            verts = comp.to_vert()
            obj_edge_indices[str(comp.dagpath)].add(tuple(verts.indices))
        return obj_edge_indices

    def get_edge_loop_from_indices(indices):
        """
        Loop through given indices and check if they are connected. Maps
        connected indices and returns a dict.
        """
        def is_ids_in_loop(ids):
            """
            Check if id is connected to any indices currently in
            loops[loop_count] key.
            """
            id1, id2 = ids
            for edge in loops[loop_count]:
                if id1 in edge or id2 in edge:
                    return True
            return False

        loop_count = 0
        loops = collections.defaultdict(set)
        while indices:

            loop_count += 1
            loops[loop_count].add(indices.pop())

            loop_growing = True
            while True:
                if loop_growing:
                    loop_growing = False
                else:
                    break

                for ids in indices.copy():
                    if is_ids_in_loop(ids):
                        loop_growing = True
                        loops[loop_count].add(ids); indices.remove(ids)
        return loops

    def get_outer_and_inner_edges(connected_edges):
        """
        Sort the connected_edges in outer and inner edges.
        """
        vert_count = collections.Counter()
        for edge in loop:
            vert_count.update(edge)

        outer_edges = []
        for uncommon in vert_count.most_common()[-2:]:

            # Get outer edge vert pair
            outer_vert = uncommon[0]
            outer_edge = [e for e in connected_edges if outer_vert in e].pop()
            inner_vert = [idx for idx in outer_edge if not idx == outer_vert].pop()

            outer_vert = mampy.MeshVert.create(dag).add(outer_vert)
            inner_vert = mampy.MeshVert.create(dag).add(inner_vert)

            # Remove outer edges, they will not be moved.
            connected_edges.remove(outer_edge)
            outer_edges.append((outer_vert, inner_vert))
        return outer_edges, connected_edges

    # Collect data
    s = mampy.ls(sl=True, fl=True)
    obj_edge_indices = get_object_edge_indices_map()
    obj_loops = {
        obj: get_edge_loop_from_indices(indices)
        for obj, indices in obj_edge_indices.iteritems()
        }

    # perform unbevel
    for dag, loops in obj_loops.iteritems():
        cmds.select(dag, r=True)

        merge_list = mampy.SelectionList()
        for loop in loops.itervalues():
            outer_edges, inner_edges = get_outer_and_inner_edges(loop)

            # Place verts that will be moved in selection list. Mergin verts
            # while looping will change the index list of the object.
            verts_to_move = mampy.MeshVert.create(dag)
            verts_to_move.add(set([idx for edge in inner_edges for idx in edge]))
            merge_list.append(verts_to_move)

            # Get intersection line.
            edge1, edge2 = outer_edges
            line1 = mampy.Line3D(edge1[0].points[0], edge1[1].points[0])
            line2 = mampy.Line3D(edge2[0].points[0], edge2[1].points[0])
            intersection_line = line1.shortest_line_to_other(line2)

            # collapse verts
            verts_to_move.translate(t=intersection_line.sum() * 0.5, ws=True)

        # Merge points on object after operation
        cmds.polyMergeVertex(list(merge_list), distance=0.001, ch=False)

    # Restore selection
    cmds.selectMode(component=True)
    cmds.hilite(list(obj_loops), r=True)
    cmds.select(cl=True)


@mampy.history_chunk()
def spin_edge():
    """
    Spin all selected edges.

    Allows us to spin edges within a face selection.
    """
    s = mampy.selected()
    for comp in s.itercomps():
        edge = comp.to_edge(internal=True)
        cmds.polySpinEdge(list(edge), offset=-1, ch=False)
    cmds.select(cl=True); cmds.select(list(s), r=True)


if __name__ == '__main__':
    spin_edge()

