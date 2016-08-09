import math
import logging
import itertools

from maya import cmds
from maya.api import OpenMaya as api

import mampy
from mampy.packages import mvp
from mampy.dgcomps import Component
from mampy.dgnodes import Camera
from mampy.utils import undoable, get_outliner_index

logger = logging.getLogger(__name__)


def set_pivot_center():
    cmds.xform(cp=True)


def set_pivot(vector=(0, 0, 0)):
    vec = api.MVector(vector)
    for each in mampy.ls(sl=True, tr=True, l=True).iterdags():
        try:
            each.get_transform().set_pivot(vec)
        except RuntimeError():
            raise mampy.InvalidSelection('{} is not valid for function.'
                                         .format(each.typestr))


@undoable
def match_pivot_to_object():
    """
    Match secondary selection pivots to first object selected.
    """
    s, hl = mampy.ordered_selection(tr=True, l=True), mampy.ls(hl=True)
    if len(s) == 0:
        if len(hl) > 0:
            s = hl
        else:
            return logger.warn('Nothing Selected.')

    # check driver information
    dag = s.pop(0)
    trns = dag.get_transform()
    piv = trns.get_scale_pivot()

    # set pivot for driven objects
    for each in s.iterdags():
        print each, type(each)
        trns = each.get_transform().set_pivot(piv)


@undoable
def bake_pivot():
    """
    Bake modified manipulator pivot onto object.
    """
    s = mampy.ordered_selection(tr=True, l=True)
    dag = s.pop(len(s) - 1)
    out_idx = get_outliner_index(dag)
    parent = dag.get_parent()

    # Get manipulator information
    pos = cmds.manipMoveContext('Move', q=True, p=True)
    rot = cmds.manipMoveContext('Move', q=True, oa=True)
    rot = tuple(math.degrees(i) for i in rot)

    # Create dummpy parent
    space_locator = cmds.spaceLocator(name='bake_dummy_loc', p=pos)[0]
    cmds.xform(space_locator, cp=True)
    cmds.xform(space_locator, rotation=rot, ws=True)

    dag.set_parent(space_locator)
    cmds.makeIdentity(dag.name, rotate=True, translate=True, apply=True)

    dag.set_parent(parent)
    cmds.delete(space_locator)
    cmds.reorder(dag.name, f=True); cmds.reorder(dag.name, r=out_idx)
    cmds.select(list(s), r=True); cmds.select(dag.name, add=True)


def get_pane_size(pane):
    """
    Return pane size of given pane.
    """
    return [cmds.control(pane, q=True, **{p: True}) for p in ['w', 'h']]


def get_world_vectors():
    matrix = chunks(list(api.MMatrix()), 4)
    xyz = [api.MVector(i[:-1]) for i in list(matrix)[:-1]]
    axes = []
    for idx, vec in enumerate(itertools.repeat(xyz, 2)):
        axes.extend([v if idx == 1 else (v * -1) for v in vec])
    return axes


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]


class InvalidManipType(Exception):
    """Raise when invalid manipulator is encountered."""


class BaseManip(object):

    manip_names = {
        'RotateSupercontext': 'Rotate',
        'moveSuperContext': 'Move',
        'scaleSuperContext': 'Scale',
    }
    world_vectors = get_world_vectors()
    type_ = None

    def __init__(self):
        self._name = None

    def cmd(self, **kwargs):
        return {
            'RotateSupercontext': cmds.manipRotateContext,
            'moveSuperContext': cmds.manipMoveContext,
            'scaleSuperContext': cmds.manipScaleContext,
        }[self.type](self.name, **kwargs)

    @property
    def is_active(self):
        return cmds.currentCtx() == self.type

    @property
    def mode(self):
        return {
            0: 'object',
            1: 'parent',
            2: 'world',
            4: 'object',
            5: 'live',
            6: 'custom',
            9: 'custom',
        }[self.cmd(q=True, mode=True)]

    @property
    def active_axis(self):
        return self.cmd(q=True, currentActiveHandle=True)

    @property
    def orient(self):
        return api.MEulerRotation(self.cmd(q=True, orientAxes=True))

    @property
    def position(self):
        return self.cmd(q=True, position=True)

    @property
    def type(self):
        if self.type_ is None:
            raise NotImplemented()
        return self.type_

    @property
    def name(self):
        if self._name is None:
            self._name = self.manip_names[self.type]
        return self._name

    def set_active_handle(self, handle):
        self.cmd(e=True, currentActiveHandle=handle)


class MoveManip(BaseManip):
    type_ = 'moveSuperContext'


class ScaleManip(BaseManip):
    type_ = 'scaleSuperContext'


class RotateManip(BaseManip):
    type_ = 'RotateSupercontext'

    @property
    def mode(self):
        return {
            0: 'object',
            1: 'world',
            2: 'object',
            3: 'custom',
            9: 'custom',
        }[self.cmd(q=True, mode=True)]


def set_active_axes_to_view(manip=0, axis_mode=0):
    manip = {
        0: MoveManip,
        1: RotateManip,
        2: ScaleManip,
    }[manip]()

    offset = get_vector_offset(manip)
    camera = Camera(mvp.Viewport.active().camera)
    main_vector = camera.get_view_direction()

    vector_map = get_axis_vector_map(main_vector, offset, mode=axis_mode)
    closest_match = max(vector_map, key=vector_map.get)

    manip.set_active_handle(closest_match)


def set_active_axes(axis='center'):
    try:
        ctx = cmds.currentCtx()
        manip = {cls.type_: cls for cls in BaseManip.__subclasses__()}[ctx]()
    except KeyError:
        return logger.warn('Supports move, scale and rotate super context')
    dispatch = {
        'x': 0,
        'y': 1,
        'z': 2,
        'center': 3,
        'xy': 4,
        'yz': 5,
        'xz': 6,
    }[axis]
    manip.set_active_handle(dispatch)


def get_vector_offset(manip):
    """
    :: todo ..
        implement parent
        implement live
    """
    try:
        offset = {
            'custom': manip.orient.asMatrix,
            'object': get_object_vector,
            # 'parent': get_parent_object,
            # 'live': get_live_object,
        }[manip.mode]()
    except KeyError:
        offset = api.MMatrix()
    return offset


def get_object_vector():
    selected = mampy.selected().iterdags().next()
    transform = selected.get_transform()
    rotation = transform._mfntrans.rotation()
    return rotation.asMatrix()


def get_axis_vector_map(view_vec, offset, mode=0):
    world_vectors = get_world_vectors()
    camera_vector = {}
    for v in world_vectors:
        axis = {
            0: get_axis_from_vector,
            1: get_perpenticular_axis_from_vector,
            2: get_perpenticular_axes_from_vector,
        }[mode](v)
        view_angle = view_vec * (v * offset)
        if axis in camera_vector:
            if view_angle > camera_vector[axis]:
                camera_vector[axis] = view_angle
        else:
            camera_vector[axis] = view_angle
    return camera_vector


def get_axis_from_vector(vec):
    for idx, n in enumerate(vec):
        if abs(n):
            return {
                0: 0,  # x
                1: 1,  # y
                2: 2,  # z
            }[idx]


def get_perpenticular_axis_from_vector(vec):
    for idx, n in enumerate(vec):
        if abs(n):
            return {
                0: 2,  # x => z
                1: 0,  # y => x
                2: 1,  # z => y
            }[idx]


def get_perpenticular_axes_from_vector(vec):
    for idx, n in enumerate(vec):
        if abs(n):
            return {
                0: 5,  # x => yz
                1: 6,  # y => xz
                2: 4,  # z => xy
            }[idx]


def scale_to_zero():
    piv = ScaleManip()
    scalar = [1, 1, 1]
    try:
        scalar[piv.active_axis] = 0
    except IndexError:
        return
    cmds.scale(*scalar, pivot=piv.position)


def scale_mirror():
    piv = ScaleManip()

    sel = mampy.selected()[0]
    if isinstance(sel, Component):
        scalar = [1, 1, 1]
    else:
        scalar = cmds.xform(str(sel), q=True, r=True, scale=True)

    try:
        value = scalar[piv.active_axis]
        scalar[piv.active_axis] = value * -1
    except IndexError:
        return
    cmds.scale(*scalar, pivot=piv.position)


if __name__ == '__main__':
    scale_mirror()
