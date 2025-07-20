import streamlit as st
import os
from yt_dlp import YoutubeDL
from pytube import Playlist
import threading

st.set_page_config(layout="wide")
st.title("📥 유튜브 재생목록 전체 다운로드")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

playlist_url = st.text_input("🔗 유튜브 재생목록 URL 입력")

def get_playlist_videos(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        return playlist.video_urls
    except Exception as e:
        st.error(f"재생목록 불러오기 실패: {e}")
        return []

def download_video(url):
    ydl_opts = {
        "format": "best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info_dict)
            return filepath
    except Exception as e:
        st.error(f"다운로드 실패: {e}")
        return None

if playlist_url:
    urls = get_playlist_videos(playlist_url)
    total = len(urls)

    if total == 0:
        st.warning("재생목록에서 영상을 찾을 수 없습니다.")
    else:
        st.info(f"총 {total}개의 영상이 감지되었습니다.")

        if st.button("전체 영상 다운로드 시작"):
            downloaded_files = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, url in enumerate(urls):
                status_text.text(f"{idx+1}/{total}번째 영상 다운로드 중...")
                filepath = download_video(url)
                if filepath and os.path.exists(filepath):
                    downloaded_files.append(filepath)
                progress_bar.progress((idx + 1) / total)

            status_text.text("모든 영상 다운로드 완료!")
            st.success("🎉 모든 영상 다운로드가 완료되었습니다!")

            st.divider()
            st.subheader("다운로드된 영상 목록")

            for fpath in downloaded_files:
                fname = os.path.basename(fpath)
                with open(fpath, "rb") as f:
                    st.download_button(
                        label=f"📥 {fname} 다운로드",
                        data=f,
                        file_name=fname,
                        mime="video/mp4"
                    )
