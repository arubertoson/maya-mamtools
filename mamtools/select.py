import logging
from collections import defaultdict

from PySide import QtGui, QtCore

import maya.cmds as cmds
import maya.api.OpenMaya as api
from maya.OpenMaya import MFn, MGlobal

import mampy

optionvar = mampy.optionVar()
logger = logging.getLogger(__name__)


def adjacent():
    """
    Grow and remove previous selection to get adjacent selection.
    """
    slist = mampy.selected()
    components = list(slist.itercomps())
    if not slist or not components:
        return logger.warn('Invalid selection, select valid mesh component.')

    tglist = mampy.SelectionList()
    for comp in components:
        try:
            adjacent_selection = {
                MFn.kMeshPolygonComponent: comp.to_edge().to_face(),
                MFn.kMeshEdgeComponent: comp.to_vert().to_edge(),
                MFn.kMeshVertComponent: comp.to_edge().to_vert(),
                MFn.kMeshMapComponent: comp.to_edge().to_map(),
            }[comp.type]
            tglist.extend(adjacent_selection)
        except KeyError:
            logger.warn('Invalid selection type, select component from mesh.')
            return

    cmds.select(list(tglist), toggle=True)


def clear():
    """
    Clear Selection.
    """
    slist = mampy.selected()
    if slist:
        return cmds.select(list(slist), clear=True)

    hlist = mampy.ls(hl=True)
    if hlist:
        cmds.hilite(list(hlist), toggle=True)
        mask = mampy.get_active_mask()
        mask.set_mode(mask.kSelectObjectMode)
        return
    cmds.select(clear=True)


def flood():
    """
    Get contiguous components from current selection.
    """
    slist = mampy.selected()
    if not slist:
        return logger.warn('Invalid selection, select mesh component')

    # extend slist with ``mampy.Component`` objects.
    slist.extend([comp.get_mesh_shell() for comp in slist.itercomps()])
    cmds.select(list(slist))


def inbetweent():
    """
    Select components between the last two selections.
    """
    slist = mampy.ordered_selection(-2)
    if not slist or not len(slist) == 2:
        return logger.warn('Invalid selection, select two mesh components.')

    comptype = slist.itercomps().next().type
    indices = [c.index for c in slist.itercomps()]

    if (comptype in [
        MFn.kMeshPolygonComponent,
        MFn.kMeshEdgeComponent,
            MFn.kMeshVertComponent]):
        # check if a edge ring can be selected.
        if (comptype == MFn.kMeshEdgeComponent and
                cmds.polySelect(q=True, edgeRingPath=indices)):
            inbetween = cmds.polySelect(q=True, ass=True, edgeRingPath=indices)
        else:
            inbetween = cmds.polySelectSp(list(slist), q=True, loop=True)
    elif comptype == MFn.kMeshMapComponent:
        path = cmds.polySelect(q=True, ass=True, shortestEdgePathUV=indices)
        inbetween = cmds.polyListComponentConversion(path, tuv=True)

    cmds.select(inbetween, add=True)


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
                    smask.kSelectMeshVerts: MFn.kMeshVertComponent,
                    smask.kSelectMeshEdges: MFn.kMeshEdgeComponent,
                    smask.kSelectMeshFaces: MFn.kMeshPolygonComponent,
                    smask.kSelectMeshUVs: MFn.kMeshMapComponent,
                }[m]
            except KeyError:
                continue
            else:
                break

    # perform component invert
    t = mampy.SelectionList()
    if not shell or not slist:
        for dp in hilited:
            t.extend(mampy.Component.create(dp, ctype).get_complete())
    else:
        for comp in slist.copy().itercomps():
            t.extend(comp.get_mesh_shell() if shell else comp.get_complete())

    # for some reason the tgl keyword makes cmds.select really fast.
    cmds.select(list(t), tgl=True)


class coplanar(mampy.DraggerCtx):
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
            self._mesh_vectors = defaultdict(lambda: defaultdict(list))
        return self._mesh_vectors

    @property
    def comp_indices(self):
        if self._comp_indices is None:
            self._comp_indices = defaultdict(set)
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

    def set_threshold(self, value):
        optionvar['mamtools_coplanar_threshold'] = value

    def _setup_hilited(self):
        cmds.polySelectConstraint(
            type=0x0008,
            mode=3,
            orient=1,
            orientbound=[0, self.threshold],
            orientaxis=self.normal
            )

    def _setup_contiguous_object(self):
        result = mampy.SelectionList()
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
                if n.isEquivalent(self.normal, self.value*2):
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

        view = mampy.Viewport.active()
        pos = (view.widget.width()/2, view.widget.height()/5)
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
            cmds.polySelectConstraint(orientbound=[0, self.value*180])
        elif self.mode == self.OBJECT:
            self._update_object()
        elif self.mode == self.CONTIGUOUS:
            self._update_contiguous()

    def _update_contiguous(self):
        result = mampy.SelectionList()
        for comp in self.comp_indices:
            new = comp.new()
            new.add(self._get_contiguous(comp))
            result.append(new)
        cmds.select(list(result))

    def _update_object(self):
        result = mampy.SelectionList()
        for comp, normal_indices in self.mesh_vectors.iteritems():
            new = comp.new()
            for n in normal_indices:
                if self.normal.isEquivalent(api.MVector(n), self.value*2.01):
                    new.add(normal_indices[n])
            result.append(new)
        cmds.select(list(result))

    def release(self):
        self.default = self.value


if __name__ == '__main__':
    coplanar.hilited()
