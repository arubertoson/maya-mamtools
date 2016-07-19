import logging

import maya.cmds as cmds
import maya.mel as mel
from maya.api.OpenMaya import MFn

import mampy
from mampy.dgcontainers import SelectionList


logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


__all__ = ['unhide_all', 'visibility_toggle', 'isolate_selected', 'subd_toggle_all',
           'subd_toggle_selected', 'subd_level', 'display_edges', 'display_vertex',
           'display_border_edges', 'display_map_border', 'display_textures',
           'display_xray', 'wireframe_shaded_toggle', 'wireframe_on_shaded',
           'wireframe_on_bg_objects', 'wireframe_backface_culling']


# if(`isAttributeEditorRaised`){if(!`isChannelBoxVisible`){setChannelBoxVisible(1);} else {raiseChannelBox;}}else{openAEWindow;}


class IsolateSelected(object):
    """IsolateSelected class

    Additional functionality for standard isolate selection. Will isolate again
    if selection has changed.
    """

    instance = None

    def __init__(self):
        self.reset()

    @staticmethod
    def get_instance():
        if IsolateSelected.instance is None:
            IsolateSelected.instance = IsolateSelected()
        return IsolateSelected.instance

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


def isolate_selected():
    """
    Toggles isolate selected.
    """
    IsolateSelected.get_instance().toggle()


class SubDToggle(object):
    """SubDToggle class

    Clas for subd toggle functionality.
    """

    instance = None

    @staticmethod
    def get_instance():
        if SubDToggle.instance is None:
            SubDToggle.instance = SubDToggle()
        return SubDToggle.instance

    def all(self, off=False):
        """SubD toggle all meshes off or on."""
        for mesh in self.get_meshes(True):
            cmds.displaySmoothness(str(mesh), po=3 if off else 0)

    def selected(self, hierarchy=False):
        """SubD toggle selected meshes."""
        for mesh in self.get_meshes(False, hierarchy):
            state = cmds.displaySmoothness(str(mesh), q=True, po=True).pop()
            cmds.displaySmoothness(str(mesh), po=0 if state == 3 else 3)

    def get_meshes(self, all=False, hierarchy=False):
        if all:
            return mampy.ls(type='mesh').iterdags()

        if hierarchy:
            selected = mampy.ls(sl=True, dag=True, type='mesh')
        else:
            selected = SelectionList()
            for mesh in mampy.selected().iterdags():
                shape = mesh.get_shape()
                if shape is None:
                    continue
                selected.add(shape)

        hilited = mampy.ls(hl=True, dag=True, type='mesh')
        if hilited:
            selected.extend(hilited)
        return selected.iterdags()

    def level(self, level=1, all=True, hierarchy=False):
        """Change subd level on meshes."""
        if all:
            meshes = self.get_meshes(all=True, hierarchy=hierarchy)
        else:
            meshes = self.get_meshes(all=False, hierarchy=hierarchy)

        for mesh in meshes:
            mesh['smoothLevel'] = mesh['smoothLevel'] + level


def subd_toggle_all(state=False):
    SubDToggle.get_instance().all(state)


def subd_toggle_selected(hierarchy=True):
    """
    Toggle subd display on meshes.
    """
    SubDToggle.get_instance().selected(hierarchy=hierarchy)


def subd_level(level, all=False, hierarchy=True):
    """
    Change level of subd meshes.
    """
    subdtoggle = SubDToggle.get_instance()
    subdtoggle.level(level) if all else subdtoggle.level(level, all, hierarchy)


def is_model_panel(panel):
    return cmds.getPanel(typeOf=panel) == 'modelPanel'


def unhide_all(unhide_types=None):
    """
    unhide all groups and mesh objects in the scene.
    """
    s = mampy.ls(transforms=True)
    for dag in s.iterdags():
        shape = dag.get_shape()
        if shape is None or shape.type == MFn.kMesh:
            dag["visibility"] = True


def visibility_toggle():
    """
    Toggle visibility of selected objects.
    """
    s = mampy.selected()
    for dag in s.iterdags():
        dag['visibility'] = not(dag.visibility)


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
    """
    Toggles xray on selected objects.
    """
    s = mampy.ls(sl=True, dag=True, type='mesh')
    h = mampy.ls(hl=True, dag=True, type='mesh')
    if h: s.extend(h)

    if not s:
        return logger.warn('Nothing selected.')

    for dag in s.iterdags():
        shape = dag.get_shape()
        if shape is not None and shape.type == MFn.kMesh:
            state = cmds.displaySurface(str(shape), q=True, xRay=True)
            cmds.displaySurface(str(shape), xRay=not(state.pop()))


def wireframe_shaded_toggle():
    """
    Toggles between wireframe and shaded on objects.
    """
    current_panel = cmds.getPanel(withFocus=True)
    if not is_model_panel(current_panel):
        return logger.warn('Panel must be modelPanel.')

    is_wire = cmds.modelEditor(current_panel, q=True, da=True)
    if is_wire == 'wireframe':
        cmds.modelEditor(current_panel, e=True, da='smoothShaded')
    else:
        cmds.modelEditor(current_panel, e=True, da='wireframe')


def wireframe_on_shaded():
    """
    Toggles shaded on wireframe, will be visible on background objects.
    """
    current_panel = cmds.getPanel(withFocus=True)
    if not is_model_panel(current_panel):
        return logger.warn('Panel must be modelPanel.')

    is_wos = cmds.modelEditor(current_panel, q=True, wos=True)
    cmds.modelEditor(current_panel, e=True, wos=not(is_wos))


def wireframe_on_bg_objects():
    """
    Toggles wireframe/shaded on background objects.
    """
    current_panel = cmds.getPanel(withFocus=True)
    if not is_model_panel(current_panel):
        return cmds.warning('Panel must be modelPanel')

    state = cmds.modelEditor(current_panel, q=True, activeOnly=True)
    cmds.modelEditor(current_panel, e=True, activeOnly=not(state))


def wireframe_backface_culling():
    """
    Toggles backface culling on/off.
    """
    is_wire_culling = cmds.polyOptions(gl=True, q=True, wireBackCulling=True)
    if not all(is_wire_culling):
        cmds.polyOptions(gl=True, wireBackCulling=True)
    else:
        cmds.polyOptions(gl=True, backCulling=True)


def view_outliner(floating=False):
    """
    Toggle the outliner on as a dock window to the right side of the viewport,
    if floating is ture then toggle outliner to a floating window.

    makes sure to delete the dockControl UI when visibility is lost to
    ensure the name is available for maya.

    .. old::
        panel_window = 'outlinerPanel1Window'
        if cmds.window(panel_window, q=True, exists=True):
            cmds.deleteUI(panel_window, window=True)
        else:
            panel = cmds.getPanel(withLabel='Outliner')
            cmds.outlinerPanel(panel, e=True, tearOff=True)
    """
    # Constants
    TABLAYOUT = 'MAM_TAB_LAYOUT'
    DOCK_CONTROL_OUTLINER = 'MAM_DOCK_CONTROL_OUTLINER'

    if not cmds.paneLayout(TABLAYOUT, q=True, ex=True):
        cmds.paneLayout(TABLAYOUT, p=mel.eval('$tmp = $gMainWindow'))

    # Creat or show outliner.
    if not cmds.dockControl(DOCK_CONTROL_OUTLINER, q=True, ex=True):
        cmds.dockControl(
            DOCK_CONTROL_OUTLINER,
            label='Outliner',
            width=280,
            content=TABLAYOUT,
            allowedArea=['left', 'right'],
            area='right',
        )

    # Tear it off or dock it depending on floating arg.
    vis_state = cmds.dockControl(DOCK_CONTROL_OUTLINER, q=True, vis=True)
    fl_state = cmds.dockControl(DOCK_CONTROL_OUTLINER, q=True, fl=True)
    cmds.dockControl(DOCK_CONTROL_OUTLINER, e=True, fl=floating)
    if (vis_state and not fl_state == floating):
        pass
    else:
        cmds.dockControl(
            DOCK_CONTROL_OUTLINER,
            e=True,
            vis=not(cmds.dockControl(DOCK_CONTROL_OUTLINER, q=True, vis=True)),
        )

    if not cmds.dockControl(DOCK_CONTROL_OUTLINER, q=True, vis=True):
        try:
            cmds.deleteUI(DOCK_CONTROL_OUTLINER)
        except RuntimeError:
            pass
    else:
        # Create outliner pane under tablayout if it's not there.
        outliner_window = 'outlinerPanel1Window'
        if not cmds.control(outliner_window, q=True, ex=True):
            panel = cmds.getPanel(withLabel='Outliner')
            cmds.outlinerPanel(panel, e=True, p=TABLAYOUT)
            # cmds.control(outliner_window, e=True, p=TABLAYOUT)

    if floating:
        cmds.dockControl(DOCK_CONTROL_OUTLINER, e=True, height=600)


def view_script_editor(direction='bottom', floating=False):
    """
    Toggle the script output as a dock window to the given side of the
    viewport, if floating is true then toggle outliner to a floating window.

    makes sure to delete the dockControl UI when visibility is lost to
    ensure the name is available for maya.
    """
    def context_menu():
        """
        Create context menu for output window.
        """
        # context menu
        output_win = cmds.cmdScrollFieldReporter(SCRIPT_OUTPUT_SCROLLFIELD, fst="")
        cmds.popupMenu(parent=output_win)
        cmds.menuItem(
            label='Clear Output',
            command=lambda c: cmds.cmdScrollFieldReporter(
                output_win, e=True, clear=True),
        )
        # Echo all commands toggle
        cmds.menuItem(
            label='Toggle Echo Commands',
            command=lambda c: cmds.commandEcho(
                state=not(cmds.commandEcho(q=True, state=True))),
        )
        # Go to python reference
        cmds.menuItem(
            label='Python Command Reference',
            command=lambda c: cmds.showHelp('DocsPythonCommands'),
        )

    def create_script_output():
        """
        Create the dock window.
        """
        if cmds.window(SCRIPT_OUTPUT_WINDOW, ex=True):
            main_win = SCRIPT_OUTPUT_WINDOW
        else:
            main_win = cmds.window(SCRIPT_OUTPUT_WINDOW, title='Output Window')

        cmds.paneLayout(parent=main_win)
        context_menu()

        cmds.dockControl(
            SCRIPT_OUTPUT_DOCK,
            content=main_win,
            label='Output Window',
            area=direction,
            # height=500,
            floating=False,
            allowedArea=['bottom']
        )

    # Constants
    SCRIPT_OUTPUT_WINDOW = 'MAM_SCRIPT_OUTPUT_WINDOW'
    SCRIPT_OUTPUT_DOCK = 'MAM_SCRIPT_OUTPUT_DOCK'
    SCRIPT_OUTPUT_SCROLLFIELD = 'MAM_SCRIPT_OUTPUT_SCROLLFIELD'
    SCRIPT_EDITOR_WINDOW = 'scriptEditorPanel1Window'
    SCRIPT_EDITOR_PANE = 'scriptEditorPanel1'

    if not floating:
        if not cmds.dockControl(SCRIPT_OUTPUT_DOCK, ex=True):
            create_script_output()
        else:
            state = not(cmds.dockControl(SCRIPT_OUTPUT_DOCK, q=True, vis=True))
            cmds.dockControl(SCRIPT_OUTPUT_DOCK, e=True, vis=state)
    elif floating:
        if cmds.window(SCRIPT_EDITOR_WINDOW, q=True, exists=True):
            cmds.deleteUI(SCRIPT_EDITOR_WINDOW, window=True)
        else:
            cmds.scriptedPanel(SCRIPT_EDITOR_PANE, e=True, tearOff=True)


def view_render():
    panel_window = 'renderViewWindow'
    if cmds.window(panel_window, q=True, exists=True):
        cmds.deleteUI(panel_window, window=True)
    else:
        panel = cmds.getPanel(withLabel='Render View')
        cmds.scriptedPanel(panel, e=True, tearOff=True)


def view_hypershader():
    panel_window = 'hyperShadePanel1Window'
    if cmds.window(panel_window, q=True, exists=True):
        cmds.deleteUI(panel_window, window=True)
    else:
        panel = cmds.getPanel(withLabel='Hypershade')
        cmds.scriptedPanel(panel, e=True, tearOff=True)


def view_uv_editor():
    panel_window = 'uvTextureEditor'
    if cmds.window(panel_window, q=True, exists=True):
        cmds.deleteUI(panel_window, window=True)
    else:
        mel.eval('NightshadeUVEditor')


def view_namespace_editor():
    panel_window = 'namespaceEditor'
    if cmds.window(panel_window, q=True, exists=True):
        cmds.deleteUI(panel_window, window=True)
    else:
        mel.eval(panel_window)


def view_hypergraph():
    mel.eval('HypergraphDGWindow')


def view_node_editor():
    mel.eval('NodeEditorWindow;')


if __name__ == '__main__':
    pass
