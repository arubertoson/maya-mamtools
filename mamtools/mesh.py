"""
"""
import sys
import math
import logging
import collections

from maya import cmds
from maya.api.OpenMaya import MFn
import maya.api.OpenMaya as api

import mampy
from mampy.utils import undoable, repeatable, get_outliner_index
from mampy.core.datatypes import BoundingBox
from mampy.core.dagnodes import Node
from mampy.core.components import MeshPolygon, MeshVert, get_vert_order_from_connected_edges
from mampy.core.selectionlist import ComponentList
from mampy.core.exceptions import InvalidSelection, ObjecetDoesNotExist
from mampy.core.utils import get_average_vert_normal

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


EPS = sys.float_info.epsilon


@undoable()
@repeatable
def detach(extract=False):
    """
    Extracts or duplicate selected polygon faces.
    """
    selected = mampy.complist()
    if not selected:
        raise InvalidSelection('Detach only works on edge and polygon components.')
    else:
        control = selected[0]
        if control.type not in [MFn.kMeshPolygonComponent, MFn.kMeshEdgeComponent]:
            raise InvalidSelection('Detach only works on edges and polygons.')

    new = ComponentList()
    for comp in selected:

        node = Node(comp.dagpath)
        name = '{}_{}'.format(node.transform.short_name, 'ext' if extract else 'dup')
        cmds.duplicate(str(comp.dagpath), n=name)

        # Delete unwanted children from duplicate hierarchy
        dupdag = Node(name)
        for child in dupdag.iterchildren():
            if child.type == MFn.kTransform:
                cmds.delete(str(child))

        if extract:
            cmds.polyDelFacet(comp.cmdslist())

        dupcomp = MeshPolygon.create(dupdag.dagpath).add(comp.indices)
        cmds.polyDelFacet(dupcomp.toggle().cmdslist())

        cmds.hilite(str(dupdag))
        new.append(dupcomp.get_complete())
    cmds.select(new.cmdslist(), r=True)


@undoable()
@repeatable
def combine_separate():
    """
    Depending on selection will combine or separate objects.

    Script will try to retain the transforms and outline position of the
    first object selected.

    """
    def clean_up_object(new):
        """
        Cleans up after `polyUnite` / `polySeparate`
        """
        if not new.get_parent() == parent:
            new.set_parent(parent)

        cmds.reorder(str(new), f=True)
        cmds.reorder(str(new), r=outliner_index)
        new.transform.set_pivot(pivot)

        new.attr['rotate'] = list(transforms.rotate)
        new.attr['scale'] = list(transforms.scale)
        return cmds.rename(str(new), name.split('|')[-1])

    selected = mampy.daglist(os=True, tr=True, l=True)
    if not selected:
        raise InvalidSelection()

    dag = selected.pop()
    name, parent = dag.short_name, dag.get_parent()
    transforms = dag.transform.get_transforms()
    pivot = dag.transform.get_rotate_pivot()

    if selected:
        logger.debug('Combining Objects.')
        for each in selected:
            if dag.is_child_of(each):
                raise InvalidSelection('Cannot parent an object to one of its '
                                       'children')
            elif dag.is_parent_of(each):
                continue
            each.set_parent(each)

    outliner_index = get_outliner_index(dag)
    dag.transform.attr['rotate'] = (0, 0, 0)
    dag.transform.attr['scale'] = (1, 1, 1)

    if selected:
        new_dag = Node(cmds.polyUnite(name, selected.cmdslist(), ch=False)[0])
        cmds.select(clean_up_object(new_dag), r=True)
    else:
        logger.debug('Separate Objects.')
        new_dags = mampy.daglist(cmds.polySeparate(name, ch=False))
        for new in new_dags:
            cmds.rename(clean_up_object(new), name.split('|')[-1])
        cmds.delete(name)
        cmds.select(new_dags.cmdslist(), r=True)


@undoable()
@repeatable
def flatten(averaged=True):
    """
    Flattens selection by averaged normal.
    """
    def flatten(component, script_job=False):

        if script_job:
            cmds.select(selected.cmdslist())
        else:
            cmds.select(component.cmdslist())

        center = list(component.bbox.center)[:3]
        origin = get_average_vert_normal(component.normals, component.indices)

        # Perform scale
        cmds.manipScaleContext('Scale', e=True, mode=6, alignAlong=origin)
        radians = cmds.manipScaleContext('Scale', q=True, orientAxes=True)
        t = [math.degrees(r) for r in radians]
        cmds.scale(0, 1, 1, r=True, oa=t, p=center)

    def script_job():
        """
        Get normal from script job selection and pass it to flatten.
        """
        flatten(next(iter(mampy.complist())).to_vert(), True)

    selected = mampy.complist()
    if averaged:
        for comp in selected:
            flatten(comp.to_vert())
        cmds.select(selected.cmdslist(), r=True)
    else:
        # Scale selection to given selection.
        cmds.scriptJob(event=['SelectionChanged', script_job], runOnce=True)


@undoable()
@repeatable
def spin_edge(offset=1):
    """
    Spin all selected edges.

    Allows us to spin edges within a face selection.
    """
    selected = mampy.complist()
    for comp in selected:
        if not comp.is_edge():
            comp = comp.to_edge(internal=True)
        cmds.polySpinEdge(comp.cmdslist(), offset=offset, ch=False)
    cmds.select(cl=True); cmds.select(selected.cmdslist(), r=True)


@undoable()
def draw_circle():

    def dpsum():
        verts = collections.deque(ordered_verts)
        plane_euler = api.MEulerRotation(plane_unit_vector).asMatrix()
        greatest_sum = 0
        for x in xrange(len(verts)):
            verts.append(verts[0])

            dpsum = 0
            theta = (math.pi*2) / (len(verts)-1)
            for idx, vert in enumerate(verts):
                angle = theta*idx
                point = vert.bbox.center
                angle_matrix = api.MMatrix((
                    [math.cos(angle), -math.sin(angle), 0, 0],
                    [math.sin(angle), math.cos(angle), 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1],
                ))
                rotate_vector = angle_matrix * api.MVector(point * plane_euler)
                dpsum += api.MVector(point) * rotate_vector

            if dpsum > greatest_sum:
                greatest_sum, first = dpsum, verts[0]
            verts.pop()
            verts.rotate(1)
        return first.indices[0]

    def get_control_vert():
        for vert in selected:
            # make sure vert belongs to same dagpath object and is vert
            if not vert.is_vert() or not vert.dagpath == comp.dagpath:
                continue

            for index in vert.indices:
                if index in comp.vertices:
                    return index
        # If we can't find a control vert try to determine the vert.
        # This is very unreliable but better than skewed results.
        return dpsum()

    selected = mampy.multicomplist()
    for component in selected:
        # Verts are used to specify first vert in row. Exit out if we encounter
        # one here.
        if component.is_vert():
            continue

        for comp in component.get_connected_components():

            # Only work on border edges
            edge = comp.to_edge(border=True)

            # Order the vert list to make sure we operate in order.
            ordered_vert_indices = get_vert_order_from_connected_edges(edge.vertices.values())
            vert_object = MeshVert.create(comp.dagpath).add(ordered_vert_indices)
            ordered_verts = [vert_object.new().add(i) for i in ordered_vert_indices]
            # Get plane unit vector from selection.
            plane_vector = get_average_vert_normal(vert_object.normals, vert_object.indices)
            plane_unit_vector = plane_vector.normalize()

            # Cant use the components bounding box here as the bounding box is not
            # rotated to fit the component. The only valid way to get center is
            # average the selected points.
            center = api.MPoint()
            for i in comp.points:
                center += i
            center /= len(comp.points)

            # iterate over the selection and try to find the selected control point.
            control_vert_index = get_control_vert()
            # place vert at beginning of list.
            index_of_control_vert = ordered_vert_indices.index(control_vert_index)
            ordered_verts = collections.deque(ordered_verts)
            ordered_verts.rotate(index_of_control_vert)

            # make circle
            radius = sum([center.distanceTo(i.bbox.center) for i in ordered_verts])
            radius /= len(ordered_verts)

            r1 = api.MFloatVector(comp.points[control_vert_index] - center)
            r = (r1 ^ plane_unit_vector).normalize()
            s = (r ^ plane_unit_vector).normalize()

            # Create circle and place points in a list, verts might actually not
            # represent the correct translation yet.
            points = []
            theta = (math.pi*2) / len(ordered_verts)
            for i, p in enumerate(ordered_verts):
                angle = theta*i
                x = center.x + radius * (math.sin(angle)*r.x + math.cos(angle)*s.x)
                y = center.y + radius * (math.sin(angle)*r.y + math.cos(angle)*s.y)
                z = center.z + radius * (math.sin(angle)*r.z + math.cos(angle)*s.z)

                points.append(api.MPoint(x, y, z))

            # Finally move the points, find the closest vert to result and move
            # that vert there.
            for v in ordered_verts:
                point = v.bbox.center

                d = {point.distanceTo(p): p for p in points}
                result = d[min(d.iterkeys())]

                v.translate(translation=list(result)[:3], ws=True, absolute=True)
                points.remove(result)


_face_weighted_name = 'face_weighted'
def get_face_weighted_set_name(input_string):
    return '{}_{}'.format(_face_weighted_name, input_string)


def set_face_weighted_normals_sets(add=True):
    faces = mampy.complist()
    for face in faces:
        name = face.mdag.transform.short_name
        set_name = get_face_weighted_set_name(name)

        try:
            result = bool(cmds.sets(set_name, q=True))
        except ValueError:
            result = False

        if result:
            if add:
                cmds.sets(face.cmdslist(), addElement=set_name)
            else:
                cmds.sets(face.cmdslist(), remove=set_name)
        else:
            cmds.sets(name=set_name)


def get_face_weighted_sets():
    sets = cmds.ls('{}*'.format(_face_weighted_name))
    selected, to_weight = mampy.daglist(), ComponentList()
    if selected:
        for each in selected:
            set_name = get_face_weighted_set_name(each.transform.short_name)
            if set_name in sets:
                to_weight.extend(mampy.complist(cmds.sets(set_name, q=True)))
    else:
        for set_name in sets:
            try:
                to_weight.extend(mampy.complist(cmds.sets(set_name, q=True)))
            except ValueError:
                continue
    return to_weight


def display_face_weighted_normals_sets():
    cmds.select(get_face_weighted_sets().cmdslist())


def set_face_weighted_normals():
    """
    """
    to_weight = get_face_weighted_sets()
    if not to_weight:
        raise ObjecetDoesNotExist()

    for each in to_weight:
        for connected in each.get_connected_components():
            shared_vert_map = collections.defaultdict(list)

            for idx in connected.indices:
                for vert_index in each.vertices[idx]:
                    shared_vert_map[vert_index].append(idx)

            for vert, shared in shared_vert_map.iteritems():
                averaged = get_average_vert_normal(each.normals, shared)
                each.mesh.setVertexNormal(averaged, vert)


def set_vertex_normals_on_selected_from_vector(vector):
    for component in mampy.complist():
        if not component.is_vert():
            component = component.to_vert()
        for index in component:
            normal = (component.points[index] - vector).normalize()
            component.mesh.setVertexNormal(normal, index, space=api.MSpace.kWorld)


def vertex_normals_from_origo():
    set_vertex_normals_on_selected_from_vector(api.MPoint(api.MPoint.kOrigin))


def vertex_normals_from_selection_center():
    bbox = BoundingBox()
    for component in mampy.complist():
        if not component.is_vert():
            component = component.to_vert()
        bbox.expand(component.bbox)
    set_vertex_normals_on_selected_from_vector(bbox.center)


if __name__ == '__main__':
    pass
