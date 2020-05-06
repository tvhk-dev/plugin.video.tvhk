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

API_ENDPOINT = str(kodiutils.get_setting("api_endpoint"))
db = sqlite.connect(os.path.dirname(os.path.realpath(__file__)) + '/db.db')
db.row_factory = lambda c, r: dict([(col[0], r[idx]) for idx, col in enumerate(c.description)])
f = open(os.path.dirname(os.path.realpath(__file__)) + "/../init.sql", "r")
sql = f.read()
f.close()

db.executescript(sql)

try:
    lastTimestamp = db.execute("select CAST(strftime('%s', updatedAt) as integer) from playlists order by updatedAt desc limit 1").fetchone()['updatedAt']
except:
    lastTimestamp = 0

xbmc.log('lastTimestamp:' + str(lastTimestamp), 2)

def update(updateType):
    if updateType == "lives":
        """
        j = requests.get(API_ENDPOINT + '/api.php?action=lives&channelID=' + CHANNEL_ID + '&lastUpdate=' + str(lastTimestamp), timeout=15).json()      
        lives = j["live"]

        db.execute('DELETE FROM lives;')

        for id in lives:
            db.execute(
                'INSERT INTO lives (`id`, `channelID`, `timestamp`, `content`) values (%(id)s,%(channel)s,%(timestamp)s,%(content)s);',
                {
                    'id': id,
                    'channel': CHANNEL_ID,
                    'timestamp': datetime.datetime.fromtimestamp(int(lives[id]["timestamp"])).strftime("%Y-%m-%d %H:%M:%S"),
                    'content': json.dumps(lives[id])
                })
        """

    elif updateType == "channels":
        j = requests.get(API_ENDPOINT + '/api.php?action=channels&lastUpdate=' + str(lastTimestamp), timeout=15).json()
        
        config = j["config"]
        if db.execute('select id from config').fetchone() == None:
            db.execute('INSERT INTO config (`config`) values (?);',[json.dumps(config)])
        else:
            db.execute('UPDATE config SET `config` = ? WHERE `id` = ?', [json.dumps(config), db.execute('select id from config').fetchone()["id"]])

        channels = j["channels"]
        for channelID in channels:
            channel = channels[channelID]
            playlists = channel["playlists"]
            playlistConfigs = {}
            for playlistID in playlists:
                playlistConfigs[playlistID] = playlists[playlistID]["config"]
                for videoID in playlists[playlistID]["videos"]:
                    video = playlists[playlistID]["videos"][videoID]
                    if int(db.execute('select count(*) as count from playlists where uuid=? and playlistID=?',(videoID, playlistID)).fetchone()['count']) == 0:
                        db.execute(
                            'INSERT INTO playlists (`uuid`, `channelID`, `playlistID`, `timestamp`, `content`, `updatedAt`) values (?,?,?,?,?,?);',
                            (
                                videoID,
                                channelID,
                                playlistID,
                                datetime.datetime.fromtimestamp(int(video["timestamp"])).strftime("%Y-%m-%d %H:%M:%S"),
                                json.dumps(video),
                                datetime.datetime.fromtimestamp(int(video["updatedAt"])).strftime("%Y-%m-%d %H:%M:%S")
                            ))
                    else:
                        db.execute(
                            'UPDATE playlists SET `channelID` = ?, `timestamp` = ?, `content` = ?, `updatedAt` = ? WHERE `uuid` = ?', 
                            (
                                channelID,
                                datetime.datetime.fromtimestamp(int(video["timestamp"])).strftime("%Y-%m-%d %H:%M:%S"),
                                json.dumps(video),
                                datetime.datetime.fromtimestamp(int(video["updatedAt"])).strftime("%Y-%m-%d %H:%M:%S"),
                                playlistID
                            ))
            config = channel["config"]
            config["playlists"] = playlistConfigs
            if db.execute('select channelID from channels where channelID = ?', [channelID]).fetchone() == None:
                db.execute('INSERT INTO channels (`channelID`, `config`, `updatedAt`) values (?,?,?);',[channelID, json.dumps(config), datetime.datetime.fromtimestamp(int(j["updatedAt"])).strftime("%Y-%m-%d %H:%M:%S")])
            else:
                db.execute('UPDATE channels SET `config` = ?, `updatedAt` = ? WHERE `channelID` = ?', [json.dumps(config), datetime.datetime.fromtimestamp(int(j["updatedAt"])).strftime("%Y-%m-%d %H:%M:%S"), channelID])

    db.commit()

def getChannels():
    update("channels")
    query = db.execute('select config, channelID from channels').fetchall()
    channels = {}
    if (query != None):
        for row in query:
            channels[row["channelID"]] = json.loads(row["config"])
            metadata = channels[row["channelID"]]["metadata"]
            metadata["bg"] = constructResourceURL(metadata["thumb"]) #makeshift temply
            metadata["thumb"] = constructResourceURL(metadata["thumb"])
            for playlistID in channels[row["channelID"]]["playlists"]:
                playlist = channels[row["channelID"]]["playlists"][playlistID]
                playlist["metadata"]["bg"] = constructResourceURL(playlist["metadata"]["thumb"]) #makeshift temply
                playlist["metadata"]["thumb"] = constructResourceURL(playlist["metadata"]["thumb"]) #makeshift temply
                
        return channels

def getConfig():
    update("channels")
    query = db.execute('select config from config').fetchone()
    if (query != None):
        config = json.loads(query["config"])
        return config

def getPlaylistVideos(playlistID, raw=False):
    update("channels")
    playlist = db.execute('select * from playlists where playlistID = ? order by `updatedAt` desc', [playlistID]).fetchall()
    result = []
    for video in playlist:
        info = json.loads(video['content'])
        info['id'] = video['uuid']
        result.append(info)
    if (raw):
        return result
    else:
        return videoInfoToListItem(result)
    pass

def getLives(channelID):
    update("lives")
    lives = db.execute('select * from lives where channelID = ? order by `timestamp` desc', [channelID]).fetchall()
    result = []
    for video in lives:
        info = json.loads(video['content'])
        info['id'] = video['id']
        result.append(info)
    return videoInfoToListItem(result)
    
    
def videoInfoToListItem(videoInfos):
    result = []
    for info in videoInfos:
       
        liz = ListItem(label=info['title'])
        infolabels = {"plot": info["description"]}
        liz.setInfo(type="video", infoLabels=infolabels)
        liz.setProperty("videoid", info['id'])
        liz.setProperty("url", info['files'][next(iter(info['files']))])
        liz.setProperty('IsPlayable', 'true')
        liz.setArt({
            'thumb': constructResourceURL(info['thumb']),
            'fanart': constructResourceURL(info['thumb']),
            #"poster": remoteConfig['peertube']['serverRoot'] + info['thumb']
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
        result.append(liz)
        #liz.setProperty('IsPlayable', 'true')
        #cm = []
        #cm.append(("Info", 'XBMC.Action(Info)'))
        #liz.addContextMenuItems(cm, replaceItems=False)
    return result


def constructResourceURL(url):
    return remoteConfig['peertube']['serverRoot'] + url if str(url).startswith("/") else url

remoteConfig = getConfig()