import xbmc
import os
try:
    from sqlite3 import dbapi2 as sqlite
    xbmc.log("Loading sqlite3 as DB engine", 2)
except:
    from pysqlite2 import dbapi2 as sqlite
    xbmc.log("Loading pysqlite2 as DB engine", 2)
import datetime
import requests
import json
from xbmcgui import ListItem
import xbmcaddon
import kodiutils

CHANNEL_ID = str(kodiutils.get_setting("channel_id"))
API_ENDPOINT = str(kodiutils.get_setting("api_endpoint"))
db = sqlite.connect(os.path.dirname(os.path.realpath(__file__)) + '/db.db')
db.row_factory = lambda c, r: dict([(col[0], r[idx]) for idx, col in enumerate(c.description)])
f = open(os.path.dirname(os.path.realpath(__file__)) + "/../init.sql", "r")
sql = f.read()
f.close()

db.executescript(sql)

try:
    lastTimestamp = db.execute("select CAST(strftime('%s', updatedAt) as integer) from channels order by updatedAt desc limit 1").fetchone()['updatedAt']
    lastPlaylistTimestamp = db.execute("select CAST(strftime('%s', updatedAt) as integer) from playlists order by updatedAt desc limit 1").fetchone()['updatedAt']
    if (lastTimestamp < lastPlaylistTimestamp):
        lastTimestamp = lastPlaylistTimestamp
except:
    lastTimestamp = 0

xbmc.log('lastTimestamp:' + str(lastTimestamp), 2)

def update(updateType):
    if updateType == "lives":
        j = requests.get(API_ENDPOINT + '/api.php?action=lives&channelID=' + CHANNEL_ID + '&lastUpdate=' + str(lastTimestamp), timeout=15).json()      
        lives = j["live"]

        db.execute('DELETE FROM lives;')

        for id in lives:
            db.execute(
                'INSERT INTO lives (`id`, `channel`, `timestamp`, `content`) values (%(id)s,%(channel)s,%(timestamp)s,%(content)s);',
                {
                    'id': id,
                    'channel': CHANNEL_ID,
                    'timestamp': datetime.datetime.fromtimestamp(int(lives[id]["timestamp"])).strftime("%Y-%m-%d %H:%M:%S"),
                    'content': json.dumps(lives[id])
                })

    elif updateType == "uploads":
        j = requests.get(API_ENDPOINT + '/api.php?action=uploads&channelID=' + CHANNEL_ID + '&lastUpdate=' + str(lastTimestamp), timeout=15).json()
        uploads = j["uploads"]

        for uuid in uploads:
            db.execute(
                "REPLACE INTO channels (`uuid`, `channel`, `timestamp`, `content`, `updatedAt`) VALUES (?,?,?,?,?)",
                (
                    uuid,
                    CHANNEL_ID,
                    str(datetime.datetime.fromtimestamp(int(uploads[uuid]["timestamp"]))).strftime("%Y-%m-%d %H:%M:%S"),
                    json.dumps(uploads[uuid]),
                    str(datetime.datetime.fromtimestamp(int(uploads[uuid]["updatedAt"]))).strftime("%Y-%m-%d %H:%M:%S")
                ))

    elif updateType == "playlists":
        j = requests.get(API_ENDPOINT + '/api.php?action=playlists&channelID=' + CHANNEL_ID + '&lastUpdate=' + str(lastTimestamp), timeout=15).json()
        playlists = j["playlists"]

        for playlistID in playlists:
            for videoID in playlists[playlistID]:
                video = playlists[playlistID][videoID]
                if int(db.execute('select count(*) as count from playlists where uuid=? and playlist=?',(videoID, playlistID)).fetchone()['count']) == 0:
                    db.execute(
                        'INSERT INTO playlists (`uuid`, `channel`, `playlist`, `timestamp`, `content`, `updatedAt`) values (?,?,?,?,?,?);',
                        (
                            videoID,
                            CHANNEL_ID,
                            playlistID,
                            datetime.datetime.fromtimestamp(int(video["timestamp"])).strftime("%Y-%m-%d %H:%M:%S"),
                            json.dumps(video),
                            datetime.datetime.fromtimestamp(int(video["updatedAt"])).strftime("%Y-%m-%d %H:%M:%S")
                        ))
                else:
                    db.execute(
                        'UPDATE playlists SET `channel` = ?, `timestamp` = ?, `content` = ?, `updatedAt` = ? WHERE `uuid` = ?', 
                        (
                            CHANNEL_ID,
                            datetime.datetime.fromtimestamp(int(video["timestamp"])).strftime("%Y-%m-%d %H:%M:%S"),
                            json.dumps(video),
                            datetime.datetime.fromtimestamp(int(video["updatedAt"])).strftime("%Y-%m-%d %H:%M:%S"),
                            playlistID
                        ))
    elif updateType == "config":
        j = requests.get(API_ENDPOINT + '/api.php?action=config&channelID=' + CHANNEL_ID, timeout=15).json()
        config = j["config"]
        if db.execute('select id from config').fetchone() == None:
            db.execute('INSERT INTO config (`config`) values (?);',[json.dumps(config)])
        else:
            db.execute('UPDATE config SET `config` = ? WHERE `id` = ?', [json.dumps(config), db.execute('select id from config').fetchone()["id"]])

    db.commit()

def getUploadVideos(page):
    update("uploads")
    #itemPerPage = 10
    #page -= 1
    uploads = db.execute('select * from channels order by `updatedAt` desc').fetchall()
    result = []
    for video in uploads:
        info = json.loads(video['content'])
        info['id'] = video['uuid']
        result.append(info)
    return videoInfoToListItem(result)
    pass

def getPlaylistVideos(playlistID, page):
    update("playlists")
    playlist = db.execute('select * from playlists where playlist = ? order by `updatedAt` desc', [playlistID]).fetchall()
    result = []
    for video in playlist:
        info = json.loads(video['content'])
        info['id'] = video['uuid']
        result.append(info)
    return videoInfoToListItem(result)
    pass

def getLives():
    update("lives")
    lives = db.execute('select * from lives order by `timestamp` desc').fetchall()
    result = []
    for video in lives:
        info = json.loads(video['content'])
        info['id'] = video['id']
        result.append(info)
    return videoInfoToListItem(result)

def getConfig():
    update("config")
    query = db.execute('select config from config').fetchone()
    if (query != None):
        config = json.loads(query["config"])
        return config
    
def videoInfoToListItem(videoInfos):
    remoteConfig = getConfig()
    for info in videoInfos:
       
        liz = ListItem(info['title'])
        infolabels = {"plot": info["description"]}
        liz.setInfo(type="video", infoLabels=infolabels)
        liz.setProperty("videoid", info['id'])
        liz.setProperty("url", info['files'][next(iter(info['files']))])
        liz.setArt({
            'thumb': remoteConfig['peertube']['serverRoot'] + info['thumb'],
            'fanart': xbmcaddon.Addon().getAddonInfo("fanart"),
            "poster": remoteConfig['peertube']['serverRoot'] + info['thumb']
        })
        #liz.setProperty("type","playlist")
        video_info = {
            'codec': 'avc1',
            'aspect': 1.78,
            'width': 1920,
            'height': 1080
        }
        liz.addStreamInfo('video', video_info)
        audio_info = {'codec': 'aac', 'language': 'zh-hk', 'channels': 2}
        liz.addStreamInfo('audio', audio_info)
        liz.setProperty('IsPlayable', 'true')
        cm = []
        cm.append(("Info", 'XBMC.Action(Info)'))
        liz.addContextMenuItems(cm, replaceItems=False)
        yield liz