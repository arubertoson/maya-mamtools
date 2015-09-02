
import logging

import maya.cmds as cmds
from maya.OpenMaya import MFn, MGlobal

import mampy


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


if __name__ == '__main__':
    pass
