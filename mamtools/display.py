import logging

import maya.cmds as cmds
import maya.mel as mel
from maya.api.OpenMaya import MFn

import mampy
from mampy.dgcontainers import SelectionList


logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


__all__ = ['unhide_all', 'visibility_toggle', 'isolate_selected',
           'subd_toggle', 'subd_level', 'display_edges', 'display_vertex',
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
        self._all = False

    def all(self, off=False):
        """SubD toggle all meshes off or on."""
        self._all = True
        self._state = 3 if off else 0
        self._meshes = self.get_meshes(all=True)
        self._toggle()

    def selected(self, hierarchy=False):
        """SubD toggle selected meshes."""
        self._all = False
        self._hierarchy = hierarchy
        self._meshes = self.get_meshes(all=False)
        self._toggle()

    def level(self, level=1, all=True, hierarchy=False):
        """Change subd level on meshes."""
        self._hierarchy = hierarchy
        if all:
            meshes = self.get_meshes(all=True)
        else:
            meshes = self.get_meshes(all=False)

        for mesh in meshes.iterdags():
            mesh.smoothLevel.set(mesh.smoothLevel.get() + level)

    def get_meshes(self, all=True):
        """Return all SubD meshes in scene."""
        if all:
            return mampy.ls(type='mesh')
        else:
            if self._hierarchy:
                s = mampy.ls(sl=True, dag=True, type='mesh')
            else:
                s = SelectionList()
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
        for mesh in self._meshes.iterdags():
            try:
                if self._all:
                    logger.debug('doing all {}, {}'.format(self._all, self._state))
                    cmds.displaySmoothness(str(mesh), po=self._state)
                elif self._state is None or self._state:
                    state = cmds.displaySmoothness(str(mesh), q=True, po=True)[0]
                    cmds.displaySmoothness(str(mesh), po=0 if state == 3 else 3)
            except AttributeError:
                logger.warn('{} is of type: {}'.format(mesh, type(mesh)))


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
        dag.visibility.set(not(dag.visibility.get()))


def isolate_selected():
    """
    Toggles isolate selected.
    """
    if IsolateSelected.instance is None:
        IsolateSelected.instance = IsolateSelected()
    IsolateSelected.instance.toggle()


def subd_toggle(all=False, hierarchy=True, off=None):
    """
    Toggle subd display on meshes.
    """
    if SubDToggle.instance is None:
        SubDToggle.instance = SubDToggle()

    logger.debug('all state: {}'.format(all))
    if all:
        SubDToggle.instance.all(off)
    else:
        SubDToggle.instance.selected(hierarchy=hierarchy)


def subd_level(level, all=False, hierarchy=True):
    """
    Change level of subd meshes.
    """
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
        output_win = cmds.cmdScrollFieldReporter(fst="")
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
    view_script_editor(floating=True)
