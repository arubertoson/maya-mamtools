import logging

import maya.cmds as cmds
from maya.api.OpenMaya import MFn

import mampy


logger = logging.getLogger(__name__)


__all__ = ['unhide_all', 'visibility_toggle', 'isolate_selected',
           'subd_toggle', 'subd_level', 'display_edges', 'display_vertex',
           'display_border_edges', 'display_map_border', 'display_textures',
           'display_xray', 'wireframe_shaded_toggle', 'wireframe_on_shaded',
           'wireframe_on_bg_objects', 'wireframe_backface_culling']


class IsolateSelected(object):
    """IsolateSelected class

    Additional functionality for standard isolate selection. Will isolate again
    if selection has changed.
    """

    instance = None

    def __init__(self):
        self.reset()

    @property
    def isoset(self):
        if self._isoset is None or self._isoset == '':
            self._isoset = cmds.isolateSelect(self.panel, q=True, vo=True)
        return self._isoset

    @property
    def panel(self):
        if self._panel is None:
            self._panel = cmds.getPanel(withFocus=True)
        return self._panel

    @property
    def state(self):
        return cmds.isolateSelect(self.panel, q=True, state=True)

    def toggle(self):
        if self.state:
            isoset = cmds.sets(self.isoset, q=True)
            selset = cmds.ls(sl=True)
            selset.extend(cmds.ls(hl=True))
            if set(isoset) == set(selset) or not cmds.ls(sl=True):
                cmds.isolateSelect(self.panel, state=False)
                self.reset()
                return
            else:
                return self.update()

        cmds.isolateSelect(self.panel, state=not(self.state))
        if self.state:
            self.update()
        else:
            self.reset()

    def update(self):
        try:
            cmds.sets(clear=self.isoset)
        except TypeError:
            pass
        finally:
            cmds.isolateSelect(self.panel, addSelected=True)
            hl = cmds.ls(hl=True)
            if hl:
                cmds.sets(hl, addElement=self.isoset)

    def reset(self):
        self._isoset = None
        self._panel = None


class SubDToggle(object):
    """SubDToggle class

    Clas for subd toggle functionality.
    """

    instance = None

    def __init__(self):
        self._meshes = None
        self._state = None

    def all(self, off=False):
        """SubD toggle all meshes off or on."""
        self._state = off
        self._meshes = self.get_meshes(all=True)
        self._toggle()

    def selected(self, hierarchy=False):
        """SubD toggle selected meshes."""
        self._hierarchy = hierarchy
        self._meshes = self.get_meshes(all=False)
        print self._meshes
        self._toggle()

    def level(self, level=1, all=True, hierarchy=False):
        """Change subd level on meshes."""
        self._hierarchy = hierarchy
        if all:
            meshes = self.get_meshes(all=True)
        else:
            meshes = self.get_meshes(all=False)

        for mesh in meshes.iterdags():
            mesh.smoothLevel.set(mesh.smoothLevel.get()+level)

    def get_meshes(self, all=True):
        """Return all SubD meshes in scene."""
        if all:
            return mampy.ls(type='mesh')
        else:
            if self._hierarchy:
                s = mampy.ls(sl=True, dag=True, type='mesh')
            else:
                s = mampy.SelectionList()
                for i in mampy.selected().iterdags():
                    shape = i.get_shape()
                    if shape is None:
                        continue
                    s.add(shape)

            # merge hilited
            hilited = mampy.ls(hl=True, dag=True, type='mesh')
            if hilited:
                s.extend(hilited)
            return s

    def _toggle(self):
        """Toggle specified meshes."""
        for mesh in self._meshes:
            if self._state is None:
                state = cmds.displaySmoothness(str(mesh), q=True, po=True).pop()
            else:
                state = self._state
            cmds.displaySmoothness(str(mesh), po=0 if state else 3)


def is_model_panel(panel):
    return cmds.getPanel(typeOf=panel) == 'modelPanel'


def unhide_all(unhide_types=None):
    """unhide all groups and mesh objects in the scene."""
    s = mampy.ls(transforms=True)
    for dag in s.iterdags():
        shape = dag.get_shape()
        if shape is None or shape.type == MFn.kMesh:
            dag.visibility.set(True)


def visibility_toggle():
    """Toggle visibility of selected objects."""
    s = mampy.selected()
    for dag in s.iterdags():
        dag.visibility.set(not(dag.visibility.get()))


def isolate_selected():
    """Toggles isolate selected."""
    if IsolateSelected.instance is None:
        IsolateSelected.instance = IsolateSelected()
    IsolateSelected.instance.toggle()


def subd_toggle(all=False, hierarchy=True, off=False):
    """Toggle subd display on meshes."""
    if SubDToggle.instance is None:
        SubDToggle.instance = SubDToggle()

    if all:
        SubDToggle.instance.all(off)
    else:
        SubDToggle.instance.selected(hierarchy=hierarchy)


def subd_level(level, all=True, hierarchy=True):
    """Change level of subd meshes."""
    if SubDToggle.instance is None:
        SubDToggle.instance = SubDToggle()

    if all:
        SubDToggle.instance.level(level)
    else:
        SubDToggle.instance.level(
            level,
            all=all,
            hierarchy=hierarchy
            )


def display_edges(show_hard=True):
    edge = {'hardEdge': True} if show_hard else {'softEdge': True}
    is_hard_edge = cmds.polyOptions(gl=True, q=True, **edge)
    if not all(is_hard_edge):
        cmds.polyOptions(gl=True, **edge)
    else:
        cmds.polyOptions(gl=True, allEdges=True)


def display_vertex():
    is_vertex_visible = cmds.polyOptions(gl=True, q=True, displayVertex=True)
    if not all(is_vertex_visible):
        cmds.polyOptions(gl=True, displayVertex=True)
    else:
        cmds.polyOptions(gl=True, displayVertex=False)


def display_border_edges():
    is_border_edge_visible = cmds.polyOptions(
        gl=True, q=True, displayBorder=True
    )
    if not all(is_border_edge_visible):
        cmds.polyOptions(gl=True, displayBorder=True)
    else:
        cmds.polyOptions(gl=True, displayBorder=False)


def display_map_border():
    is_map_border_visible = cmds.polyOptions(
        gl=True, q=True, displayMapBorder=True,
    )
    if not all(is_map_border_visible):
        cmds.polyOptions(gl=True, displayMapBorder=True)
    else:
        cmds.polyOptions(gl=True, displayMapBorder=False)


def display_textures():
    current_panel = cmds.getPanel(withFocus=True)
    if not is_model_panel(current_panel):
        cmds.warning('Panel must be modelpanel.')

    is_texture = cmds.modelEditor(current_panel, q=True, displayTextures=True)
    cmds.modelEditor(current_panel, e=True, displayTextures=not(is_texture))


def display_xray():
    """Toggles xray on selected objects."""
    s = mampy.selected()
    h = mampy.ls(hl=True, dag=True, type='mesh')
    if h: s.extend(h)

    if not s:
        return logger.warn('Nothing selected.')

    print s
    for dag in s.iterdags():
        shape = dag.get_shape()
        if shape is not None and shape.type == MFn.kMesh:
            state = cmds.displaySurface(str(shape), q=True, xRay=True)
            cmds.displaySurface(str(shape), xRay=not(state.pop()))


def wireframe_shaded_toggle():
    """Toggles between wireframe and shaded on objects."""
    current_panel = cmds.getPanel(withFocus=True)
    if not is_model_panel(current_panel):
        return logger.warn('Panel must be modelPanel.')

    is_wire = cmds.modelEditor(current_panel, q=True, da=True)
    if is_wire == 'wireframe':
        cmds.modelEditor(current_panel, e=True, da='smoothShaded')
    else:
        cmds.modelEditor(current_panel, e=True, da='wireframe')


def wireframe_on_shaded():
    """Toggles shaded on wireframe, will be visible on background objects."""
    current_panel = cmds.getPanel(withFocus=True)
    if not is_model_panel(current_panel):
        return logger.warn('Panel must be modelPanel.')

    is_wos = cmds.modelEditor(current_panel, q=True, wos=True)
    cmds.modelEditor(current_panel, e=True, wos=not(is_wos))


def wireframe_on_bg_objects():
    """Toggles wireframe/shaded on background objects."""
    current_panel = cmds.getPanel(withFocus=True)
    if not is_model_panel(current_panel):
        return cmds.warning('Panel must be modelPanel')

    state = cmds.modelEditor(current_panel, q=True, activeOnly=True)
    cmds.modelEditor(current_panel, e=True, activeOnly=not(state))


def wireframe_backface_culling():
    """Toggles backface culling on/off."""
    is_wire_culling = cmds.polyOptions(gl=True, q=True, wireBackCulling=True)
    if not all(is_wire_culling):
        cmds.polyOptions(gl=True, wireBackCulling=True)
    else:
        cmds.polyOptions(gl=True, backCulling=True)


if __name__ == '__main__':
    display_xray()
