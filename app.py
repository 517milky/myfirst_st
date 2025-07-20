import streamlit as st
import os
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from pytube import Playlist

# 페이지 설정
st.set_page_config(layout="wide")
st.title("📥 유튜브 재생목록 일괄 다운로드 (최고 화질)")

# 다운로드 폴더 준비
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 재생목록 URL 입력
playlist_url = st.text_input("🔗 유튜브 재생목록 URL을 입력하세요:")

def get_playlist_videos(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        return playlist.video_urls
    except Exception as e:
        st.error(f"재생목록 불러오기 실패: {e}")
        return []

def download_video(url, index, total):
    st.write(f"🎬 ({index+1}/{total}) 다운로드 중: {url}")
    ydl_opts = {
        "format": "best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "progress_hooks": [lambda d: st.write(f"✅ 완료: {d['filename']}") if d['status'] == 'finished' else None]
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadError as e:
        st.error(f"❌ 오류 발생: {e}")

if playlist_url:
    urls = get_playlist_videos(playlist_url)
    total = len(urls)
    if urls:
        st.success(f"🔍 총 {total}개의 영상이 감지되었습니다.")
        with st.spinner("📥 영상 다운로드 중..."):
            for idx, url in enumerate(urls):
                download_video(url, idx, total)
        st.success("🎉 모든 다운로드가 완료되었습니다!")
    else:
        st.warning("⚠️ 재생목록에서 영상을 불러오지 못했습니다.")
