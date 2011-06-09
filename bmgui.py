# -*- coding: utf-8 -*-

import wx
from wx.xrc import *
import os
import wxmpl
from numpy import *
from beatingmode import BeatingImage
from colors import rate_color_map, ratio_color_map, gray_color_map
import multiprocessing
from scipy.stats.mstats import mquantiles


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
        self.x, self.y = None, None
        self.InitDetails()

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
        self.menuMain = self.res.LoadMenuBar('menuMain')

        # Bind menu events to the proper methods
        wx.EVT_MENU(self, XRCID('menuOpen'), self.OnOpenMeasure)
        wx.EVT_MENU(self, XRCID('menuSave'), self.OnSave)
        wx.EVT_MENU(self, XRCID('menuExit'), self.OnClose)

        # Set the menu as the default menu for this frame
        self.SetMenuBar(self.menuMain)

        self.SetSizer(mainGrid)
        self.Layout()

        #Set the Minumum size
        self.SetMinSize((900, 700))
        self.Centre(wx.BOTH)

        # Initialize the welcome notebook tab
        panelWelcome = self.res.LoadPanel(self.notebook, 'panelWelcome')
        self.notebook.AddPage(panelWelcome, 'Welcome')

    def InitDetails(self):
        self.old_coord = (None, None)
        self.fig = self.panelDetails.get_figure()
        self.fig.set_edgecolor('white')
        self.ax_top = self.fig.add_subplot(211,
            title="Row Repetitions")
        self.ax_bottom = self.fig.add_subplot(212,
            title="Point Repetitions")
        self.ax_bottom.grid()
        self.fig.subplots_adjust(hspace=0.3)
        self.canvas = self.fig.canvas
        self.empty_details = True
        self.canvas.draw()

    def ReplotDetails(self, e=None):
        x, y = self.x, self.y
        ax_top, ax_bottom = self.ax_top, self.ax_bottom
        # clear the axes and replot everything
        # Do the drawing
        if x is not None and y is not None and (x,y) != self.old_coord:
            if self.empty_details:
                # TODO non aspettare il primo draw per fare le prime cose
                # Set axes limits
                ax_top.imshow(empty((self.bimg.width, self.bimg.repetitions)))
                self.ax_bottom.set_xlim(0.0, self.bimg.repetitions)
                self.ax_bottom.set_ylim(0.0, self.bimg.unbleached_array.max())
                # Copy the plot backgrounds for later reuse
                self.bg_top = self.canvas.copy_from_bbox(ax_top.bbox)
                self.bg_bottom = self.canvas.copy_from_bbox(ax_bottom.bbox)
                # Initial plot, top slot
                self.det_im = ax_top.imshow(self.bimg.unbleached_array[y,:,:],
                    cmap=rate_color_map, interpolation='nearest',
                    vmin=0.0, vmax=self.rec_on.max(), animated=True)
                # Initial plot, bottom slot (repetitions)
                values = self.bimg.unbleached_array[y,:,x]
                pos = arange(len(values))
                self.det_plt, = ax_bottom.plot(pos, values, 'k',
                    animated=True)
                # Beating status highlight plots
                mask_off = self.bimg.rows[y].beating_mask[:,x]
                mask_on = ones(mask_off.shape) - mask_off
                val_off = ma.array(values, mask=mask_off)
                val_on = ma.array(values, mask=mask_on)
                self.det_plt_on, = ax_bottom.plot(pos, val_on, 'r',
                    animated=True)
                self.det_plt_off, = ax_bottom.plot(pos, val_off, 'b',
                    animated=True)
                # Thresholds plot
                self.det_thr_on = ax_bottom.axhline(
                    y=self.bimg.thresOn, color='r', animated=True)
                self.det_thr_off = ax_bottom.axhline(
                    y=self.bimg.thresOff, color='b', animated=True)
                # Draw, but from now on we blit
                self.panelDetails.draw()
                self.empty_details = False
            else:
                # Top panel: only if y changes. Laziness = performance
                self.canvas.restore_region(self.bg_top)
                self.det_im.set_data(self.bimg.unbleached_array[y,:,:])
                ax_top.draw_artist(self.det_im)
                self.canvas.blit(ax_top.bbox)
                # Bottom panel
                # Restore background
                self.canvas.restore_region(self.bg_bottom)
                # Update data
                values = self.bimg.unbleached_array[y,:,x]
                width = len(values)
                pos = arange(width)
                mask_off = self.bimg.rows[y].beating_mask[:,x]
                mask_on = ones(mask_off.shape) - mask_off
                val_off = ma.array(values, mask=mask_off)
                val_on = ma.array(values, mask=mask_on)
                # Update line image and line data
                self.det_plt.set_ydata(values)
                self.det_plt_on.set_ydata(val_on)
                self.det_plt_off.set_ydata(val_off)
                self.det_thr_on.set_ydata(self.bimg.thresOn)
                self.det_thr_off.set_ydata(self.bimg.thresOff)
                # Tell those slacking artists to draw
                ax_bottom.draw_artist(self.det_plt)
                ax_bottom.draw_artist(self.det_plt_on)
                ax_bottom.draw_artist(self.det_plt_off)
                ax_bottom.draw_artist(self.det_thr_on)
                ax_bottom.draw_artist(self.det_thr_off)
                # Blit, and we're done
                self.canvas.blit(ax_bottom.bbox)
            self.old_coord = (x,y)

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
            'panelReconstructOn')
        self.panelOff = self.res.LoadPanel(self.notebook,
            'panelReconstructOff')
        self.panelRatios = self.res.LoadPanel(self.notebook,
            'panelRatios')
        self.panelOn.Init(self.res, self)
        self.panelOff.Init(self.res, self)
        self.panelRatios.Init(self.res, self)
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
        # Threshold stuff
        self.sliderThresOn = XRCCTRL(self.panelOn, 'sliderThresholdOn')
        self.sliderThresOff = XRCCTRL(self.panelOff, 'sliderThresholdOff')
        maxThresOn = mquantiles(self.rec_on.flatten(), [0.5])[0]
        maxThresOff = mquantiles(self.rec_off.flatten(), [0.5])[0]
        self.sliderThresOn.SetRange(0.0, maxThresOn)
        self.sliderThresOff.SetRange(0.0, maxThresOff)
        self.spinThresOn = XRCCTRL(self.panelOn, 'spinThresholdOn')
        self.spinThresOff = XRCCTRL(self.panelOff, 'spinThresholdOff')
        self.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK,
            self.OnSliderOn, self.sliderThresOn)
        self.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK,
            self.OnSliderOff, self.sliderThresOff)
        # Enable the Save menu
        self.menuMain.Enable(XRCID('menuSave'), True)

    def OnSliderOn(self, e):
        threshold = self.sliderThresOn.GetValue()
        self.spinThresOn.SetValue(threshold)
        self.bimg.thresOn = threshold
        self.rec_on = self.bimg.reconstructed_on
        self.panelOn.Replot(data=self.rec_on,
            max_rate=self.rec_on.max())
        self.ratios = self.bimg.ratios
        self.panelRatios.Replot(data=self.ratios)

    def OnSliderOff(self, e):
        threshold = self.sliderThresOff.GetValue()
        self.spinThresOff.SetValue(threshold)
        self.bimg.thresOff = threshold
        self.rec_off = self.bimg.reconstructed_off
        self.panelOff.Replot(data=self.rec_off,
            max_rate=self.rec_on.max())
        self.ratios = self.bimg.ratios
        self.panelRatios.Replot(data=self.ratios)

    def OnSave(self, e):
        wildcard = "Data file (.dat)|*.dat|PNG file (.png)|*.png"
        dialog = wx.FileDialog(None, message="Choose a prefix", defaultDir="",
            defaultFile="output", wildcard=wildcard, style=wx.SAVE)
        if dialog.ShowModal() == wx.ID_OK:
            print("Saving. Prefix: {0}. Format: {1}".format(
                dialog.GetPath(), dialog.GetFilterIndex()))
            self.saveData(dialog.GetPath(), dialog.GetFilterIndex())
            dialog.Destroy()

    def saveData(self, path, index):
        if index == 0:
            savetxt(path + "-on.dat", self.rec_on,
                fmt="%10.5f", delimiter="\t")
            savetxt(path + "-off.dat", self.rec_off,
                fmt="%10.5f", delimiter="\t")
            savetxt(path + "-ratios.dat", self.ratios,
                fmt="%10.5f", delimiter="\t")
        else:
            self.panelOn.fig.savefig(path + "-on.png", dpi=300)
            self.panelOff.fig.savefig(path + "-off.png", dpi=300)
            self.panelRatios.fig.savefig(path + "-ratios.png", dpi=300)

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
            crosshairs=False, autoscaleUnzoom=False)
        self.panelOnOff.director.axesMouseMotion = self.axesMouseMotion
        self.fig = self.panelOnOff.get_figure()
        self.fig.set_edgecolor('white')
        res.AttachUnknownControl('panelReconstructed',
            self.panelOnOff, self)
        self.empty = True
        self.panelOnOff.draw()

    def Replot(self, data=None, max_rate=None):
        # Clear the axes and replot everything
        if data is not None:
            if self.empty:
                self.axes = self.fig.gca()
                self.axes.cla()
                self.axes.imshow(zeros_like(data), cmap=rate_color_map)
                self.panelOnOff.draw()
                self.bg = self.panelOnOff.copy_from_bbox(self.axes.bbox)
                self.im = self.axes.imshow(data, cmap=rate_color_map,
                interpolation='nearest', vmin=0.0, vmax=max_rate, animated=True)
                if not hasattr(self, 'cb'):
                    self.cb = self.fig.colorbar(self.im, shrink=0.5)
                    self.cb.set_label("Hz")
                self.panelOnOff.draw()
                self.empty = False
            else:
                self.panelOnOff.restore_region(self.bg)
                self.im.set_data(data)
                self.axes.draw_artist(self.im)
                self.panelOnOff.blit(self.axes.bbox)

    def axesMouseMotion(self, evt, x, y, axes, xdata, ydata):
        """
        Overriding wxmpl event handler to do my stuff™
        """
        xdata = int(floor(xdata + 0.5))
        ydata = int(floor(ydata + 0.5))
        # The original stuff. We'll leave this for now.
        view = self.panelOnOff.director.view
        view.cursor.setCross()
        view.crosshairs.set(x, y)
        # Changed: we round the coordinates
        view.location.set(wxmpl.format_coord(axes, xdata, ydata))
        # Added: the replot of the details on mouse movement
        self.mainFrame.x, self.mainFrame.y = xdata, ydata
        self.mainFrame.ReplotDetails()


class PanelRatios(wx.Panel):

    def __init__(self):
        pre = wx.PrePanel()
        # the Create step is done by XRC.
        self.PostCreate(pre)

    def Init(self, res, frame):
        self.mainFrame = frame
        self.panelRatios = wxmpl.PlotPanel(self, -1, size=(6, 4.50), dpi=68,
            crosshairs=False, autoscaleUnzoom=False)
        self.panelRatios.director.axesMouseMotion = self.axesMouseMotion
        self.fig = self.panelRatios.get_figure()
        self.fig.set_edgecolor('white')
        res.AttachUnknownControl('panelRatios',
            self.panelRatios, self)
        self.empty = True
        self.panelRatios.draw()

    def Replot(self, data=None):
        # Clear the axes and replot everything
        if data is not None:
            if empty:
                self.axes = self.fig.gca()
                self.axes.cla()
                self.axes.imshow(zeros_like(data), cmap=ratio_color_map)
                self.panelRatios.draw()
                self.bg = self.panelRatios.copy_from_bbox(self.axes.bbox)
                self.im = self.axes.imshow(data, cmap=ratio_color_map,
                    interpolation='nearest', animated=True)
                if not hasattr(self, 'cb'):
                    self.cb = self.fig.colorbar(self.im, shrink=0.5)
                self.panelRatios.draw()
                self.empty = False
            else:
                self.panelRatios.restore_region(self.bg)
                self.im.set_data(data)
                self.axes.draw_artist(self.im)
                self.panelRatios.blit(self.axes.bbox)

    def axesMouseMotion(self, evt, x, y, axes, xdata, ydata):
        """
        Overriding wxmpl event handler to do my stuff™
        """
        xdata = int(floor(xdata + 0.5))
        ydata = int(floor(ydata + 0.5))
        # The original stuff. We'll leave this for now.
        view = self.panelRatios.director.view
        view.cursor.setCross()
        view.crosshairs.set(x, y)
        # Changed: we round the coordinates
        view.location.set(wxmpl.format_coord(axes, xdata, ydata))
        # Added: the replot of the details on mouse movement
        self.mainFrame.x, self.mainFrame.y = xdata, ydata
        self.mainFrame.ReplotDetails()


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
