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
from mampy._old.comps import MeshVert
from mampy._old.computils import get_vert_order_on_edge_row

from mampy.utils import undoable, repeatable, get_outliner_index
from mampy.core.dagnodes import Node
from mampy.core.components import MeshPolygon
from mampy.core.selectionlist import ComponentList
from mampy.core.exceptions import InvalidSelection

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


def make_circle(mode=0):

    def draw_circle():

        sl = mampy.comp_ls()
        for comp in sl:
            edge = comp.to_edge(border=True)
            circle_indices = get_vert_order_on_edge_row(
                [edge.mesh.getEdgeVertices(i) for i in edge.indices]
            )
            vert = MeshVert.create(edge.dagpath).add(circle_indices)
            circle_indices = [MeshVert.create(edge.dagpath).add(i) for i in circle_indices]

            vec = api.MFloatVector()
            for i in vert.indices:
                vec += vert.get_normal(i).normal()
            vec = (vec / len(vert)).normalize()

            center = api.MPoint()
            for i in vert.points:
                center += i
            center = center / len(vert.points) #  vert.bounding_box.center

            verts = collections.deque(circle_indices)
            for i in verts:
                if i.index == 104:
                    first_vert = i
                    break
            # print verts[282]

            # first_vert = get_dpsum(verts, vec)
            # Rotate list to first_vert
            for x in xrange(len(verts)):
                if verts[x] == first_vert:
                    break
            verts.rotate(-x)

            radius = sum([center.distanceTo(i.points[0]) for i in circle_indices]) / len(circle_indices)
            r1 = api.MFloatVector(list(first_vert.points[0] - center)[:3])
            r = (r1 ^ vec).normalize()
            s = (r ^ vec).normalize()

            # Create circle
            points = []
            theta = (math.pi*2) / len(circle_indices)
            for i, p in enumerate(verts):
                angle = theta*i
                x = center.x + radius * (math.sin(angle)*r.x + math.cos(angle)*s.x)
                y = center.y + radius * (math.sin(angle)*r.y + math.cos(angle)*s.y)
                z = center.z + radius * (math.sin(angle)*r.z + math.cos(angle)*s.z)
                points.append(api.MPoint(x, y, z))

        for v in verts:
            point = v.points[0]

            d = {point.distanceTo(p): p for p in points}
            result = d[min(d.iterkeys())]

            v.translate(translation=list(result)[:3], ws=True, absolute=True)
            points.remove(result)

    def get_dpsum(vert_row, average_vec):
        rotated_vec = api.MEulerRotation(average_vec).asMatrix()

        dpsum = 0
        first_vert = None
        greatest_dpsum = -999999999.999999999
        vert_deque = collections.deque(vert_row)
        for x in xrange(len(vert_deque)):
            vert_deque.append(vert_deque[0])

            dpsum = 0
            dtheta = math.radians(360 / len(vert_deque))
            theta = 0
            for i, vert in enumerate(vert_deque):
                theta = math.radians((360 / (len(vert_deque) - 1)) * i)

                angle_matrix = api.MMatrix((
                    [math.cos(theta), -math.sin(theta), 0, 0],
                    [math.sin(theta), math.cos(theta), 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1],
                ))
                rot_vec = angle_matrix * (api.MVector(vert.points[0] * rotated_vec))
                dpsum += api.MVector(vert.points[0]) * rot_vec
                theta += dtheta

            print 'dpsum', dpsum
            if dpsum > greatest_dpsum:
                first_vert, greatest_dpsum = vert_deque[0], dpsum

            vert_deque.pop()
            vert_deque.rotate(1)
        return first_vert


if __name__ == '__main__':
    spin_edge()

    # faces = mampy.ComponentList(cmds.sets('face_weighted_set', q=True))
    # dag_name = str(iter(faces).next().dagpath)
    # set_name = 'face_weighted_{}'.format(dag_name.replace('|', '_'))
    # # print set_name

    # face_weighted_name = 'face_weighted'
    # def modify_set(add=True):
    #     faces = mampy.dagp_ls()
    #     for face in faces:
    #         dag_name = str(face).replace('|', '_')
    #         set_name = '{}_{}'.format(face_weighted_name, dag_name)

    #         try:
    #             result = bool(cmds.sets(set_name, q=True))
    #         except ValueError:
    #             result = False
    #         print result

    #         if result:
    #             cmds.sets(cmds.ls(sl=True), addElement=set_name)
    #         else:
    #             cmds.sets(n=set_name)

    # def set_face_weighted_normals():

    #     faces = mampy.ComponentList()
    #     for set in cmds.ls('face_weighted*'):
    #         try:
    #             tmp = mampy.ComponentList(cmds.sets(set, q=True))
    #             faces.extend(tmp)
    #         except ValueError:
    #             continue

    #     for face in faces:
    #         for connected in face.get_connected():
    #             shared_vert_map = collections.defaultdict(list)

    #             for i in face.indices:
    #                 for pv in face.mesh.getPolygonVertices(i):
    #                     shared_vert_map[pv].append(i)

    #             for vert, shared in shared_vert_map.iteritems():
    #                 vec = api.MVector()
    #                 for idx in shared:
    #                     vec += face.mesh.getPolygonNormal(idx)
    #                 vec = vec / len(shared)
    #                 face.mesh.setVertexNormal(vec, vert)

    # # modify_set()
    # set_face_weighted_normals()

