import wx
from wx.xrc import *


class MainFrame(wx.Frame):

    def __init__(self, parent, id, title, res):

        wx.Frame.__init__(self, parent, id, title, pos=wx.DefaultPosition,
            size=(900, 700), style=wx.DEFAULT_FRAME_STYLE)

        # set up resource file and config file
        self.res = res

        # Load the main panel for the program
        self.panelGeneral = self.res.LoadPanel(self, 'panelGeneral')

        # Initialize the General panel controls
        self.notebook = XRCCTRL(self, 'notebook')

        # Setup the layout for the frame
        mainGrid = wx.BoxSizer(wx.VERTICAL)
        hGrid = wx.BoxSizer(wx.HORIZONTAL)
        hGrid.Add(self.panelGeneral, 1, flag=wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE, border=4)
        mainGrid.Add(hGrid, 1, flag=wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE)

        # Load the menu for the frame
        menuMain = self.res.LoadMenuBar('menuMain')

        # Bind menu events to the proper methods
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

    def OnClose(self, _):
        self.Destroy()


class bmgui(wx.App):

    def OnInit(self):
        wx.InitAllImageHandlers()
        wx.GetApp().SetAppName("bmgui")

        # Load the XRC file for our gui resources
        self.res = XmlResource('main.xrc')

        dicompylerFrame = MainFrame(None, -1, "bmgui", self.res)
        self.SetTopWindow(dicompylerFrame)
        dicompylerFrame.Centre()
        dicompylerFrame.Show()
        return 1


if __name__ == '__main__':
    app = bmgui(0)
    app.MainLoop()
