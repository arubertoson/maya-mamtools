import maya.api.OpenMaya as api
import maya.cmds as cmds

import mampy


import maya.mel as mel


def get_global_var(var):
    return mel.eval("$mampytmp ="+ var)


def set_pivot():
    s = mampy.selected()

    # origo_vec = api.MVector(1, 0, 1)
    # for each in s.iterdags():
        # print cmds.manipMoveContext('Move', e=True, orientTowards=[10, 49, 49])
        # print each.name
        # print cmds.manipPivot(each.name, q=True, p=True)
    # for each in s.iterdags():
        # print each.rotatePivot.get()


# class Pivot(object):

    # def __init__(self, obj):
        # self.pivot = obj.



# class pivot(object):




if __name__ == '__main__':

    # t = [0.18677182069146364, 1.344467805788809, -0.6292614505580241]


    # cmds.manipMoveContext('Move', e=True, mode=6)
    # cmds.manipMoveContext('Move', e=True, oa=t)

    # create script Ctx
    cmds.scriptCtx()
    cmds.setToolTo()

    # create script job
    cmds.scriptJob()

    # for i in s.itercomps():

        # bboxc = list(i.bounding_box.center)[:-1]
        # t = cmds.spaceLocator(name='test', p=bboxc)
    #     node = mampy.DagNode(t.pop())
    #     cmds.xform(node.name, cp=True)

        # verts = i.to_vert()
        # n = verts.mesh.getVertexNormals(True, api.MSpace.kWorld)
        # tmpn = api.MVector()
        # for v in verts.indices:
            # tmpn += api.MVector(n[v])

        # normal = tmpn/len(verts)
    #     # new_n = i.bounding_box.center + normal
    #     # print new_n
    #     # nnode = mampy.DagNode(cmds.spaceLocator(name='ntest', p=list(new_n)[:-1]).pop())
    #     # cmds.xform(nnode.name, cp=True)

    #     # cmds.aimConstraint(nnode.name, node.name, n='MTool')
    #     # cmds.delete(nnode.name)
        # cmds.manipMoveContext('Move', e=True, mode=6)
        # cmds.manipMoveContext('Move', e=True, aa=normal)



        # i.mesh.getFaceNormalIds()


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
