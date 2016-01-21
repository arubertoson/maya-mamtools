"""
Various utility functions that doesn't really fit anywhere else.
"""
import math
import logging

import maya.api.OpenMaya as api

import maya.cmds as cmds
import maya.mel as mel

import mampy


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def tool_select(release=False):
    if release:
        mel.eval('dR_DoCmd("selectRelease");')
    else:
        mel.eval('dR_DoCmd("selectPress");')


class ComponentKeep(object):
    """
    Saves component selections when switching type.

    This is redundant, better to use mayas built in features. Keepsake
    for inspiration to solve other problems.

    ..todo:
        * Check objects selected to avoid selection stuff you dont want.
    """

    OPTVAR = 'component_selection_keep'

    state = True
    active = OPTVAR + '_active'
    vert = OPTVAR + '_vert'
    edge = OPTVAR + '_edge'
    face = OPTVAR + '_face'
    map = OPTVAR + '_uvmap'

    def __init__(self, comp_type):
        self.comp_type = comp_type

        # make sure optionVars exists
        for i in [self.vert, self.edge, self.face, self.map, self.active]:
            if not cmds.optionVar(exists=i):
                cmds.optionVar(sv=(i, ''))

    def __enter__(self):
        """
        Checks current selection and saves the selection string to a
        optionVar representing the active component.
        """
        s = mampy.selected()
        active = self.dispatch(cmds.optionVar(q=self.active))
        cmds.optionVar(sv=(active, '-'.join(list(s))))
        return self

    def __exit__(self, t, value, tb):
        """
        Get selection string list from given comp type then select or
        clear depending on the result.
        """
        selection_str = cmds.optionVar(q=self.dispatch(self.comp_type))
        prev_selection = selection_str.split('-')

        if prev_selection and not prev_selection[0] == '':
            cmds.select(prev_selection, r=True)
        else:
            cmds.select(cl=True)

        cmds.optionVar(iv=(self.active, self.comp_type))

    def dispatch(self, t):
        try:
            return {
                api.MFn.kMeshVertComponent: self.vert,
                api.MFn.kMeshEdgeComponent: self.edge,
                api.MFn.kMeshPolygonComponent: self.face,
                api.MFn.kMeshMapComponent: self.map,
            }[t]
        except KeyError:
            return None


def get_global_var(var):
    """
    Return a mel global variable given var.
    """
    return mel.eval('$mampytmp = ${}'.format(var))


def select_mode(type_, toggle=True):
    """
    Selection mode setter, given component or objects set Maya selection
    masks.
    """
    def trim_dict():
        new_dict = {}
        for k, v in kwargs.iteritems():
            if k.startswith(type_) or k.lower().endswith(type_):
                new_dict[k] = v
                return new_dict

    vert = {
        'vertex': True,
        'controlVertex': True,
        'latticePoint': True,
        }
    edge = {
        'edge': True,
        'surfaceEdge': True,
        }
    face = {
        'facet': True,
        'surfaceFace': True,
        }
    meshuv = {
        'polymeshUV': True,
        'surfaceUV': True,
        }
    kwargs = locals()[type_]
    mode = trim_dict()
    if (cmds.selectMode(q=True, component=True) and
            cmds.selectType(q=True, **mode)):
        cmds.selectMode(object=True)
        cmds.selectType(allObjects=True, allComponents=False)
    else:
        cmds.selectMode(component=True)
        cmds.selectType(allComponents=False)
        cmds.selectType(**kwargs)


def convert(comptype, **kwargs):
    """
    Convert current selection to given comptype.
    """
    mode = {
        'vert': (api.MFn.kMeshVertComponent, 'to_vert'),
        'edge': (api.MFn.kMeshEdgeComponent, 'to_edge'),
        'face': (api.MFn.kMeshPolygonComponent, 'to_face'),
        'map': (api.MFn.kMeshMapComponent, 'to_map'),
    }[comptype]

    s, cl = mampy.selected(), mampy.SelectionList()
    if not s:
        return logger.warn('Nothing Selected.')

    for comp in s.itercomps():
        if comp.type == mode[0]:
            return
        # Special case for vert -> edge
        elif ('border' not in kwargs and
                comp.type == api.MFn.kMeshVertComponent and
                mode[0] == api.MFn.kMeshEdgeComponent):
            kwargs.update({'internal': True})

        cl.append(getattr(comp, mode[1])(**kwargs))

    select_mode(comptype if not comptype == 'map' else 'meshuv')
    cmds.select(list(cl))


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


@mampy.history_chunk()
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


@mampy.history_chunk()
def bake_pivot():
    """
    Bake modified manipulator pivot onto object.
    """
    s = mampy.ordered_selection(tr=True, l=True)
    dag = s.pop(len(s)-1)
    out_idx = mampy.get_outliner_index(dag)
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

if __name__ == '__main__':

    print get_pane_size(cmds.getPanel(underPointer=True))



# def uvShellHardEdges():
#     '''
#     Sets uv border edges on a mesh has hard, and everythign else as soft.
#     '''
#     objList = cmds.ls(sl=True, o=True)
#     finalBorder = []

#     for subObj in objList:
#         cmds.select(subObj, r=True)
#         cmds.polyNormalPerVertex(ufn=True)
#         cmds.polySoftEdge(subObj, a=180, ch=1)
#         cmds.select(subObj + '.map[*]', r=True)

#         polySelectBorderShell(borderOnly=True)

#         uvBorder = cmds.polyListComponentConversion(te=True, internal=True)
#         uvBorder = cmds.ls(uvBorder, fl=True)

#         for curEdge in uvBorder:
#             edgeUVs = cmds.polyListComponentConversion(curEdge, tuv=True)
#             edgeUVs = cmds.ls(edgeUVs, fl=True)

#             if len(edgeUVs) > 2:
#                 finalBorder.append(curEdge)

#         cmds.polySoftEdge(finalBorder, a=0, ch=1)

#     cmds.select(objList)
