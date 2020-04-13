# -*- coding: utf-8 -*-

import routing # pylint: disable=E0401
import xbmcaddon
import xbmcplugin
from resources.lib import kodiutils
from resources.lib import db
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory
import xbmc
import urllib
import json, sys


ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ICON = ADDON.getAddonInfo("icon")
FANART = ADDON.getAddonInfo("fanart")
plugin = routing.Plugin()
_channels = db.getChannels()

@plugin.route('/')
def index():
    for channelID in _channels:
        channelConfig = _channels[channelID]
        liz = ListItem(channelConfig["title"])
        infolabels = {"plot": channelConfig["description"]}
        liz.setInfo(type="video", infoLabels=infolabels)
        liz.setArt({"thumb": channelConfig["thumb"], "fanart": channelConfig["bg"]})
        addDirectoryItem(plugin.handle, plugin.url_for(channel, channelID=channelID), liz, True)
        
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    endOfDirectory(plugin.handle)        
    pass

@plugin.route('/channel')
def channel():
    channelID = plugin.args["channelID"][0] if "channelID" in plugin.args.keys() else ""
    channelConfig = _channels[channelID]
    
    # Playlists
    for playlistID in channelConfig['playlists']:
        liz = ListItem(channelConfig['playlists'][playlistID]["title"])
        infolabels = {"plot": channelConfig['playlists'][playlistID]["description"]}
        liz.setInfo(type="video", infoLabels=infolabels)
        
        liz.setArt({"thumb": channelConfig['playlists'][playlistID]["thumb"], "fanart": xbmcaddon.Addon().getAddonInfo("fanart")})
        if (True if len(channelConfig['playlists']) == 1 else False):
            liz.setProperty('IsPlayable', 'true')
            addDirectoryItem(plugin.handle, plugin.url_for(play_playlist, playlistID=playlistID), liz, False)
        else:
            addDirectoryItem(plugin.handle, plugin.url_for(all_videos, playlistID=playlistID), liz, True)
            
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    endOfDirectory(plugin.handle)


@plugin.route('/videos')
def all_videos():
    #page_num = int(plugin.args["page"][0]) if "page" in plugin.args.keys() else 1
    playlistID = plugin.args["playlistID"][0] if "playlistID" in plugin.args.keys() else ""

    if "playlistID" in plugin.args.keys() and plugin.args["playlistID"][0] != "all":
        liz = ListItem("Play All")
        liz.setInfo(type="video", infoLabels={'plot':"Play All"})
        liz.setProperty('IsPlayable', 'true')
        addDirectoryItem(plugin.handle, plugin.url_for(play_playlist, playlistID=playlistID), liz, False)
        result = db.getPlaylistVideos(playlistID) #,page_num
    else:
        #result = db.getUploadVideos(page_num)
        pass

    for liz in result:
        addDirectoryItem(plugin.handle, plugin.url_for(play, liz.getProperty("url")), liz, False)
    
    kodiutils.add_sort_methods(plugin.handle)
    xbmcplugin.setContent(plugin.handle, 'episodes')
    endOfDirectory(plugin.handle)


@plugin.route('/play_playlist')
def play_playlist(playlistID = ""):
    playlistID = plugin.args["playlistID"][0] if "playlistID" in plugin.args.keys() else playlistID
    videos = db.getPlaylistVideos(playlistID, raw=True)
    urls = []
    for video in videos:
        urls.append(video["files"][next(iter(video['files']))])

    stream = 'plugin://plugin.video.peertube/?action=play_videos&urls=%s' % json.dumps(urls)
    liz = ListItem()
    liz.setPath(stream)
    liz.setProperty('IsPlayable', 'true') 
    #Send to peertube player plugin
    xbmcplugin.setResolvedUrl(plugin.handle, True, liz)

    #Back from peertube, videos already in queue, let's rock!
    xbmc.Player().play(xbmc.PlayList(1))
    #xbmc.executebuiltin('playlist.playoffset(video,0)')

@plugin.route('/play/<path:url>')
def play(url):    
    stream = 'plugin://plugin.video.peertube/?action=play_videos&url=%s' % url
    liz = ListItem()
    liz.setPath(stream)
    xbmcplugin.setResolvedUrl(plugin.handle, True, liz)

@plugin.route('/live')
def live():
    __addon__ = xbmcaddon.Addon()
    __profile__ = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
    xbmc.log(__profile__,2)
    
    live_videos = db.getLives()
    if not live_videos:
        kodiutils.notification(
            ADDON_NAME,
            kodiutils.get_string(32009)
        )
    else:
        for liz in live_videos:
            addDirectoryItem(plugin.handle, plugin.url_for(play, liz.getProperty("videoid")), liz, False)
        kodiutils.add_sort_methods(plugin.handle)
        xbmcplugin.setContent(plugin.handle, 'episodes')
        endOfDirectory(plugin.handle)
        
def run():
    if not kodiutils.get_setting_as_bool("enter_all_videos"):
        plugin.run()
    else:
        plugin.redirect("/videos")




