"""
Contains selection tools for working with meshes and surfaces.
"""
import sys
import logging
import collections

from PySide import QtCore, QtGui

import maya.api.OpenMaya as api
from maya import cmds, mel
from maya.OpenMaya import MGlobal

import mampy
from mampy.utils import undoable, repeatable, get_object_under_cursor, DraggerCtx, mvp
from mampy.components import Component, MeshPolygon
from mampy.selections import SelectionList
from mampy.exceptions import InvalidSelection

from mamtools.viewport_masks import VERT, EDGE, FACE, MAP, set_mask


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

optionvar = mampy.optionVar()


def set_selection_mask(mask):
    set_mask(*globals()[mask.upper()].masks)


@undoable
@repeatable
def adjacent(expand=True):
    """Grow and remove previous selection to get adjacent selection.

    .. todo:: make contractable
    """
    selected = mampy.selected()
    components = list(selected.itercomps())
    if not selected or not components:
        raise InvalidSelection('Select valid mesh component.')

    toggle_components = SelectionList()
    for component in components:
        try:
            adjacent_selection = {
                api.MFn.kMeshPolygonComponent: component.to_edge().to_face(),
                api.MFn.kMeshEdgeComponent: component.to_vert().to_edge(),
                api.MFn.kMeshVertComponent: component.to_edge().to_vert(),
                api.MFn.kMeshMapComponent: component.to_edge().to_map(),
            }[component.type]
            toggle_components.extend(adjacent_selection)
        except KeyError:
            raise InvalidSelection('Select component from mesh object.')

    cmds.select(list(toggle_components), toggle=True)


@undoable
@repeatable
def clear_mesh_or_loop():
    """Clear mesh or loop under mouse."""
    preselect_hilite = mampy.ls(preSelectHilite=True)[0]

    if preselect_hilite.type == api.MFn.kEdgeComponent:
        cmds.polySelect(preselect_hilite.dagpath,
                        edgeLoop=preselect_hilite.index, d=True)
    elif preselect_hilite.type == api.MFn.kMeshPolygonComponent:
        cmds.polySelect(preselect_hilite.dagpath,
                        extendToShell=preselect_hilite.index, d=True)


def toggle_mesh_under_cursor():
    """Toggle mesh object under cursor."""
    preselect = mampy.ls(preSelectHilite=True)
    if not preselect:
        under_cursor_mesh = get_object_under_cursor()
        if under_cursor_mesh is None:
            raise InvalidSelection('No valid selection')
        obj = mampy.get_node(under_cursor_mesh)
    else:
        obj = preselect.pop()

    if issubclass(obj.__class__, Component):
        component = obj.get_complete()
        if component.node in mampy.selected():
            cmds.select(list(component), d=True)
        else:
            dagpath = mampy.get_node(component.dagpath)
            cmds.hilite(dagpath.get_transform().name, unHilite=True)
        return
    else:
        cmds.select(obj.name, toggle=True)
        if obj.name in mampy.selected():
            if cmds.selectMode(q=True, component=True):
                cmds.hilite(obj.name)


class coplanar(DraggerCtx):
    """
    Class for selecting coplanar faces.
    """

    CONTIGUOUS, OBJECT, HILITED = range(3)
    CONTEXT_NAME = 'mamtools_coplanar_context'
    OPTIONVAR_NAME = 'mamtools_coplanar_threshold'

    def __init__(self, mode, context=False):
        super(coplanar, self).__init__(self.CONTEXT_NAME)

        self.mode = mode
        self.default = self.threshold
        self.value = self.threshold

        # properties
        self._slist = None
        self._normal = None
        self._label = None
        self._mesh_vectors = None
        self._comp_indices = None

        if mode == self.HILITED:
            self._setup_hilited()
        elif mode == self.OBJECT or mode == self.CONTIGUOUS:
            self._setup_contiguous_object()

        if context:
            self.run()
        else:
            self.tear_down()

    @property
    def mesh_vectors(self):
        if self._mesh_vectors is None:
            self._mesh_vectors = collections.defaultdict(
                 lambda: collections.defaultdict(list)
         )
        return self._mesh_vectors

    @property
    def comp_indices(self):
        if self._comp_indices is None:
            self._comp_indices = collections.defaultdict(set)
        return self._comp_indices

    @property
    def slist(self):
        if self._slist is None:
            self._slist = mampy.selected()
            if not self._slist:
                raise TypeError('Invalid selection, select mesh face.')
        return self._slist

    @property
    def normal(self):
        if self._normal is None:
            comp = self.slist.itercomps().next()
            if not comp.is_face():
                raise TypeError('Invalid selection, select mesh face.')

            self._normal = comp.mesh.getPolygonNormal(
                comp.index, api.MSpace.kWorld
            )
        return self._normal

    @property
    def threshold(self):
        return optionvar.get(self.OPTIONVAR_NAME, 0.1)

    @threshold.setter
    def threshold(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError('Value needs to be int or float.')
        optionvar[self.OPTIONVAR_NAME] = value

    @property
    def label(self):
        if self._label is None:
            text = 'threshold: {}'.format(self.threshold)
            self._label = QtGui.QLabel(text)
            self._label.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint |
                                       QtCore.Qt.FramelessWindowHint)
            self._label.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        return self._label

    @classmethod
    def contiguous(cls, context=False):
        return cls(cls.CONTIGUOUS, context)

    @classmethod
    def hilited(cls, context=False):
        return cls(cls.HILITED, context)

    @classmethod
    def object(cls, context=False):
        return cls(cls.OBJECT, context)

    def _setup_hilited(self):
        cmds.polySelectConstraint(
            type=0x0008,
            mode=3,
            orient=1,
            orientbound=[0, self.threshold],
            orientaxis=self.normal
        )

    def _setup_contiguous_object(self):
        result = SelectionList()
        for comp in self.slist.itercomps():
            get_normal = comp.mesh.getPolygonNormal

            if self.mode == self.OBJECT:
                for idx in comp.get_mesh_shell().indices:
                    # Create dict object with Vector as key
                    n = get_normal(idx, api.MSpace.kWorld)
                    self.mesh_vectors[comp][tuple(n)].append(idx)

                    if self.normal.isEquivalent(n, self.threshold):
                        comp.add(idx)
            else:
                matching = self._get_contiguous(comp)
                self.comp_indices[comp].update(matching)
                comp.add(matching)

            result.append(comp)
        cmds.select(list(result))

    def _get_contiguous(self, comp):
        get_normal = comp.mesh.getPolygonNormal
        matching = set()
        while True:
            found_matching = False

            comp = comp.to_vert().to_face()
            for idx in comp.indices:
                if idx in matching:
                    continue

                n = get_normal(idx, api.MSpace.kWorld)
                if n.isEquivalent(self.normal, self.value * 2):
                    matching.add(idx)
                    found_matching = True

            if found_matching:
                comp = comp.new()
                comp.add(matching)
            else:
                break
        return matching

    def setup(self):
        self.min, self.max = 0, 1
        self.label.show()

    def tear_down(self):
        if self.mode == self.HILITED:
            cmds.polySelectConstraint(disable=True)
        self.label.close()

    def drag(self):
        super(coplanar, self).drag()

        view = mvp.Viewport.active()
        pos = (view.widget.width() / 2, view.widget.height() / 5)
        pos = view.widget.mapToGlobal(QtCore.QPoint(*pos))
        self.label.move(pos)
        self.label.setText('threshold: {:4.3f}'.format(self.value))
        self.label.setMinimumSize(self.label.minimumSizeHint())

    def drag_left(self):
        change = (self.dragPoint[0] - self.anchorPoint[0]) * 0.001
        self.value = change + self.default
        if self.value < self.min:
            self.value = self.min
        elif self.value > self.max:
            self.value = self.max

        if self.mode == self.HILITED:
            cmds.polySelectConstraint(orientbound=[0, self.value * 180])
        elif self.mode == self.OBJECT:
            self._update_object()
        elif self.mode == self.CONTIGUOUS:
            self._update_contiguous()

    def _update_contiguous(self):
        result = SelectionList()
        for comp in self.comp_indices:
            new = comp.new()
            new.add(self._get_contiguous(comp))
            result.append(new)
        cmds.select(list(result))

    def _update_object(self):
        result = SelectionList()
        for comp, normal_indices in self.mesh_vectors.iteritems():
            new = comp.new()
            for n in normal_indices:
                if self.normal.isEquivalent(api.MVector(n), self.value * 2.01):
                    new.add(normal_indices[n])
            result.append(new)
        cmds.select(list(result))

    def release(self):
        self.default = self.value


@undoable
def convert(comptype, **convert_arguments):
    """
    Convert current selection to given comptype.
    """
    ComponentType = collections.namedtuple('ComponentType', ('type', 'function'))
    convert_mode = {
        'vert': ComponentType(api.MFn.kMeshVertComponent, 'to_vert'),
        'edge': ComponentType(api.MFn.kMeshEdgeComponent, 'to_edge'),
        'face': ComponentType(api.MFn.kMeshPolygonComponent, 'to_face'),
        'map': ComponentType(api.MFn.kMeshMapComponent, 'to_map'),
    }[comptype]

    selected, converted = mampy.selected(), SelectionList()
    # s, cl = mampy.selected(), mampy.SelectionList()
    if not selected:
        raise InvalidSelection('Nothing Selected.')

    for component in selected.itercomps():
        if component.type == convert_mode.type:
            return logger.info('{} already active component type.'.format(comptype))

        # Special treatment when converting vert -> edge
        elif ('border' not in convert_arguments and
                component.type == api.MFn.kMeshVertComponent and
                convert_mode.type == api.MFn.kMeshEdgeComponent):
            convert_arguments.update({'internal': True})

        converted.append(getattr(component, convert_mode.function)(**convert_arguments))

    set_selection_mask(comptype)
    cmds.select(list(converted))


@undoable
@repeatable
def flood():
    """Get contiguous components from current selection."""
    selected = mampy.selected()
    if not selected:
        raise InvalidSelection('Select mesh component')

    # extend selected with ``mampy.Component`` objects.
    selected.extend([comp.get_mesh_shell() for comp in selected.itercomps()])
    cmds.select(list(selected))


class fill(object):

    UVSET_NAME = 'mamtools_fill_uvset'
    TOOLKIT_CTX_NAME = 'ModelingToolkitSuperCtx'
    TOOLKIT_TGL_CMD = 'dR_mtkToolTGL'

    def __init__(self):

        self._slist = None
        self._dagpath = None
        self._culling = None
        self._toolkit = None
        self._scriptjob = None

        self.setup()

    @property
    def slist(self):
        if self._slist is None:
            self._slist = mampy.selected()
            if not self._slist and not self._slist.is_edge():
                raise TypeError('Select a closed edge loop.')
        return self._slist

    @property
    def dagpath(self):
        if self._dagpath is None:
            self._dagpath = self.slist.itercomps().next().dagpath
        return self._dagpath

    @property
    def culling(self):
        if self._culling is None:
            self._culling = cmds.polyOptions(
                self.dagpath, q=True, wireBackCulling=True
            )
        return self._culling

    @property
    def toolkit(self):
        if self._toolkit is None:
            self._toolkit = cmds.currentCtx(q=True) == self.TOOLKIT_CTX_NAME
        return self._toolkit

    def toggle_culling(self):
        if self.culling:
            cmds.polyOptions(self.dagpath, backCulling=True)

    def toggle_toolkit(self):
        if self.toolkit:
            mel.eval(self.TOOLKIT_TGL_CMD)

    def tear_down(self):
        cmds.polySelectConstraint(disable=True)
        cmds.polyUVSet(self.dagpath, delete=True, uvSet=self.UVSET_NAME)

        if self.culling:
            cmds.polyOptions(self.dagpath, wireBackCulling=True)

        if self.toolkit:
            mel.eval(self.TOOLKIT_TGL_CMD)

        cmds.undoInfo(closeChunk=True)

    def setup(self):
        cmds.undoInfo(openChunk=True)
        self.toggle_culling()
        self.toggle_toolkit()

        self._polygon_projection()
        self._selection_mask()
        self._script_job()

    def _polygon_projection(self):
        faces = MeshPolygon.create(self.dagpath)
        faces = faces.get_complete()
        cmds.polyProjection(
            list(faces),
            type='planar',
            uvSetName=self.UVSET_NAME,
            createNewMap=True,
            mapDirection='c',
            insertBeforeDeformers=True,
        )
        cmds.polyUVSet(self.dagpath, currentUVSet=True, uvSet=self.UVSET_NAME)
        cmds.polyMapCut(list(self.slist))

    def _selection_mask(self):
        mask = mampy.get_active_mask()
        mask.set_mode(mask.kSelectComponentMode)
        mask.set_mask(mask.kSelectMeshFaces)
        cmds.select(cl=True)
        cmds.polySelectConstraint(type=0x0008, shell=True, m=1)

    def _script_job(self):
        if self._scriptjob is None:
            self._scriptjob = cmds.scriptJob(
                event=['SelectionChanged', self.tear_down],
                runOnce=True,
            )
        return self._scriptjob


@undoable
@repeatable
def inbetween():
    """Select components between the last two selections."""
    slist = mampy.ordered_selection(-2)
    if not slist or not len(slist) == 2:
        return logger.warn('Invalid selection, select two mesh components.')

    comptype = slist.itercomps().next().type
    indices = [c.index for c in slist.itercomps()]

    if (comptype in [
            api.MFn.kMeshPolygonComponent,
            api.MFn.kMeshEdgeComponent,
            api.MFn.kMeshVertComponent]):
        # check if a edge ring can be selected.
        if (comptype == api.MFn.kMeshEdgeComponent and
                cmds.polySelect(q=True, edgeRingPath=indices)):
            inbetween = cmds.polySelect(q=True, ass=True, edgeRingPath=indices)
        else:
            inbetween = cmds.polySelectSp(list(slist), q=True, loop=True)
    elif comptype == api.MFn.kMeshMapComponent:
        path = cmds.polySelect(q=True, ass=True, shortestEdgePathUV=indices)
        inbetween = cmds.polyListComponentConversion(path, tuv=True)

    cmds.select(inbetween, add=True)


@undoable
@repeatable
def invert(shell=False):
    """
    Invert selection.

    If shell is active but there are no selections, script assumes we
    want a full invert.

    .. note:: If current selection mask is *object* and there are no
        selections there is no way that I know of to find out the active
        component type.
    """
    slist, hilited = mampy.selected(), mampy.ls(hl=True)
    smask = mampy.get_active_mask()
    ctype = None

    # Try object invert
    if smask.mode == MGlobal.kSelectObjectMode and not hilited:
        dagobjs = cmds.ls(visible=True, assemblies=True)
        if not dagobjs:
            logger.warn('Nothing to invert.')
        else:
            cmds.select(dagobjs, toggle=True)
        return

    # set up component invert
    if smask.mode == MGlobal.kSelectObjectMode and not slist:
        return logger.warn('Switch selection mask from object to component.')
    elif slist:
        ctype = slist.itercomps().next().type
    else:
        for m in smask:
            try:
                ctype = {
                    smask.kSelectMeshVerts: api.MFn.kMeshVertComponent,
                    smask.kSelectMeshEdges: api.MFn.kMeshEdgeComponent,
                    smask.kSelectMeshFaces: api.MFn.kMeshPolygonComponent,
                    smask.kSelectMeshUVs: api.MFn.kMeshMapComponent,
                }[m]
            except KeyError:
                continue
            else:
                break

    # perform component invert
    t = SelectionList()
    if not shell or not slist:
        for dp in hilited:
            t.extend(Component.create(dp, ctype).get_complete())
    else:
        for comp in slist.copy().itercomps():
            t.extend(comp.get_mesh_shell() if shell else comp.get_complete())

    # for some reason the tgl keyword makes cmds.select really fast.
    cmds.select(list(t), tgl=True)


@undoable
@repeatable
def nonquads(ngons=True, query=False):
    """
    Select all nonquads from an object.
    """
    type_ = 3 if ngons else 1

    if query:
        selected = mampy.selected()

    cmds.selectMode(component=True)
    cmds.selectType(facet=True)

    cmds.polySelectConstraint(mode=3, t=0x0008, size=type_)
    cmds.polySelectConstraint(disable=True)
    ngons = mampy.selected()

    if query:
        cmds.select(list(selected))
        return ngons
    sys.stdout.write(str(len(ngons)) + ' N-Gon(s) Selected.\n')


@undoable
@repeatable
def traverse(expand=True, mode='normal'):
    if mode == 'normal':
        if expand:
            return mel.eval('PolySelectTraverse(1)')
        return mel.eval('PolySelectTraverse(2)')
    elif mode == 'adjacent':
        if expand:
            return adjacent(expand)
        return adjacent


if __name__ == '__main__':
    invert(True)
