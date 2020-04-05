# -*- coding: utf-8 -*-

import routing # pylint: disable=E0401
import xbmcaddon
import xbmcplugin
from resources.lib import kodiutils
from resources.lib import youtubelib
from resources.lib import db
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory
import xbmc
import YDStreamExtractor


ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ICON = ADDON.getAddonInfo("icon")
FANART = ADDON.getAddonInfo("fanart")
plugin = routing.Plugin()


@plugin.route('/')
def index():
    remoteConfig = db.getConfig()
    # Add play directoryItem
    # Live videos
    liz = ListItem("[I]%s[/I]" % (kodiutils.get_string(32010)))
    liz.setInfo(type="video", infoLabels={"plot": kodiutils.get_string(32011)})
    #liz.setArt({"thumb": ICON, "icon": ICON, "fanart": FANART})
    liz.setArt({"thumb": remoteConfig["thumb"], "icon": remoteConfig["thumb"], "fanart": remoteConfig["thumb"]})
    liz.setProperty("isPlayable", "true")
    addDirectoryItem(plugin.handle, plugin.url_for(live), liz, True)

    # All videos
    liz = ListItem("[I]%s[/I]" % (kodiutils.get_string(32000)))
    liz.setInfo(type="video", infoLabels={"plot": kodiutils.get_string(32001)})
    #liz.setArt({"thumb": ICON, "icon": ICON, "fanart": FANART})
    liz.setArt({"thumb": remoteConfig["thumb"], "icon": remoteConfig["thumb"], "fanart": remoteConfig["thumb"]})
    addDirectoryItem(plugin.handle, plugin.url_for(all_videos, playlist="all"), liz, True)
    
    # Playlists
    for playlistID in remoteConfig['playlists']:
        liz = ListItem(remoteConfig['playlists'][playlistID]["title"])
        infolabels = {"plot": remoteConfig['playlists'][playlistID]["description"]}
        liz.setInfo(type="video", infoLabels=infolabels)
        liz.setArt({"thumb": remoteConfig['playlists'][playlistID]["thumb"], "fanart": xbmcaddon.Addon().getAddonInfo("fanart")})
        addDirectoryItem(plugin.handle, plugin.url_for(all_videos, playlist=playlistID), liz, True)
    
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    endOfDirectory(plugin.handle)


@plugin.route('/videos')
def all_videos():
    #db.getPlaylists()
    #grab kwargs
    page_num = int(plugin.args["page"][0]) if "page" in plugin.args.keys() else 1

    if "playlist" in plugin.args.keys() and plugin.args["playlist"][0] != "all":
        result = db.getPlaylistVideos(plugin.args["playlist"][0], page_num)
    else:
        result = db.getUploadVideos(page_num)

    for liz in result:
        addDirectoryItem(plugin.handle, plugin.url_for(play, liz.getProperty("videoid")), liz, False)
        
    kodiutils.add_sort_methods(plugin.handle)
    xbmcplugin.setContent(plugin.handle, 'episodes')
    endOfDirectory(plugin.handle)


@plugin.route('/play/<videoid>')
def play(videoid):
    stream = 'plugin://plugin.video.youtube/play/?video_id=%s' % (videoid)
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
