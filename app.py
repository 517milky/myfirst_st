from yt_dlp import YoutubeDL

playlist_url = "https://www.youtube.com/playlist?list=PL1dMxl3V0rvhW6JxKtw6yIw3LyLN8Z_wW"

ydl_opts = {
    'quiet': False,
    'verbose': True,
    'no_warnings': False,
    'extract_flat': True,
}

with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(playlist_url, download=False)
    print(f"재생목록 제목: {info.get('title')}")
    entries = info.get('entries', [])
    print(f"영상 수: {len(entries)}")
    for e in entries[:5]:
        print(e.get('title'))
