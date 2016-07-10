import sys
import math
import logging
import functools

from maya import cmds, mel
import maya.api.OpenMaya as api

import mampy
from mampy.utils import undoable, repeatable, get_outliner_index
from mampy.exceptions import InvalidSelection
from mampy.selections import SelectionList
from mampy.nodes import DagNode
from mampy.datatypes import Line3D
from mampy.components import (MeshPolygon, MeshVert, get_connected_components,
                              get_outer_edges_in_loop)

from mamtools import contexts, delete, uv, mesh_select

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


EPS = sys.float_info.epsilon


@undoable
def detach_mesh(extract=False):
    """
    Extracts or duplicat selected polygon faces.
    """
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing selected.')

    new = SelectionList()
    for comp in s.itercomps():
        if not comp.is_face():
            continue

        # Duplicate
        trans = DagNode.from_object(comp.dagpath.transform())
        name = trans.name + ('_ext' if extract else '_dup')
        dupdag = cmds.duplicate(str(comp.dagpath), n=name).pop(0)

        # Delete children transforms
        children = cmds.listRelatives(dupdag, type='transform', f=True)
        if children is not None:
            cmds.delete(children)

        # Delete unused faces
        if extract:
            cmds.polyDelFacet(list(comp))

        dcomp = MeshPolygon.create(dupdag)
        dcomp.add(comp.indices)
        print dcomp.is_complete()
        if not dcomp.is_complete():
            cmds.polyDelFacet(list(dcomp.toggle()))

        # Select
        cmds.hilite(str(dcomp.dagpath))
        new.append(dcomp.get_complete())

    cmds.select(list(new), r=True)


@undoable
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

        dag['rotate'] = list(src_trns.rotate)
        dag['scale'] = list(src_trns.scale)
        return dag.name

    s = mampy.ordered_selection(tr=True, l=True)
    hl = mampy.ls(hl=True)
    if len(s) == 0:
        if len(hl) > 0:
            s = hl
        else:
            return logger.warn('Nothing Selected.')

    dag = s.pop()
    parent = dag.get_parent()

    # Get origin information from source object
    trns = dag.get_transform()
    src_trns = trns.get_transforms()
    pivot = trns.get_rotate_pivot()

    if s:
        logger.debug('Combining Objects.')
        for i in s.iterdags():
            if dag.is_child_of(i):
                raise InvalidSelection('Cannot parent an object to one of its children')
            if dag.is_parent_of(i):
                continue
            i.set_parent(dag)

    # Now we can check source objects position in outliner and
    # un-rotate/un-scale
    outliner_index = get_outliner_index(dag)
    dag.rotate = (0, 0, 0)
    dag.scale = (1, 1, 1)

    # Perform combine or separate and clean up objects and leftover nulls.
    if s:
        new_dag = DagNode(cmds.polyUnite(dag.name, list(s), ch=False)[0])
        cmds.select(cmds.rename(clean_up_object(new_dag), dag.name), r=True)
    else:
        logger.debug('Separate Objects.')
        new_dags = SelectionList(cmds.polySeparate(dag.name, ch=False))
        for i in new_dags.copy().iterdags():
            cmds.rename(clean_up_object(i), dag.name)
        cmds.delete(dag.name)  # Delete leftover group.
        cmds.select(list(new_dags), r=True)


def flatten(averaged=True):
    """
    Flattens selection by averaged normal.
    """
    def flatten(vector):
        cmds.select(list(s))
        comp = s.itercomps().next()

        # Perform scale
        cmds.manipScaleContext('Scale', e=True, mode=6, alignAlong=vector)
        radians = cmds.manipScaleContext('Scale', q=True, orientAxes=True)
        t = [math.degrees(r) for r in radians]
        cmds.scale(0, 1, 1, r=True, oa=t, p=list(comp.bounding_box.center)[:3])

    def script_job():
        """
        Get normal from script job selection and pass it to flatten.
        """
        driver = mampy.selected()
        for comp in driver.itercomps():
            vector = comp.get_normal(comp.index).normalize()
        flatten(vector)

    s = mampy.selected()
    if averaged:
        # Get average normal and scale selection to zero
        for c in s.itercomps():
            comp = c.to_vert()
            average_vector = api.MFloatVector()
            for idx in comp.indices:
                average_vector += comp.get_normal(idx)
            average_vector /= len(comp.indices)
        flatten(average_vector)
    else:
        # Scale selection to given selection.
        cmds.scriptJob(event=['SelectionChanged', script_job], runOnce=True)


@undoable
def unbevel():
    """
    Unbevel beveled edges.

    Select Edges along a bevel you want to unbevel. Make sure the edge is not
    connected to another edge from another bevel. This will cause the script
    to get confused.
    """
    s = mampy.selected()
    for comp in s.itercomps():

        cmds.select(str(comp.dagpath), r=True)
        merge_list = SelectionList()

        for c in get_connected_components(comp):
            outer_edges, rest = get_outer_edges_in_loop(c)

            edge1, edge2 = outer_edges
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


@undoable
def spin_edge():
    """
    Spin all selected edges.

    Allows us to spin edges within a face selection.
    """
    s = mampy.selected()
    for comp in s.itercomps():
        edge = comp.to_edge(internal=True)
        cmds.polySpinEdge(list(edge), offset=-1, ch=False)
    cmds.select(cl=True)
    cmds.select(list(s), r=True)


def get_vert_order_on_edge_row(indices):
    """
    .. note:: Should probably be moved to mampy.
    """
    idx = 0
    next_ = None
    sorted_ = []
    while indices:

        edge = indices.pop(idx)
        if next_ is None:
            next_ = edge[-1]

        sorted_.append(next_)
        for i in indices:
            if next_ in i:
                idx = indices.index(i)
                next_ = i[-1] if next_ == i[0] else i[0]
                break

    return sorted_


def make_circle(mode=0):
    """
    Make circle from selection.

    .. note:: This is pretty broken still, will need a rehaul when opertunity
    is given.
    """
    import collections
    s = mampy.selected()
    for comp in s.itercomps():

        connected = get_connected_components(comp)
        for con in connected:
            edges = con.to_edge(border=True)
            indices = [edges.mesh.getEdgeVertices(i) for i in edges.indices]
            vert_row = get_vert_order_on_edge_row(indices)
            vert_row = [
                MeshVert.create(con.dagpath).add(i) for i in vert_row
            ]
            cen_point = con.bounding_box.center

            # Get average Normal
            avg_normal = api.MFloatVector()
            for i in con.indices:
                avg_normal += con.get_normal(i).normal()
            avg_normal = api.MVector(avg_normal / len(con))

            # # Get Plane
            proj_normal = avg_normal.normal()
            dist = [(vert.points[0] - cen_point).length() for vert in vert_row]
            radius = sum(dist) / len(vert_row)

            # Sorting help
            angle = []
            for i, vert in enumerate(vert_row):
                try:
                    vec1 = vert.points[0] - cen_point
                    vec2 = vert_row[i + 1].points[0] - cen_point
                except IndexError:
                    pass

                angle1 = math.degrees(math.atan2(vec1.x, vec1.y))
                angle2 = math.degrees(math.atan2(vec2.x, vec2.y))

                if angle2 > 90 and angle1 < -90:
                    angle1 += 360
                elif angle1 > 90 and angle2 < -90:
                    angle2 += 360

                angle_sum = angle2 - angle1
                if angle_sum < -180:
                    angle_sum += 180

                print angle_sum

                angle.append(angle_sum)

            if sum(angle) > 0:
                vert_row.reverse()

            dpsum = 0
            first_vert = None
            greatest_dpsum = -999999999.999999999
            vert_deque = collections.deque(vert_row)
            for x in xrange(len(vert_deque)):
                vert_deque.append(vert_deque[0])

                dpsum = 0
                for i, vert in enumerate(vert_deque):
                    radian = math.radians((360 / (len(vert_deque) - 1)) * i)

                    angle_matrix = api.MMatrix((
                        [math.cos(radian), -math.sin(radian), 0, 0],
                        [math.sin(radian), math.cos(radian), 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ))
                    rot_vec = api.MVector(vert.points[0] * angle_matrix)
                    dpsum += api.MVector(vert.points[0]) * rot_vec

                print 'dpsum', dpsum
                if dpsum > greatest_dpsum:
                    first_vert, greatest_dpsum = vert_deque[0], dpsum

                vert_deque.pop()
                vert_deque.rotate(1)

            # Rotate
            for x in xrange(len(vert_deque)):
                if vert_deque[x] == first_vert:
                    break
                vert_deque.rotate()

            # Radius average
            # avg_radius = 0
            # for x, vert in enumerate(vert_deque):
            #     avg_radius += (vert.points[0]-vert_deque[x-1].points[0]).length()
            # avg_radius /= (math.pi*2)

            # Perform
            if mode == 0:
                # Equal
                base_point = vert_deque[0].points[0]
                # base_vector = (base_point - cen_point).normal()
                base_vector = base_point - cen_point

                degeree_span = 360 / len(vert_deque)

                for i, vert in enumerate(vert_deque):

                    rad_span = math.radians(degeree_span * i)
                    rot_vector = base_vector.rotateBy(
                        api.MQuaternion(rad_span, avg_normal)
                    )
                    trans = api.MVector(cen_point + rot_vector)
                    vert.translate(t=trans, ws=True)

            elif mode == 1:
                # Closest
                for vert in vert_deque:
                    unit_vector = (vert.points[0] - cen_point).normal()
                    angle_a = math.degrees(avg_normal.angle(unit_vector))
                    angle_b = 90 - angle_a
                    length = math.sin(math.radians(angle_b))

                    print length
                    cb = length * avg_normal
                    ac = unit_vector - cb
                    dist = ac.length()
                    ac = ac * (radius / dist)
                    ac = api.MVector(cen_point + ac)

                    vert.translate(t=ac, ws=True)


# CONTEXT SENSITIVE FUNCTIONS


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
            api.MFn.kMeshVertComponent: functools.partial(delete.merge_verts, True),
            api.MFn.kMeshPolygonComponent: delete.merge_faces,
            api.MFn.kMeshEdgeComponent: delete.collapse,
            api.MFn.kMesh: combine_separate,
        }[t]()
    except KeyError:
        logger.warn('{} is not a valid type'.format(t))


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
            detach_mesh(extract)
        elif s.type in [api.MFn.kTransform]:
            cmds.duplicate(rr=True)  # parentOnly=hierarchy)


def get_border_loop_from_edge_index(index):
    return set(sorted([int(i) for i in cmds.polySelect(q=True, edgeBorder=index)]))


def get_border_loop_from_edge(component):
    return set([
        tuple(border for border in get_border_loop_from_edge_index(idx))
        for idx in component.indices
    ])


def get_indices_sharing_edge_border(component):
    """Get indices sharing border edge loop from component."""
    edge_borders = SelectionList()
    for border in get_border_loop_from_edge(component):
        new_component = component.new()
        for index in component.indices:
            if index in border:
                new_component.add(index)
        edge_borders.append(new_component)
    return edge_borders


def get_border_edges_from_selection(edge_selection):
    """Get border edges from selection and return a new selection list."""
    border_edges = SelectionList()
    for component in edge_selection.itercomps():
        borders = component.new()
        for index in component.indices:
            if not component.is_border(index):
                continue
            borders.add(index)
        if borders:
            border_edges.append(borders)
    return border_edges


@undoable
@repeatable
def bridge():
    selected = mampy.selected()
    if not selected:
        raise InvalidSelection('Nothing selected, select border edges.')
    borders = get_border_edges_from_selection(selected)

    for component in borders.itercomps():
        if component.type == api.MFn.kMeshPolygonComponent:
            bridge_face()
        elif component.type == api.MFn.kMeshEdgeComponent:
            borders = get_indices_sharing_edge_border(component)
            for each in borders.itercomps():
                cmds.select(list(each), r=True)
                connected = get_connected_components(each)
                if not len(component) > 1 or len(connected) > 1:
                    cmds.polyBridgeEdge(divisions=0)
                elif len(component) == 2 and len(connected) == 1:
                    cmds.polyAppend(str(component.dagpath),
                                    s=1, a=(component.index, component.indices[-1]))
                else:
                    mel.eval('polyPerformAction polyCloseBorder e 0;')

    cmds.select(list(borders))


@undoable
def bridge_face():
    faces = mampy.selected()
    mesh_select.convert('edge')
    cmds.delete(list(faces))
    cmds.polyBridgeEdge(divisions=0)


if __name__ == '__main__':
    bridge_face()
