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
from beatingmode import BeatingImageRow, BeatingImage


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
        # self.beatingimage = BeatingImage(path="dati/generated.dat", repetitions=15)
        # self.beatingdata = BeatingImageRow(data=self.beatingimage.data[24,:,:], pixel_frequency=100.0, shutter_frequency=5.856 / 2)
        self.beatingimage = BeatingImage(path="dati/samp6.dat", repetitions=90, shutter_frequency=5.856/2)
        self.beatingdata = BeatingImageRow(data=self.beatingimage.data[1,:,:], pixel_frequency=100.0, shutter_frequency=5.865 / 2)
        self.drawingdata = self.beatingdata.data
        self.line_det_h, = self.axes_det1.plot(
            arange(self.beatingdata.image_width),
            zeros_like(arange(self.beatingdata.image_width)),
            animated=True)
        self.axes_det1.set_ylim(self.beatingdata.data.min(), self.beatingdata.data.max())
        self.line_det_v, = self.axes_det2.plot(
            arange(self.beatingdata.image_height),
            zeros_like(arange(self.beatingdata.image_height)),
            animated=True)
        self.axes_det2.set_ylim(self.beatingdata.data.min(), self.beatingdata.data.max())
        self.crosshair_lock = False
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
        self.fig = Figure((9.0, 7.0), dpi=self.dpi)
        self.canvas = FigCanvas(self.panel, -1, self.fig)
        self.onclick_cid = self.canvas.mpl_connect('button_press_event', self.on_mouseclick)
        self.detailfig = Figure((1.0, 7.0), dpi=self.dpi)
        self.detailcanvas = FigCanvas(self.panel, -1, self.detailfig)
        # Since we have only one plot, we can use add_axes
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        self.axes = self.fig.add_subplot(111)
        self.axes_det1 = self.detailfig.add_subplot(211)
        self.axes_det2 = self.detailfig.add_subplot(212)
        self.in_axes = False
        self.canvas.mpl_connect('axes_enter_event', self.enter_axes)
        self.canvas.mpl_connect('axes_leave_event', self.leave_axes)
        self.cb_grid = wx.CheckBox(self.panel, -1,
            "Show Grid",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_unbleach = wx.CheckBox(self.panel, -1,
            "Correct for bleaching",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_unbleach, self.cb_unbleach)
        self.cb_ratiograph = wx.CheckBox(self.panel, -1,
            "Show enhancement ratio data")
        self.cb_ratiograph.Enable(False)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_ratiograph, self.cb_ratiograph)
        self.slider_label = wx.StaticText(self.panel, -1,
            "Crosshair opacity (%): ")
        self.slider_alpha = wx.Slider(self.panel, -1,
            value=30,
            minValue=1,
            maxValue=100,
            style=wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.alpha = 0.3
        self.slider_alpha.SetTickFreq(5, 1)
        self.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK, self.on_slider_alpha, self.slider_alpha)
        # Create the navigation toolbar, tied to the canvas
        self.toolbar = NavigationToolbar(self.canvas)
        #
        # Layout with box sizers
        #
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.graphbox = wx.BoxSizer(wx.HORIZONTAL)
        flags = wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL
        self.graphbox.Add(self.canvas, 2, flag=flags| wx.GROW)
        self.graphbox.Add(self.detailcanvas, 1, flag=flags | wx.GROW)
        self.vbox.Add(self.graphbox, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.vbox.Add(self.toolbar, 0, wx.EXPAND)
        self.vbox.AddSpacer(10)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        flags = wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL
        self.hbox.Add(self.cb_unbleach, 0, border=3, flag=flags)
        self.hbox.Add(self.cb_ratiograph, 0, border=3, flag=flags)
        self.hbox.Add(self.cb_grid, 0, border=3, flag=flags)
        self.hbox.AddSpacer(30)
        self.hbox.Add(self.slider_label, 0, flag=flags)
        self.hbox.Add(self.slider_alpha, 0, border=3, flag=flags)
        self.vbox.Add(self.hbox, 0, flag = wx.ALIGN_CENTER | wx.TOP)
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.callback, self.timer)
        self.prevx, self.prevy = -1, -1

    def draw_figure(self):
        """ Redraws the figure
        """
        self.axes.clear()
        if self.cb_grid.IsChecked():
            self.axes.grid(b=True, color="#ffffff", alpha=0.8)
        if self.cb_unbleach.IsChecked():
            self.drawingdata = self.beatingdata.unbleached_data
        else:
            self.drawingdata = self.beatingdata.data
        self.beating_image = self.axes.imshow(self.drawingdata, cmap=my_color_map)
        self.beating_image.set_interpolation('nearest')
        self.canvas.draw()
        self.detailcanvas.draw()
        if not self.cb_ratiograph.IsChecked():
            self.background_h = self.detailcanvas.copy_from_bbox(self.axes_det1.bbox)
            self.background_v = self.detailcanvas.copy_from_bbox(self.axes_det2.bbox)


    def on_cb_grid(self, event):
        self.draw_figure()

    def on_cb_unbleach(self, event):
        if self.cb_unbleach.IsChecked():
            self.cb_ratiograph.Enable(True)
        else:
            self.cb_ratiograph.Enable(False)
        self.draw_figure()

    def on_cb_ratiograph(self,event):
        if self.cb_ratiograph.IsChecked():
            self.axes_det1.clear()
            width = self.drawingdata.shape[1]
            self.er_graph, = self.axes_det1.plot(
                arange(width),
                self.beatingdata.enhancement_ratios)
            self.axes_det2.clear()
            self.min_graph, = self.axes_det2.plot(
                arange(width),
                self.beatingdata.reconstructed_off)
            self.max_graph, = self.axes_det2.plot(
                arange(width),
                self.beatingdata.reconstructed_on)
            self.detailcanvas.draw()
            self.axes_det1.autoscale()
            self.axes_det2.autoscale()
        else:
            # Riattivare il vecchio grafico!
            self.axes_det1.cla()
            self.axes_det2.cla()
            self.line_det_h, = self.axes_det1.plot(
                arange(self.beatingdata.image_width),
                zeros_like(arange(self.beatingdata.image_width)),
                animated=True)
            self.axes_det1.set_ylim(self.beatingdata.data.min(), self.beatingdata.data.max())
            self.line_det_v, = self.axes_det2.plot(
                arange(self.beatingdata.image_height),
                zeros_like(arange(self.beatingdata.image_height)),
                animated=True)
            self.axes_det2.set_ylim(self.beatingdata.data.min(), self.beatingdata.data.max())
            self.detailcanvas.draw()
            self.background_h = self.detailcanvas.copy_from_bbox(self.axes_det1.bbox)
            self.background_v = self.detailcanvas.copy_from_bbox(self.axes_det2.bbox)

    def OnCloseMe(self, event):
        self.Close(True)

    def on_mouseover(self, event):
        if event.inaxes == self.axes:
            x, y = int(floor(event.xdata)), int(floor(event.ydata))
            self.x, self.y = x, y

    def on_mouseclick(self, event):
        if event.inaxes == self.axes:
            if not self.crosshair_lock:
                self.crosshair_lock = True
                self.deactivate_mouseover()
                x, y = int(floor(event.xdata)), int(floor(event.ydata))
                self.x, self.y = x, y
            else:
                self.crosshair_lock = False
                x, y = int(floor(event.xdata)), int(floor(event.ydata))
                self.x, self.y = x, y
                self.activate_mouseover()

    def activate_mouseover(self):
        self.cid = self.canvas.mpl_connect('motion_notify_event',
            self.on_mouseover)
        self.timer.Start(80)

    def deactivate_mouseover(self):
        self.canvas.mpl_disconnect(self.cid)
        self.timer.Stop()

    def enter_axes(self, event):
        self.in_axes = True
        if not self.crosshair_lock:
            self.activate_mouseover()

    def leave_axes(self, event):
        self.in_axes = False
        if not self.crosshair_lock:
            self.deactivate_mouseover()
            self.statusbar.SetStatusText(" ")
            self.beating_image.set_array(self.drawingdata)
            self.canvas.draw()
            if not self.cb_ratiograph.IsChecked():
                self.axes_det1.clear()
                self.axes_det2.clear()
                self.detailcanvas.draw()

    def callback(self, event):
        if self.in_axes and (self.x != self.prevx or self.y != self.prevy):
            x, y = self.x, self.y
            value = self.drawingdata[y, x]
            msg = "Coordinate: {0}, {1} Valore: {2}".format(x, y, value)
            self.statusbar.SetStatusText(msg)
            highlight_data = copy(self.drawingdata)
            highlight_data[:, x] = highlight_data[:, x] * (1.0 - self.alpha) + highlight_data.max() * self.alpha
            highlight_data[y, :] = highlight_data[y, :] * (1.0 - self.alpha) + highlight_data.max() * self.alpha
            highlight_data[y, x] = value
            self.beating_image.set_array(highlight_data)
            self.canvas.draw()
            # Aggiorno i dettagli
            if not self.cb_ratiograph.IsChecked():
                self.detailcanvas.restore_region(self.background_h)
                self.detailcanvas.restore_region(self.background_v)
                self.line_det_h.set_ydata(self.drawingdata[y, :])
                self.line_det_v.set_ydata(self.drawingdata[:, x])
                self.axes_det1.draw_artist(self.line_det_h)
                self.axes_det2.draw_artist(self.line_det_v)
                self.detailcanvas.blit(self.axes_det1.bbox)
                self.detailcanvas.blit(self.axes_det2.bbox)
                self.prevx, self.prevy = x, y

    def on_slider_alpha(self, event):
        self.alpha = self.slider_alpha.GetValue() / 100.0


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
