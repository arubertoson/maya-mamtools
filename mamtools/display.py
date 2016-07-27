import logging

import maya.cmds as cmds
import maya.mel as mel
from maya.api.OpenMaya import MFn


from PySide.QtGui import QDockWidget

import mampy
from mampy.pyside.utils import get_maya_main_window



logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


__all__ = ['unhide_all', 'visibility_toggle', 'display_edges', 'display_vertex',
           'display_border_edges', 'display_map_border', 'display_textures',
           'display_xray', 'wireframe_shaded_toggle', 'wireframe_on_shaded',
           'wireframe_on_bg_objects', 'wireframe_backface_culling']


def toggle_default_material():
    current_panel = cmds.getPanel(withFocus=True)
    state = cmds.modelEditor(current_panel, q=True, useDefaultMaterial=True)
    cmds.modelEditor(current_panel, e=True, useDefaultMaterial=not(state))


def toggle_lights(lights=None):
    current_panel = cmds.getPanel(withFocus=True)
    if lights:
        cmds.modelEditor(current_panel, e=True, displayLights=lights)
    else:
        state = cmds.modelEditor(current_panel, q=True, displayLights=True)
        result = 'all' if not state == 'all' else 'default'
        cmds.modelEditor(current_panel, e=True, displayLights=result)


def toggle_AA():
    state = cmds.getAttr('hardwareRenderingGlobals.multiSampleEnable')
    cmds.setAttr('hardwareRenderingGlobals.multiSampleEnable', not(state))


def toggle_occlusion():
    state = cmds.getAttr('hardwareRenderingGlobals.ssaoEnable')
    cmds.setAttr('hardwareRenderingGlobals.ssaoEnable', not(state))


def toggle_raised_dock():
    main_window = get_maya_main_window()
    window_main_docks = sorted([
        'Tool Settings',
        'Modeling Toolkit',
        'Attribute Editor',
        'Channel Box / Layer Editor'
    ])
    print window_main_docks
    widgets = {}
    for dock in main_window.findChildren(QDockWidget):
        title = dock.windowTitle()
        if title not in window_main_docks:
            continue
        if dock.isVisible():
            widgets[title] = dock
        else:
            window_main_docks.remove(title)

    for k, i in widgets.iteritems():
        if not i.widget().visibleRegion().isEmpty():
            idx = window_main_docks.index(k)

    try:
        dock_widget = widgets[window_main_docks[idx + 1]]
    except IndexError:
        dock_widget = widgets[window_main_docks[0]]
    dock_widget.raise_()


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


def shaded_toggle():
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
        cmds.paneLayout(TABLAYOUT, p='viewPanes')  # mel.eval('$tmp = $gMainWindow'))

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


if __name__ == '__main__':
    toggle_raised_dock()
