import logging

import maya.cmds as cmds
import maya.api.OpenMaya as api

import mampy

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@mampy.history_chunk()
def bevel():
    s = mampy.selected()
    for comp in s.itercomps():
        cmds.select(list(comp))
        try:
            func = {
                api.MFn.kMeshPolygonComponent: cmds.polyExtrudeFacet,
                api.MFn.kMeshEdgeComponent: cmds.polyExtrudeEdge,
                api.MFn.kMeshVertComponent: cmds.polyExtrudeVertex,
            }[comp.type]
            func(divisions=1)
        except KeyError:
            return logger.warn('{} is not support for extrude'.format(comp.type))
        finally:
            cmds.select(list(s))
    cmds.select(list(s))


def bridge():
    pass


def bevel():
    pass


@mampy.history_chunk()
def detach_mesh(extract=False):
    """
    Extracts or duplicat selected polygon faces.
    """
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing selected.')

    new = mampy.SelectionList()
    for comp in s.itercomps():
        if not comp.is_face():
            continue

        # Duplicate
        trans = mampy.DagNode.from_object(comp.dagpath.transform())
        name = trans.name + ('_ext' if extract else '_dup')
        dupdag = cmds.duplicate(str(comp.dagpath), n=name).pop(0)

        # Delete children transforms
        children = cmds.listRelatives(dupdag, type='transform', f=True)
        if children is not None:
            cmds.delete(children)

        # Delete unused faces
        if extract:
            cmds.polyDelFacet(list(comp))

        dcomp = mampy.MeshPolygon.create(dupdag)
        dcomp.add(comp.indices)
        cmds.polyDelFacet(list(dcomp.toggle()))

        # Select
        cmds.hilite(str(dcomp.dagpath))
        new.append(dcomp.get_complete())

    cmds.select(list(new), r=True)


def detach(hierarchy=False, extract=False):
    s = mampy.selected()
    if not s:
        return logger.warn('Nothing Selected.')
    s = s[0]
    if s.type == api.MFn.kMeshPolygonComponent:
        detach_mesh(extract)
    elif s.type in [api.MFn.kTransform]:
        cmds.duplicate(rr=True) #parentOnly=hierarchy)


@mampy.history_chunk()
def combine_separate():
    """
    Depending on selection will combine or separate objects.

    Script will try to retain the transforms and outline position of the
    first object selected.

    """
    def clean_up_object(dag):
        """
        Cleans up after `polyUnite` / `polySeparate`
        """
        if dag.get_parent() is not None:
            dag.set_parent(parent)
        trns = dag.get_transform()

        cmds.reorder(dag.name, f=True)
        cmds.reorder(dag.name, r=outliner_index)
        trns.set_pivot(pivot)

        dag.rotate.set(*src_trns.rotate)
        dag.scale.set(*src_trns.scale)
        return dag.name

    s, hl = mampy.ordered_selection(tr=True, l=True), mampy.ls(hl=True)
    if len(s) == 0:
        if len(hl) > 0:
            s = hl
        else:
            return logger.warn('Nothing Selected.')

    dag = s.pop()
    logger.debug(dag)
    parent = dag.get_parent()

    # Get origin information from source object
    trns = dag.get_transform()
    src_trns = trns.get_transforms()
    pivot = trns.get_rotate_pivot()

    if s:
        logger.debug('Combining Objects.')
        for i in s.iterdags():
            if dag.is_child_of(i):
                raise mampy.InvalidSelection('Cannot parent an object to one '
                                             'of its children')
            if dag.is_parent_of(i):
                continue
            i.set_parent(dag)

    # Now we can check source objects position in outliner and
    # un-rotate/un-scale
    outliner_index = mampy.get_outliner_index(dag)
    dag.rotate.set(0, 0, 0)
    dag.scale.set(1, 1, 1)

    # Perform combine or separate and clean up objects and leftover nulls.
    if s:
        new_dag = mampy.DagNode(cmds.polyUnite(dag.name, list(s), ch=False)[0])
        cmds.select(cmds.rename(clean_up_object(new_dag), dag.name), r=True)
    else:
        logger.debug('Separate Objects.')
        new_dags = mampy.SelectionList(cmds.polySeparate(dag.name, ch=False))
        for i in new_dags.copy().iterdags():
            cmds.rename(clean_up_object(i), dag.name)
        cmds.delete(dag.name)  # Delete leftover group.
        cmds.select(list(new_dags), r=True)


if __name__ == '__main__':
    detatch()
    # dag = mampy.selected().pop(0)
    # print cmds.parent(dag.name, world=True)

    # transform = dag.get_transform()
    # r = transform.get_rotate()
    # dag.rotate.set(0, 0, 0)


    # get pivot position, save rotation and scale values.
    # check for constraints in hierarchy and unparent.
    # parent everything under the first and un-rotate/un-scale
    # check incoming connections
    # check for outgoing connections

