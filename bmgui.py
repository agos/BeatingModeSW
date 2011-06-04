# -*- coding: utf-8 -*-

import wx
from wx.xrc import *
import os
import wxmpl
from numpy import *
from beatingmode import BeatingImage
from colors import rate_color_map, ratio_color_map, gray_color_map
import multiprocessing


class MainFrame(wx.Frame):

    def __init__(self, parent, id, title, res):

        wx.Frame.__init__(self, parent, id, title, pos=wx.DefaultPosition,
            size=(900, 700), style=wx.DEFAULT_FRAME_STYLE)

        # set up resource file and config file
        self.res = res

        # Load the main panel for the program
        self.panelGeneral = self.res.LoadPanel(self, 'panelGeneral')

        # Attach the details graph panel
        self.panelDetails = wxmpl.PlotPanel(self.panelGeneral, -1,
            size=(1, 2), dpi=68, crosshairs=True, autoscaleUnzoom=False)
        self.res.AttachUnknownControl('panelDetails', self.panelDetails, self)
        self.ReplotDetails()

        # Initialize the General panel controls
        self.notebook = XRCCTRL(self, 'notebook')
        self.lblAcquired = XRCCTRL(self, 'lblAcquired')
        self.lblPixelFrequency = XRCCTRL(self, 'lblPixelFrequency')
        self.lblRepetitions = XRCCTRL(self, 'lblRepetitions')
        self.lblShutterFrequency = XRCCTRL(self, 'lblShutterFrequency')

        # Setup the layout for the frame
        mainGrid = wx.BoxSizer(wx.VERTICAL)
        hGrid = wx.BoxSizer(wx.HORIZONTAL)
        hGrid.Add(self.panelGeneral, 1, flag=wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE,
            border=4)
        mainGrid.Add(hGrid, 1, flag=wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE)

        # Load the menu for the frame
        menuMain = self.res.LoadMenuBar('menuMain')

        # Bind menu events to the proper methods
        wx.EVT_MENU(self, XRCID('menuOpen'), self.OnOpenMeasure)
        wx.EVT_MENU(self, XRCID('menuExit'), self.OnClose)

        # Set the menu as the default menu for this frame
        self.SetMenuBar(menuMain)

        self.SetSizer(mainGrid)
        self.Layout()

        #Set the Minumum size
        self.SetMinSize((900, 700))
        self.Centre(wx.BOTH)

        # Initialize the welcome notebook tab
        panelWelcome = self.res.LoadPanel(self.notebook, 'panelWelcome')
        self.notebook.AddPage(panelWelcome, 'Welcome')

    def ReplotDetails(self, x=None, y=None):
        if not hasattr(self, 'old_coord'):
            self.old_coord = (None, None)
        fig = self.panelDetails.get_figure()
        fig.set_edgecolor('white')
        if not hasattr(self, 'details_top'):
            self.details_top = fig.add_subplot(211,
                title="Row Repetitions")
        if not hasattr(self, 'details_bottom'):
            self.details_bottom = fig.add_subplot(212,
                title="Point Repetitions")
        fig.subplots_adjust(hspace=0.3)
        # clear the axes and replot everything
        # Do the drawing
        if x and y and (x,y) != self.old_coord:
            if y != self.old_coord[1]:
                self.details_top.imshow(self.bimg.data[y,:,:],
                  cmap=rate_color_map, interpolation='nearest', vmin=0.0,
                  vmax=self.rec_on.max())
            if self.old_coord != (x,y):
                self.details_bottom.clear()
                self.details_bottom.plot(self.bimg.data[y,:,x])
            self.old_coord = (x,y)
        self.panelDetails.draw()

    def OnOpenMeasure(self, evt):
        wildcard = "Data file (*.dat)|*.dat|" \
            "Ago file (*.ago)|*.ago|" \
            "All files (*.*)|*.*"
        dialog = wx.FileDialog(None, "Choose a measure file", os.getcwd(),
            "", wildcard, wx.OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            print("Opening: {0}".format(dialog.GetPath()))
            self.loadData(dialog.GetPath())
            dialog.Destroy()

    def loadData(self, path):
        # Initialize the panels
        self.notebook.DeleteAllPages()
        self.panelOn = self.res.LoadPanel(self.notebook,
            'panelReconstruct')
        self.panelOff = self.res.LoadPanel(self.notebook,
            'panelReconstruct')
        self.panelRatios = self.res.LoadPanel(self.notebook,
            'panelRatios')
        self.panelOn.Init(self.res, self)
        self.panelOff.Init(self.res, self)
        self.panelRatios.Init(self.res)
        self.notebook.AddPage(self.panelOn, "Rate on")
        self.notebook.AddPage(self.panelOff, "Rate off")
        self.notebook.AddPage(self.panelRatios, "Enhancement Ratios")
        self.panelOn.Update()
        self.panelOff.Update()
        self.panelRatios.Update()
        # Open the Loading progress dialog
        dialog = wx.ProgressDialog("Data loading progress", "Loading...", 100,
            style=wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
        dialog.SetSize((300, 200))
        dialog.Update(0, newmsg="Loading data from disk")
        # Do the actual data loading from file
        self.bimg = BeatingImage(path=path)
        # Show measure metadata
        self.lblAcquired.SetLabel(self.bimg.acquired)
        str_pixel_f = "{0} Hz".format(self.bimg.pixel_frequency)
        self.lblPixelFrequency.SetLabel(str_pixel_f)
        str_shutter_f = "{0} Hz".format(self.bimg.shutter_frequency)
        self.lblShutterFrequency.SetLabel(str_shutter_f)
        self.lblRepetitions.SetLabel(str(self.bimg.repetitions))
        # Let's reconstruct the image
        manager = multiprocessing.Manager()
        queue = manager.Queue()
        self.bimg.reconstruct_with_update(queue=queue, dialog=dialog)
        # Loading complete, progress dialog is not needed anymore
        dialog.Update(100, newmsg="Complete")
        dialog.Destroy()
        # Keep a reference to the data
        self.rec_on = self.bimg.reconstructed_on
        self.rec_off = self.bimg.reconstructed_off
        self.ratios = self.bimg.ratios
        # Paint it!
        self.panelOn.Replot(data=self.rec_on,
            max_rate=self.rec_on.max())
        self.panelOff.Replot(data=self.rec_off,
            max_rate=self.rec_on.max())
        self.panelRatios.Replot(data=self.ratios)

    def OnClose(self, _):
        self.Destroy()


class PanelReconstruct(wx.Panel):

    def __init__(self):
        pre = wx.PrePanel()
        # the Create step is done by XRC.
        self.PostCreate(pre)

    def Init(self, res, frame):
        self.mainFrame = frame
        self.panelOnOff = wxmpl.PlotPanel(self, -1, size=(6, 4.50), dpi=68,
            crosshairs=True, autoscaleUnzoom=False)
        self.panelOnOff.director.axesMouseMotion = self.axesMouseMotion
        self.fig = self.panelOnOff.get_figure()
        self.fig.set_edgecolor('white')
        res.AttachUnknownControl('panelReconstructed',
            self.panelOnOff, self)
        self.Replot()

    def Replot(self, data=None, max_rate=None):
        # Clear the axes and replot everything
        if data is not None:
            axes = self.fig.gca()
            axes.cla()
            axes.imshow(data, cmap=rate_color_map,
            interpolation='nearest', vmin=0.0, vmax=max_rate)
        self.panelOnOff.draw()

    def axesMouseMotion(self, evt, x, y, axes, xdata, ydata):
        """
        Overriding wxmpl event handler to do my stuff™
        """
        # The original stuff. We'll leave this for now.
        view = self.panelOnOff.director.view
        view.cursor.setCross()
        view.crosshairs.set(x, y)
        # Changed: we round the coordinates
        view.location.set(wxmpl.format_coord(axes,
            int(floor(xdata)), int(floor(ydata))))
        # Added: the replot of the details on mouse movement
        self.mainFrame.ReplotDetails(int(floor(xdata)), int(floor(ydata)))


class PanelRatios(wx.Panel):

    def __init__(self):
        pre = wx.PrePanel()
        # the Create step is done by XRC.
        self.PostCreate(pre)

    def Init(self, res):
        self.panelRatios = wxmpl.PlotPanel(self, -1, size=(6, 4.50), dpi=68,
            crosshairs=True, autoscaleUnzoom=False)
        self.fig = self.panelRatios.get_figure()
        self.fig.set_edgecolor('white')
        res.AttachUnknownControl('panelRatios',
            self.panelRatios, self)
        self.Replot()

    def Replot(self, data=None):
        # Clear the axes and replot everything
        if data is not None:
            axes = self.fig.gca()
            axes.cla()
            axes.imshow(data, cmap=ratio_color_map, interpolation='nearest')
        self.panelRatios.draw()


class bmgui(wx.App):

    def OnInit(self):
        wx.InitAllImageHandlers()
        wx.GetApp().SetAppName("bmgui")

        # Load the XRC file for our gui resources
        self.res = XmlResource('main.xrc')

        bmFrame = MainFrame(None, -1, "bmgui", self.res)
        self.SetTopWindow(bmFrame)
        bmFrame.Centre()
        bmFrame.Show()
        return 1


if __name__ == '__main__':
    app = bmgui(0)
    app.MainLoop()
