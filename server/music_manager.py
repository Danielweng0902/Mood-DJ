# -*- coding: utf-8 -*-
# 改為從 YouTube Music 搜尋曲目 (使用 yt_dlp 抓音訊串流 URL)
import yt_dlp

YOUTUBE_PLAYLISTS = {
    "happy": "happy upbeat music",
    "sad": "sad piano music",
    "calm": "lofi chill beats",
    "energetic": "party dance hits"
}

def search_youtube_music(mood: str) -> str:
    """Search YouTube Music by mood and return a playable audio URL."""
    query = YOUTUBE_PLAYLISTS.get(mood, "lofi chill beats")
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "format": "bestaudio/best",
        "default_search": "ytsearch1",  # 只取第一個搜尋結果
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "_type" in info and info["_type"] == "playlist":
            info = info["entries"][0]
        url = info["url"] if "url" in info else info["formats"][0]["url"]
        title = info.get("title", "Unknown")
        print(f"[music_manager] Found: {title}")
        return url