__author__ = "David Rusk <drusk@uvic.ca>"

import wx

from mopgui.view import util, navview, dialogs
from mopgui.view.dataview import KeyValueListPanel
from mopgui.view.validationview import SourceValidationPanel


class MainFrame(wx.Frame):
    """
    This is the main window of the application.  It should not be
    manipulated externally (it should be considered an implementation detail
    of the ApplicationView).  Therefore, updates should come from the
    ApplicationView.
    """

    def __init__(self, model, appcontroller, validationcontroller, navcontroller,
                 size=(400, 500)):
        super(MainFrame, self).__init__(None, title="Moving Object Pipeline",
                                        size=size)

        self.SetIcon(wx.Icon(util.get_asset_full_path("cadc_icon.jpg"),
                             wx.BITMAP_TYPE_JPEG))

        self.model = model

        self.appcontroller = appcontroller
        self.validationcontroller = validationcontroller
        self.navcontroller = navcontroller

        self._init_ui_components()

    def _init_ui_components(self):
        self.menubar = self._create_menus()

        self.CreateStatusBar()
        self.nav_view = navview.NavPanel(self, self.navcontroller)

        self.data_view = self._create_data_notebook()

        self.validation_view = SourceValidationPanel(self, self.validationcontroller)

        self.img_loading_dialog = dialogs.WaitingGaugeDialog(self, "Image loading...")

        self._do_layout()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.nav_view, 1, flag=wx.EXPAND)
        sizer.Add(self.data_view, 2, flag=wx.EXPAND)
        sizer.Add(self.validation_view, 1, flag=wx.EXPAND)

        self.SetSizer(sizer)

    def _create_menus(self):
        def do_bind(handler, item):
            self.Bind(wx.EVT_MENU, handler, item)

        # Create menus and their contents
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "Exit", "Exit the program")
        do_bind(self.appcontroller.on_exit, exit_item)

        # Create menu bar
        menubar = wx.MenuBar()
        menubar.Append(file_menu, "File")
        self.SetMenuBar(menubar)

        return menubar

    def _create_data_notebook(self):
        notebook = wx.Notebook(self)

        reading_data_panel = KeyValueListPanel(notebook, self.model.get_reading_data)
        obs_header_panel = KeyValueListPanel(notebook, self.model.get_header_data_list)

        notebook.AddPage(reading_data_panel, "Readings")
        notebook.AddPage(obs_header_panel, "Observation Header")

        return notebook

    def show_image_loading_dialog(self):
        if not self.img_loading_dialog.IsShown():
            self.img_loading_dialog.CenterOnParent()
            self.img_loading_dialog.Show()

    def hide_image_loading_dialog(self):
        if self.img_loading_dialog.IsShown():
            self.img_loading_dialog.Hide()

    def set_source_status(self, current_source, total_sources):
        self.GetStatusBar().SetStatusText(
            "Source %d of %d" % (current_source, total_sources))


if __name__ == "__main__":
    # Quick manual acceptance test
    class DummyModel(object):
        def get_reading_data(self):
            return [("X", 111), ("Y", 222)]

        def get_header_data_list(self):
            return [("FWHM", "3.00"), ("SNR", 10)]

    class DummyAppController(object):
        def on_exit(self, event):
            print "Pressed exit"

    class DummyValController(object):
        def on_accept(self, event):
            print "Accept"

        def on_reject(self, event):
            print "Reject"

    class DummyNavController(object):
        def on_next_source(self, event):
            print "Pressed next source"

        def on_previous_source(self, event):
            print "Pressed previous source"

    app = wx.App()
    frame = MainFrame(DummyModel(), DummyAppController(),
                      DummyValController(), DummyNavController())
    frame.Show()
    app.MainLoop()
