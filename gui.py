#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx
from numpy import *
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
from matplotlib.colors import LinearSegmentedColormap
from beatingmode import BeatingData


my_color_map = LinearSegmentedColormap("stdGreen",
                {
                'red': [(0.0, 0.0, 0.0),
                       (1.0, 0.0, 0.0)],
               'green': [(0.0, 0.0, 0.0),
                         (1.0, 1.0, 1.0)],
               'blue': [(0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0)],
                })


class MainFrame(wx.Frame):

    def __init__(self, parent=None, id=-1, title="Main Frame"):
        wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition,
            wx.Size(900, 700), style=wx.DEFAULT_FRAME_STYLE)

        self.create_menu()
        self.statusbar = self.CreateStatusBar()
        self.create_main_panel()
        self.Centre()
        self.beatingdata = BeatingData(path="dati/dati.dat", pixel_frequency=100.0, shutter_frequency=9.78 / 2)
        self.draw_figure()

    def create_menu(self):
        self.menubar = wx.MenuBar()
        file_menu = wx.Menu()
        close_window_menu = wx.MenuItem(file_menu, 105,
            'Close &Window\tCtrl+W', 'Close the Window')
        file_menu.AppendItem(close_window_menu)
        self.Bind(wx.EVT_MENU, self.OnCloseMe, close_window_menu)
        self.menubar.Append(file_menu, '&File')
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        """ Creates the main panel with all the controls on it:
             * mpl canvas
             * mpl navigation toolbar
             * Control panel for interaction
        """
        self.panel = wx.Panel(self)
        # Create the mpl Figure and FigCanvas objects.
        # 5x4 inches, 100 dots-per-inch
        self.dpi = 100
        self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        self.canvas = FigCanvas(self.panel, -1, self.fig)
        # Since we have only one plot, we can use add_axes
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        self.axes = self.fig.add_subplot(111)
        # Bind the 'pick' event for clicking on one of the bars
        #self.canvas.mpl_connect('pick_event', self.on_pick)
        self.textbox = wx.TextCtrl(
            self.panel,
            size=(200, -1),
            style=wx.TE_PROCESS_ENTER)
        #self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.textbox)
        self.drawbutton = wx.Button(self.panel, -1, "Draw!")
        #self.Bind(wx.EVT_BUTTON, self.on_draw_button, self.drawbutton)
        self.cb_grid = wx.CheckBox(self.panel, -1,
            "Show Grid",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.slider_label = wx.StaticText(self.panel, -1,
            "Bar width (%): ")
        self.slider_width = wx.Slider(self.panel, -1,
            value=20,
            minValue=1,
            maxValue=100,
            style=wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.slider_width.SetTickFreq(10, 1)
        #self.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK, self.on_slider_width, self.slider_width)
        # Create the navigation toolbar, tied to the canvas
        self.toolbar = NavigationToolbar(self.canvas)
        #
        # Layout with box sizers
        #
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.vbox.Add(self.toolbar, 0, wx.EXPAND)
        self.vbox.AddSpacer(10)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        flags = wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL
        self.hbox.Add(self.textbox, 0, border=3, flag=flags)
        self.hbox.Add(self.drawbutton, 0, border=3, flag=flags)
        self.hbox.Add(self.cb_grid, 0, border=3, flag=flags)
        self.hbox.AddSpacer(30)
        self.hbox.Add(self.slider_label, 0, flag=flags)
        self.hbox.Add(self.slider_width, 0, border=3, flag=flags)
        self.vbox.Add(self.hbox, 0, flag = wx.ALIGN_LEFT | wx.TOP)
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def draw_figure(self):
        """ Redraws the figure
        """
        self.axes.clear()
        self.axes.grid(self.cb_grid.IsChecked())
        self.beating_image = self.axes.imshow(self.beatingdata.data, cmap=my_color_map)
        self.beating_image.set_interpolation('nearest')
        self.canvas.draw()

    def on_cb_grid(self, event):
        self.draw_figure()

    def OnCloseMe(self, event):
        self.Close(True)


class beatingmode(wx.App):

    def OnInit(self):
        wx.GetApp().SetAppName("Beating Mode GUI")
        mainframe = MainFrame(title='Beating Mode GUI')
        self.SetTopWindow(mainframe)
        mainframe.Centre()
        mainframe.Show(True)
        return True


if __name__ == '__main__':
    app = beatingmode(0)
    app.MainLoop()
