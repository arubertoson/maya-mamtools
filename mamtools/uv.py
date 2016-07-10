import math
import logging
import operator

import maya.cmds as cmds
import maya.api.OpenMaya as api

import mampy
from mampy.selections import SelectionList
from mampy.components import MeshPolygon, MeshMap
from mampy.utils import undoable, repeatable, grouped
from mampy.datatypes import BoundingBox, Line2D

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class UV3DArea(object):

    def __init__(self, comp):

        if not comp:
            faces = MeshPolygon(comp.dagpath).get_complete()
        else:
            faces = comp.to_face()

        self.comp = faces
        self.uv = 0.0
        self.surface = 0.0

        self.mesh = comp.mesh
        self.points = self.mesh.getPoints(space=api.MSpace.kWorld)
        self.internal_distance = api.MDistance.internalToUI
        self.get_polygon_uv = self.mesh.getPolygonUV
        self.get_polygon_vert = self.mesh.getPolygonVertices

        self.update()

    @property
    def ratio(self):
        return math.sqrt(self.surface / self.uv)

    def _get_uv_area(self, idx):
        """
        Return uv area of given face index.
        """
        verts = self.get_polygon_vert(idx)
        vert_len = len(verts) - 1

        au, av = self.get_polygon_uv(idx, 0)
        for i in xrange(1, vert_len):
            if i + 1 > vert_len:
                break
            bu, bv = self.get_polygon_uv(idx, i)
            cu, cv = self.get_polygon_uv(idx, i + 1)
            s = (bu - au) * (cv - av)
            t = (cu - au) * (bv - av)
            self.uv += abs((s - t) * 0.5)

    def _get_surface_area(self, idx):
        """
        Return surface area of given face index.
        """
        verts = self.get_polygon_vert(idx)
        vert_len = len(verts) - 1

        a = self.points[verts[0]]
        for i in xrange(1, vert_len):
            if i + 1 > vert_len:
                break
            b = self.points[verts[i]]
            c = self.points[verts[i + 1]]

            la = a.distanceTo(b)
            lb = a.distanceTo(c)
            lc = b.distanceTo(c)

            # convert to internal distance
            la = self.internal_distance(la)
            lb = self.internal_distance(lb)
            lc = self.internal_distance(lc)

            s = (la + lb + lc) * 0.5
            self.surface += math.sqrt(s * (s - la) * (s - lb) * (s - lc))

    def update(self):
        self.uv = 0.0
        self.surface = 0.0
        for idx in self.comp.indices:
            self._get_uv_area(idx)
            self._get_surface_area(idx)


def get_areas():
    s = mampy.selected()
    if not s:
        logger.warn('Nothing selected.')

    return [UV3DArea(c) for c in s.itercomps()]


def get_average_texel_density(areas, texture_size):
    return (sum([a.ratio for a in areas]) / len(areas)) * texture_size


def get_texel_density(areas=None, texture_size=1024):
    return sum([a.ratio for a in areas or get_areas()]) * texture_size


def set_texel_density(shell=True, target_density=0, texture_size=1024):
    if shell:
        areas = [UV3DArea(c) for c in get_shells()]
    else:
        selected = mampy.selected()
        components = SelectionList()
        components.extend([c.get_complete() for c in selected.itercomps()])
        areas = [UV3DArea(c) for c in get_shells(components)]

    if target_density == 0:
        target_density = get_average_texel_density(areas, texture_size)

    print areas
    for area in areas:
        scale_value = (area.ratio * texture_size) / target_density
        print scale_value

        uvs = area.comp.to_map()
        print uvs
        point = uvs.bounding_box.center
        uvs.translate(su=scale_value, sv=scale_value, pu=point.u, pv=point.v)


def get_shells(components=None):
    """
    Collect selected uv shells.
    """
    s = components or mampy.selected()
    if not s:
        h = mampy.ls(hl=True)
        if not h:
            return logger.warn('Nothing selected.')
        s.extend(h)

    shells = SelectionList()
    for c in s.itercomps():
        if not c:
            print 'test'
            c = MeshMap(c.dagpath).get_complete()
        else:
            c = c.to_map()

        count, array = c.mesh.getUvShellsIds()
        wanted = set([array[idx] for idx in c.indices])

        for each in wanted:
            shell = MeshMap.create(c.dagpath)
            shell.add([idx for idx, num in enumerate(array) if num == each])
            shells.append(shell)
    return list(shells.itercomps())


class AlignUV(object):

    (MAX_U, MAX_V, MIN_U, MIN_V, CENTER_U, CENTER_V, SCALE_MAX_U, SCALE_MAX_V,
     SCALE_MIN_U, SCALE_MIN_V, DISTRIBUTE_U, DISTRIBUTE_V, SPACE_U,
     SPACE_V) = range(14)

    def __init__(self, mode):
        self.mode = mode
        self.shells = get_shells()

        # properties
        self._bbox = None
        self._span = None
        self._max_width = None
        self._max_height = None
        self._min_width = None
        self._min_height = None
        self._shell_sum = None

        if self.mode in (self.DISTRIBUTE_U, self.SPACE_U):
            self.calc_dir = 'width'
            self.shells.sort(key=operator.attrgetter('bounding_box.center.u'))
        elif self.mode in (self.DISTRIBUTE_V, self.SPACE_V):
            self.calc_dir = 'height'
            self.shells.sort(key=operator.attrgetter('bounding_box.center.v'))

    @property
    def bbox(self):
        if self._bbox is None:
            self._bbox = BoundingBox()
            self._bbox.boxtype = '2D'
            for shell in self.shells:
                self._bbox.expand(shell.bounding_box)
        return self._bbox

    @property
    def max_width(self):
        if self._max_width is None:
            self._max_width = max(shell.bounding_box.width
                                  for shell in self.shells)
        return self._max_width

    @property
    def max_height(self):
        if self._max_height is None:
            self._max_height = max(shell.bounding_box.height
                                   for shell in self.shells)
        return self._max_height

    @property
    def min_width(self):
        if self._min_width is None:
            self._min_width = min(shell.bounding_box.width
                                  for shell in self.shells)
        return self._min_width

    @property
    def min_height(self):
        if self._min_height is None:
            self._min_height = min(shell.bounding_box.height
                                   for shell in self.shells)
        return self._min_height

    @property
    def spanu(self):
        if self._span is None:
            self._span = self.bbox.width / (len(self.shells) - 1)
        return self._span

    @property
    def spanv(self):
        if self._span is None:
            self._span = self.bbox.height / (len(self.shells) - 1)
        return self._span

    @property
    def shell_sum(self):
        if self._shell_sum is None:
            self._shell_sum = sum(getattr(shell.bounding_box, self.calc_dir)
                                  for shell in self.shells)
        return self._shell_sum


@undoable
@repeatable
def align(mode):
    """
    Aligns uvs given mode.
    """
    try:
        align_mode = {
            'maxu': AlignUV.MAX_U,
            'minu': AlignUV.MIN_U,
            'maxv': AlignUV.MAX_V,
            'minv': AlignUV.MIN_V,
            'centeru': AlignUV.CENTER_U,
            'centerv': AlignUV.CENTER_V,
        }[mode]
    except KeyError:
        return logger.warn('{} is not a valid align mode.'.format(mode))

    align = AlignUV(align_mode)
    for shell in align.shells:
        shell.translate(**_get_align_kwargs(shell, align))


@undoable
@repeatable
def scalefit(mode):
    """
    Docstring
    """
    try:
        scale_mode = {
            'maxu': AlignUV.SCALE_MAX_U,
            'minu': AlignUV.SCALE_MIN_U,
            'maxv': AlignUV.SCALE_MAX_V,
            'minv': AlignUV.SCALE_MIN_V,
        }[mode]
    except KeyError:
        return logger.warn('{} is not a valid scalefit mode.'.format(mode))

    align = AlignUV(scale_mode)
    for shell in align.shells:
        u, v = shell.bounding_box.center.u, shell.bounding_box.center.v
        shell.translate(pu=u, pv=v, **_get_align_kwargs(shell, align))


def _get_align_kwargs(shell, align):
    return {
        align.MAX_U: {'u': align.bbox.max.u - shell.bounding_box.max.u},
        align.MIN_U: {'u': align.bbox.min.u - shell.bounding_box.min.u},
        align.MAX_V: {'v': align.bbox.max.v - shell.bounding_box.max.v},
        align.MIN_V: {'v': align.bbox.min.v - shell.bounding_box.min.v},

        align.CENTER_U: {'u': align.bbox.center.u - shell.bounding_box.center.u},
        align.CENTER_V: {'v': align.bbox.center.v - shell.bounding_box.center.v},

        align.SCALE_MAX_U: {'su': align.max_width / shell.bounding_box.width},
        align.SCALE_MIN_U: {'su': align.min_width / shell.bounding_box.width},
        align.SCALE_MAX_V: {'sv': align.max_height / shell.bounding_box.height},
        align.SCALE_MIN_V: {'sv': align.min_height / shell.bounding_box.height},
    }[align.mode]


@undoable
@repeatable
def distribute(mode):
    """
    docstring.
    """
    try:
        dist_mode = {
            'u': AlignUV.DISTRIBUTE_U,
            'v': AlignUV.DISTRIBUTE_V,
        }[mode]
    except KeyError:
        return logger.warn('{} is not a valid distribute mode.'.format(mode))

    align = AlignUV(dist_mode)
    for idx, shell in enumerate(align.shells):
        if idx == 0:
            distance = getattr(align.bbox.min, mode)
            continue
        elif idx == len(align.shells) - 1:
            continue

        distance += align.spanu if mode == 'u' else align.spanv
        translate_value = distance - getattr(shell.bounding_box.center, mode)
        shell.translate(**{mode: translate_value})


@undoable
@repeatable
def space(mode, space=0.04):
    try:
        space_mode = {
            'u': AlignUV.SPACE_U,
            'v': AlignUV.SPACE_V,
        }[mode]
    except KeyError:
        return logger.warn('{} is not valid space mode.'.format(mode))

    align = AlignUV(space_mode)

    spacing = (space * (len(align.shells) - 1) + align.shell_sum) / 2
    calculated_space = getattr(align.bbox.center, mode) - spacing

    for shell in align.shells:
        offset = shell.bounding_box
        shell.translate(**{mode: calculated_space - getattr(offset.min, mode)})

        max_ = getattr(offset.max, mode)
        min_ = getattr(offset.min, mode)
        calculated_space += space + (max_ - min_)


@undoable
@repeatable
def tear_off():
    """
    Creates a new uv shell from selected faces.
    """
    s = mampy.selected()

    for comp in s.itercomps():
        if not comp.is_face():
            continue

        edges = comp.to_edge(border=True)
        cmds.polyMapCut(list(edges))
    cmds.select(list(s))


@undoable
@repeatable
def orient():
    """
    Orients shell to closest 90 degree angle on selection.
    """
    s = mampy.ordered_selection(fl=True)
    if not s:
        return logger.warn('Nothing selected.')

    if s[0].is_map():
        new, current = SelectionList(), list(s)
        print current
        for pair in grouped(current, 2):
            new.append(MeshMap(pair))
        s = new

    for comp in s.itercomps():

        if not comp.is_map():
            comp = comp.to_map()
        if len(comp) > 2:
            logger.warn('Does not support border edges or multiple selections.')
            continue

        line = Line2D(*comp.points)
        shell = comp.get_uv_shell()
        shell.translate(a=line.angle, pu=line.center.u, pv=line.center.v)


@undoable
@repeatable
def translate(u=0.0, v=0.0):
    for shell in get_shells():
        shell.translate(u=u, v=v)


@undoable
@repeatable
def rotate(angle):
    for shell in get_shells():
        point = shell.bounding_box.center
        shell.translate(angle=angle, pu=point.u, pv=point.v)


@undoable
@repeatable
def mirror(mode):
    try:
        mirror = {
            'u': 'su',
            'v': 'sv',
        }[mode]
    except KeyError:
        return logger.warn('{} is not a valid mode for mirror'.format(mode))

    for shell in get_shells():
        point = shell.bounding_box.center
        shell.translate(**{mirror: -1, 'pu': point.u, 'pv': point.v})

if __name__ == '__main__':
    set_texel_density(shell=False)
