# -*- coding: utf-8 -*-

"""
    View Types
    ID     Name                Available content type
    54     BannerWall          tvshows, movies, sets
    52     LandscapeWall       tvshows, movies, sets
    ?      PosterShowcase      
    56     LandscapeShowcase   movies, sets, tvshows, episodes, videos, artists, $EXP[Exp_IsPluginAdvancedLauncher]
    57     SquareShowcase      artists, albums, $EXP[Exp_IsPluginAdvancedLauncher]
    58     BigPosters          movies, sets, tvshows, seasons, $EXP[Exp_IsPluginAdvancedLauncher]
    59     Lovefilm            movies, sets, tvshows, artists, $EXP[Exp_IsPluginAdvancedLauncher]
    502    EpisodeList         movies, sets, tvshows, episodes, videos, artists
"""
import routing # pylint: disable=E0401
import xbmc, xbmcaddon, xbmcplugin, xbmcgui
from resources.lib import kodiutils
from resources.lib import db
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory
import urllib
import json, sys, random

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
#ICON = ADDON.getAddonInfo("icon")
plugin = routing.Plugin()
_channels = db.getChannels()

def list_channels(channels):
    xbmcgui.Window(10138).setProperty('isShowAD', "false")
    for channelID in channels:
        channelConfig = _channels[channelID]
        liz = ListItem(channelConfig["metadata"]["title"])
        liz.setInfo(type="video", infoLabels={"plot": channelConfig["metadata"]["description"]})
        liz.setArt({"thumb": channelConfig["metadata"]["thumb"], "fanart": channelConfig["metadata"]["bg"]})
        liz.setProperty('IsPlayable', 'true')
        addDirectoryItem(plugin.handle, plugin.url_for(channel, channelID=channelID), liz, True)

def list_playlist(channelID):
    xbmcgui.Window(10138).setProperty('isShowAD', "false")
    playlists = _channels[channelID]['playlists']
    for playlistID in playlists:
        metadata = playlists[playlistID]["metadata"]
        xbmc.log(str(metadata), 2)
        liz = ListItem(label=metadata["title"])
        infolabels = {"plot": metadata["description"], "Genre":"Genre Here"}
        liz.setInfo(type="video", infoLabels=infolabels)
        liz.setArt({"thumb": metadata["thumb"], "fanart": metadata["thumb"]})
        addDirectoryItem(plugin.handle, plugin.url_for(all_videos, playlistID=playlistID), liz, True)    

def list_videos(playlistID, isRandomSequence=False):
    xbmcgui.Window(10138).setProperty('isShowAD', "false")
    result = db.getPlaylistVideos(playlistID)
    if isRandomSequence: random.shuffle(result)
    for liz in result:
        addDirectoryItem(plugin.handle, plugin.url_for(play, liz.getProperty("url")), liz, False)
    
@plugin.route('/')
def categories():
    for i in range(0,10):
        addDirectoryItem(plugin.handle, plugin.url_for(index, i), ListItem(str(i)), True)
    xbmcplugin.setContent(plugin.handle, 'sets')
    xbmc.executebuiltin("Container.SetViewMode(52)")
    endOfDirectory(plugin.handle)

@plugin.route('/cat/<category>')
def index(category):
    #First, pickout categories we need
    #category = plugin.args["category"][0] if "category" in plugin.args.keys() else 0
    category = int(category)
    pickedChannels = {}
    for channelID in _channels:
        if _channels[channelID]["displayProvision"]["category"] == category:
            pickedChannels[channelID] = _channels[channelID].copy()
    
    to_list_channels = pickedChannels.copy()

    for channelID in pickedChannels:
        channel_displayProvision = pickedChannels[channelID]["displayProvision"]
        if channel_displayProvision["isBreakPlaylistHierarchy"]:
            #get all it's playlists
            playlists = _channels[channelID]['playlists']
            for playlistID in playlists:
                list_videos(playlistID, channel_displayProvision["isRandomSequence"])
            del to_list_channels[channelID]
        elif channel_displayProvision["isBreakChannelHierarchy"]:
            list_playlist(channelID)
            del to_list_channels[channelID]
            
    if (len(to_list_channels) > 0): list_channels(to_list_channels)
    xbmcplugin.setContent(plugin.handle, 'sets')
    xbmc.executebuiltin("Container.SetViewMode(52)")
    endOfDirectory(plugin.handle)

@plugin.route('/channel')
def channel():
    #xbmc.executebuiltin("ActiveWindow(10138)")
    #xbmcplugin.setProperty(plugin.handle, 'FolderName', 'Test')
    #xbmcplugin.setProperty(plugin.handle, 'Container(0).FolderName', 'Test')
    #xbmc.executebuiltin("reloadskin()")
    xbmc.executebuiltin("Skin.SetString(Container.FolderName,'Test')")
    channelID = plugin.args["channelID"][0] if "channelID" in plugin.args.keys() else ""
    list_playlist(channelID)
    xbmcplugin.setContent(plugin.handle, 'videos')
    xbmc.executebuiltin("Container.SetViewMode(56)")
    endOfDirectory(plugin.handle)
    
@plugin.route('/videos')
def all_videos():
    playlistID = plugin.args["playlistID"][0] if "playlistID" in plugin.args.keys() else ""

    liz = ListItem(label="Play All")
    liz.setInfo(type="video", infoLabels={"plot": "", "Genre":""})
    liz.setProperty('IsPlayable', 'true')
    addDirectoryItem(plugin.handle, plugin.url_for(play_playlist, playlistID=playlistID), liz, False)
    list_videos(playlistID)
    xbmcplugin.setContent(plugin.handle, 'episodes')
    xbmc.executebuiltin("Container.SetViewMode(502)")
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
    r = str(random.randint(100000, 999999))
    xbmcgui.Window(10138).setProperty('adsID', r)
    xbmcgui.Window(10138).setProperty('isShowAD', "true")
    stream = 'plugin://plugin.video.peertube/?action=play_video&url=%s' % (urllib.quote(url, '~()*!.\''))
    xbmc.log(stream, 3)
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
    xbmc.log("plugin.video.tvhkAPI involved", 1)
    xbmc.log("sys.argv = " + str(sys.argv), 1)
    if not kodiutils.get_setting_as_bool("enter_all_videos"):
        plugin.run()
    else:
        plugin.redirect("/videos")