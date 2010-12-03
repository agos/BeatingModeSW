#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx


class MainFrame(wx.Frame):

    def __init__(self, parent=None, id=-1, title="Main Frame"):
        wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition,
            wx.Size(900, 700), style=wx.DEFAULT_FRAME_STYLE)

        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        close_window_menu = wx.MenuItem(file_menu, 105,
            'Close &Window\tCtrl+W', 'Close the Window')
        file_menu.AppendItem(close_window_menu)
        menubar.Append(file_menu, '&File')
        self.SetMenuBar(menubar)
        self.statusbar = self.CreateStatusBar()
        self.Bind(wx.EVT_MENU, self.OnCloseMe, close_window_menu)
        self.Centre()

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
