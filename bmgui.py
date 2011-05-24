import wx
from wx.xrc import *


class MainFrame(wx.Frame):

    def __init__(self, parent, id, title, res):

        wx.Frame.__init__(self, parent, id, title, pos=wx.DefaultPosition,
            size=(900, 700), style=wx.DEFAULT_FRAME_STYLE)


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
