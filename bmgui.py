# -*- coding: utf-8 -*-

import wx
from wx.xrc import *
import os
import wxmpl
from numpy import *
from beatingmode import BeatingImage
from colors import rate_color_map, ratio_color_map, gray_color_map
import multiprocessing
import argparse


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

        # Get the references for the stats panel
        self.choiceStatistics = XRCCTRL(self, 'choiceStatistics')
        self.caption = []
        self.lbl = []
        self.unit = []
        for i in range(5):
            self.caption.append(XRCCTRL(self, 'caption{0}'.format(i)))
            self.lbl.append(XRCCTRL(self, 'lbl{0}'.format(i)))
            self.unit.append(XRCCTRL(self, 'unit{0}'.format(i)))
        self.Bind(wx.EVT_CHOICE, self.OnChoice)
        self.bimg = None

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

    def prepare_details(self):
        x, y = self.x, self.y
        ax_top, ax_bottom = self.ax_top, self.ax_bottom
        # Set axes limits
        self.det_im = ax_top.imshow(
            zeros((self.bimg.repetitions, self.bimg.width)),
            cmap=rate_color_map, interpolation='nearest',
            vmin=0.0, vmax=self.rec_on.max(), animated=True)
        self.axis = ax_top.get_xaxis()
        self.ax_bottom.set_xlim(0.0, self.bimg.repetitions)
        self.ax_bottom.set_ylim(0.0, self.bimg.unbleached_array.max())
        self.canvas.draw()
        pos = arange(self.bimg.repetitions)
        values = zeros_like(pos)
        self.det_plt, = ax_bottom.plot(pos, values, 'k', animated=True)
        self.det_plt_on, = ax_bottom.plot(pos, values, 'r', animated=True)
        self.det_plt_off, = ax_bottom.plot(pos, values, 'b', animated=True)
        self.det_thr_on = ax_bottom.axhline(y=0, color='r', animated=True)
        self.det_thr_off = ax_bottom.axhline(y=0, color='b', animated=True)
        # Copy the plot backgrounds for later reuse
        self.bg = self.canvas.copy_from_bbox(self.fig.bbox)
        self.canvas.draw()

    def ReplotDetails(self, e=None):
        x, y = self.x, self.y
        ax_top, ax_bottom = self.ax_top, self.ax_bottom
        # clear the axes and replot everything
        # Do the drawing
        if x is not None and y is not None and (x,y) != self.old_coord:
            # Restore background
            self.canvas.restore_region(self.bg)
            # Top panel
            self.det_im.set_data(self.bimg.unbleached_array[y,:,:])
            self.axis.set_ticks([x])
            self.axis.set_tick_params(direction='out',
                length=6, width=2, colors='r')
            self.axis.set_animated(True)
            self.axis.set_ticklabels([""])
            ax_top.draw_artist(self.det_im)
            ax_top.draw_artist(self.axis)
            # Bottom panel
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
            self.canvas.blit(self.fig.bbox)
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
        if not hasattr(self, 'panelOn'):
            # Initialize the panels
            self.notebook.DeleteAllPages()
            self.panelOn = self.res.LoadPanel(self.notebook,
                'panelReconstructOn')
            self.panelOff = self.res.LoadPanel(self.notebook,
                'panelReconstructOff')
            self.panelRatios = self.res.LoadPanel(self.notebook,
                'panelRatios')
            self.panelOn.Init(self.res, self, on=True)
            self.panelOff.Init(self.res, self, on=False)
            self.panelRatios.Init(self.res, self)
            self.notebook.AddPage(self.panelOn, "Probe on")
            self.notebook.AddPage(self.panelOff, "Probe off")
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
        self.bimg = BeatingImage(path=path, no_bleach=no_bleach)
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
        self.taus = self.bimg.taus
        # Prepare main figure and details figure
        self.panelOn.prepare(data=self.rec_on, max_rate=self.rec_on.max())
        self.panelOff.prepare(data=self.rec_off, max_rate=self.rec_on.max())
        self.panelRatios.prepare(data=self.ratios)
        self.prepare_details()
        # Paint it!
        self.panelOn.Replot(data=self.rec_on)
        self.panelOff.Replot(data=self.rec_off)
        self.panelRatios.Replot(data=self.ratios)
        # Resize stuff
        self.canvas.mpl_connect('resize_event', self.OnResize)
        # Threshold stuff
        self.sliderThresOn = XRCCTRL(self.panelOn, 'sliderThresholdOn')
        self.sliderThresOff = XRCCTRL(self.panelOff, 'sliderThresholdOff')
        maxThresOn = self.rec_on.mean()
        maxThresOff = self.rec_off.mean()
        self.sliderThresOn.SetRange(0.0, maxThresOn * 100)
        self.sliderThresOff.SetRange(0.0, maxThresOff * 100)
        self.sliderThresOn.SetTickFreq(5)
        self.lblThresOn = XRCCTRL(self.panelOn, 'lblThresholdOn')
        self.lblThresOff = XRCCTRL(self.panelOff, 'lblThresholdOff')
        self.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK,
            self.OnSliderOn, self.sliderThresOn)
        self.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK,
            self.OnSliderOff, self.sliderThresOff)
        # Enable the Save menu
        self.menuMain.Enable(XRCID('menuSave'), True)
        # Update the stats
        self.update_stats()

    def update_stats(self, on=None):
        choice = self.choiceStatistics.GetCurrentSelection()
        if choice == 0:
            caption = ["Width:", "Height:",
            "Pixel Width:", "Pixel Height:", "Over Threshold:"]
            if self.bimg is not None:
                lbl = [self.bimg.w_step * self.bimg.width,
                    self.bimg.h_step * self.bimg.height,
                    self.bimg.w_step, self.bimg.h_step,
                    "{:.2%}".format(float(
                    self.ratios.count()) / self.ratios.size)]
            else:
                lbl = ["-"] * 5
            unit = ["µm", "µm", "µm", "µm", "%"]
        else:
            if self.bimg is not None:
                if on is None:
                    data = self.ratios
                elif on is False:
                    data = self.rec_off
                else:
                    data = self.rec_on
        if choice == 1:
            caption = ["Max:", "Min:", "Mean:", "Bleach Time:", "-"]
            lbl = []
            if self.bimg is not None \
            and self.x is not None and self.y is not None:
                row = data[self.y].compressed()
                taus = self.taus[self.y]
                if len(row) > 0:
                    lbl.append("{:.2f}".format(row.max()))
                    lbl.append("{:.2f}".format(row.min()))
                    lbl.append("{:.2f}".format(row.mean()))
                    if len(taus) > 0:
                        pixel_t = 1000 / self.bimg.pixel_frequency
                        tau = taus.mean() * pixel_t
                        stddev = (taus * pixel_t).std()
                        lbl.append("{:.2f} ± {:.2f}".format(tau, stddev))
                    else:
                        lbl.append("-")
                    lbl.append("-")
                else:
                    lbl = ["-"] * 5
            else:
                lbl = ["-"] * 5
            unit = ["Hz", "Hz", "Hz", "ms", "-"]
        if choice == 2:
            caption = ["Max:", "Min:", "Mean:", "Bleach Time:", "-"]
            lbl = []
            if self.bimg is not None \
            and self.x is not None and self.y is not None:
                col = data[:,self.x].compressed()
                col_taus = self.taus[:,self.x]
                if len(col) > 0:
                    lbl.append("{:.2f}".format(col.max()))
                    lbl.append("{:.2f}".format(col.min()))
                    lbl.append("{:.2f}".format(col.mean()))
                    if len(taus) > 0:
                        pixel_t = 1000 / self.bimg.pixel_frequency
                        taus.mean() * pixel_t
                        stddev = (taus * pixel_t).std()
                        lbl.append("{:.2f} ± {:.2f}".format(tau, stddev))
                    else:
                        lbl.append("-")
                    lbl.append("-")
                else:
                    lbl = ["-"] * 5
            else:
                lbl = ["-"] * 5
            unit = ["Hz", "Hz", "Hz", "ms", "-"]
        for i in range(5):
            self.caption[i].SetLabel(str(caption[i]))
            self.lbl[i].SetLabel(str(lbl[i]))
            self.unit[i].SetLabel(str(unit[i]))
            self.lbl[i].Parent.Layout()

    def OnChoice(self, e):
        self.update_stats()

    def OnResize(self, e):
        self.prepare_details()

    def OnSliderOn(self, e):
        threshold = float(self.sliderThresOn.GetValue()) / 100
        self.lblThresOn.SetLabel("{:.2f} Hz".format(threshold))
        self.bimg.thresOn = threshold
        self.rec_on = self.bimg.reconstructed_on
        self.panelOn.Replot(data=self.rec_on)
        self.ratios = self.bimg.ratios
        self.panelRatios.Replot(data=self.ratios)
        self.taus = self.bimg.taus
        self.update_stats()

    def OnSliderOff(self, e):
        threshold = float(self.sliderThresOff.GetValue()) / 100
        self.lblThresOff.SetLabel("{:.2f} Hz".format(threshold))
        self.bimg.thresOff = threshold
        self.rec_off = self.bimg.reconstructed_off
        self.panelOff.Replot(data=self.rec_off)
        self.ratios = self.bimg.ratios
        self.panelRatios.Replot(data=self.ratios)
        self.taus = self.bimg.taus
        self.update_stats()

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

    def Init(self, res, frame, on):
        self.on = on
        self.mainFrame = frame
        self.panelOnOff = wxmpl.PlotPanel(self, -1, size=(6, 4.50), dpi=68,
            crosshairs=False, autoscaleUnzoom=False)
        self.panelOnOff.director.axesMouseMotion = self.axesMouseMotion
        self.fig = self.panelOnOff.get_figure()
        self.fig.set_edgecolor('white')
        res.AttachUnknownControl('panelReconstructed',
            self.panelOnOff, self)
        self.panelOnOff.draw()
        self.panelOnOff.mpl_connect('axes_leave_event', self.OnLeave)

    def prepare(self, data, max_rate=None):
        self.fig.clear()
        self.axes = self.fig.gca()
        self.axes.cla()
        self.im = self.axes.imshow(zeros_like(data), cmap=rate_color_map,
            interpolation='nearest', vmin=0.0, vmax=max_rate, animated=True)
        self.cb = self.fig.colorbar(self.im, shrink=0.5)
        self.cb.set_label("Hz")
        self.panelOnOff.draw()
        self.bg = self.panelOnOff.copy_from_bbox(self.axes.bbox)
        self.bg_cb = self.panelOnOff.copy_from_bbox(self.cb.ax.bbox)

    def Replot(self, data):
        self.data = data
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
        # Added: the replot of the details on mouse movement
        self.mainFrame.x, self.mainFrame.y = xdata, ydata
        self.mainFrame.ReplotDetails()
        # Update colorbar
        self.panelOnOff.restore_region(self.bg_cb)
        axis = self.cb.ax.get_yaxis()
        value = self.data[ydata,xdata]
        self.cb.set_ticks([value])
        axis.set_tick_params(direction='in', length=8, width=3, colors='r')
        axis.set_animated(True)
        self.cb.ax.draw_artist(axis)
        self.panelOnOff.blit(self.cb.ax.bbox)
        # Changed: we round the coordinates
        view.location.set(wxmpl.format_coord(axes, xdata, ydata))
        self.mainFrame.update_stats(on=self.on)

    def OnLeave(self, e):
        self.mainFrame.x, self.mainFrame.y = None, None
        self.mainFrame.update_stats(on=self.on)
        self.mainFrame.prepare_details()


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
        self.panelRatios.draw()
        self.panelRatios.mpl_connect('axes_leave_event', self.OnLeave)

    def prepare(self, data):
        self.fig.clear()
        self.data = data
        self.axes = self.fig.gca()
        self.axes.cla()
        self.im = self.axes.imshow(zeros_like(data), cmap=ratio_color_map,
            interpolation='nearest', vmin=0.95, vmax=data.max(),
            animated=True)
        self.cb = self.fig.colorbar(self.im, shrink=0.5)
        self.panelRatios.draw()
        self.bg = self.panelRatios.copy_from_bbox(self.axes.bbox)
        self.bg_cb = self.panelRatios.copy_from_bbox(self.cb.ax.bbox)

    def Replot(self, data=None):
        # Clear the axes and replot everything
        if data is not None:
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
        # Added: the replot of the details on mouse movement
        self.mainFrame.x, self.mainFrame.y = xdata, ydata
        self.mainFrame.ReplotDetails()
        # Update colorbar
        self.panelRatios.restore_region(self.bg_cb)
        axis = self.cb.ax.get_yaxis()
        value = self.data[ydata,xdata]
        self.cb.set_ticks([value])
        axis.set_tick_params(direction='in', length=8, width=3,
            colors='black')
        axis.set_animated(True)
        self.cb.ax.draw_artist(axis)
        self.panelRatios.blit(self.cb.ax.bbox)
        # Changed: we round the coordinates
        view.location.set(wxmpl.format_coord(axes, xdata, ydata))
        self.mainFrame.update_stats()

    def OnLeave(self, e):
        self.mainFrame.x, self.mainFrame.y = None, None
        self.mainFrame.update_stats()
        self.mainFrame.prepare_details()


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
    description = 'GUI tool to do multi-row beating mode images reconstruction'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-n', '--no-bleach', action='store_true',
        help='disable bleaching correction')
    args = parser.parse_args()
    no_bleach = args.no_bleach
    print("Bleaching correction disabled: {0}".format(args.no_bleach))
    app = bmgui(0)
    app.MainLoop()
