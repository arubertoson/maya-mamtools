"""
Various utility functions that doesn't really fit anywhere else.
"""
import maya.api.OpenMaya as api
import maya.cmds as cmds
import maya.mel as mel

import mampy


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


def select_mode(type):
    """
    Selection mode setter, given component or objects set Maya selection
    masks.
    """
    if type in ['vert', 'edge', 'face']:
        mode = {
            'vert': 'dR_modeVert',
            'edge': 'dR_modeEdge',
            'face': 'dR_modePoly',
        }[type]
        mel.eval("{}".format(mode))
    elif type == 'map':
        if (cmds.selectMode(q=True, component=True) and
                cmds.selectType(q=True, puv=True)):
            cmds.selectMode(object=True)
            cmds.selectType(allObjects=True)
        else:
            mel.eval('dR_modeUV')


def convert(mode, **args):
    """
    Convert current selection to given mode.
    """
    s, cl = mampy.selected(), mampy.SelectionList()
    for i in s.itercomps():
        if mode == 'vert':
            cl.append(i.to_vert(**args))
            select_mode('vert')
        elif mode == 'edge':
            cl.append(i.to_edge(**args))
            select_mode('edge')
        elif mode == 'face':
            cl.append(i.to_face(**args))
            select_mode('face')
        elif mode == 'map':
            cl.append(i.to_map(**args))
            select_mode('map')
    cmds.select(list(cl))


def set_pivot():
    pass
    # s = mampy.selected()
    # origo_vec = api.MVector(1, 0, 1)
    # for each in s.iterdags():
    #     print cmds.manipMoveContext('Move', e=True,
    #                                  orientTowards=[10, 49, 49])
    #     print each.name
    #     print cmds.manipPivot(each.name, q=True, p=True)
    # for each in s.iterdags():
    #     print each.rotatePivot.get()


if __name__ == '__main__':
    select_mode('map')
    # cmds.selectMode(object=True)
    # cmds.selectType(allObjects=True)

    # vertex_mask()
    # edge_mask()
    # s = mampy.selected()
    # print s.itercomps().next().typestr

    # fbx_batch_import('G:/wuncook/dlc/dlc14/data/characters/models/geralt/'
    #                  'armor/armor__skellige/export/dlc/dlc14/data/characters/'
    #                  'models/geralt/armor/armor__skellige/')
    # clean_empty_transforms()

    # t = [0.18677182069146364, 1.344467805788809, -0.6292614505580241]

    # cmds.manipMoveContext('Move', e=True, mode=6)
    # cmds.manipMoveContext('Move', e=True, oa=t)

    # create script Ctx
    # cmds.scriptCtx()
    # cmds.setToolTo()

    # create script job
    # cmds.scriptJob()

    # for i in s.itercomps():

    #     bboxc = list(i.bounding_box.center)[:-1]
    #     t = cmds.spaceLocator(name='test', p=bboxc)
    #     node = mampy.DagNode(t.pop())
    #     cmds.xform(node.name, cp=True)

    #     verts = i.to_vert()
    #     n = verts.mesh.getVertexNormals(True, api.MSpace.kWorld)
    #     tmpn = api.MVector()
    #     for v in verts.indices:
    #         tmpn += api.MVector(n[v])

    #     normal = tmpn/len(verts)
    #     # new_n = i.bounding_box.center + normal
    #     # print new_n
    #     # nnode = mampy.DagNode(cmds.spaceLocator(name='ntest',
    #                              p=list(new_n)[:-1]).pop())
    #     # cmds.xform(nnode.name, cp=True)

    #     # cmds.aimConstraint(nnode.name, node.name, n='MTool')
    #     # cmds.delete(nnode.name)
    #     cmds.manipMoveContext('Move', e=True, mode=6)
    #     cmds.manipMoveContext('Move', e=True, aa=normal)

    #     i.mesh.getFaceNormalIds()

    # move = mampy.mel_globals['gMove']
    # move_ctx = cmds.superCtx(move, q=True)
    # print move_ctx
    # vec = api.MVector()
    # for i in s.itercomps():

    #     mesh = i.mesh
    #     for idx in i.indices:
    #         mesh.getVertexNormal
    #         vec += mesh.getPolygonNormal(idx, api.MSpace.kWorld)

    # cmds.manipMoveContext('Move', e=True, aa=vec / 3)
    # print repr(n)

    # rotate = i.rotate.get().pop()
    # print rotate
    # print mel.eval('whatIs "Pivot"')
    # print move

    # m = mampy.MelGlobals()
    # print m['gMove']
    # print mel.eval('env')
    # move = get_global_var("$gMove")
    # movectx = cmds.superCtx(move, q=True)
    # print cmds.contextInfo(movectx, q=True, c=True)

    # print cmds.manipMoveContext(, e=True, ot=[-19.9, 11.2, 11.6])
