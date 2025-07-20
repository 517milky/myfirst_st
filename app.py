import streamlit as st
import os
from yt_dlp import YoutubeDL
from pytube import Playlist
import threading
import zipfile
import shutil

st.set_page_config(layout="wide")
st.title("📥 유튜브 재생목록 전체 다운로드 (폴더 → ZIP)")

BASE_DOWNLOAD_DIR = "downloads"
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

playlist_url = st.text_input("🔗 유튜브 재생목록 URL 입력")

def get_playlist_videos(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        return playlist.video_urls
    except Exception as e:
        st.error(f"재생목록 불러오기 실패: {e}")
        return []

def download_video(url, output_dir):
    ydl_opts = {
        "format": "best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
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

def zip_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_path):
            for f in files:
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, folder_path)
                zf.write(abs_path, rel_path)

if playlist_url:
    urls = get_playlist_videos(playlist_url)
    total = len(urls)

    if total == 0:
        st.warning("재생목록에서 영상을 찾을 수 없습니다.")
    else:
        st.info(f"총 {total}개의 영상이 감지되었습니다.")

        if st.button("전체 영상 다운로드 및 ZIP 생성 시작"):
            # 재생목록별 다운로드 폴더 생성 (playlist 명 대신 임의명)
            playlist_dir = os.path.join(BASE_DOWNLOAD_DIR, "playlist_download")
            if os.path.exists(playlist_dir):
                shutil.rmtree(playlist_dir)
            os.makedirs(playlist_dir, exist_ok=True)

            progress_bar = st.progress(0)
            status_text = st.empty()

            downloaded_files = []
            for idx, url in enumerate(urls):
                status_text.text(f"{idx+1}/{total}번째 영상 다운로드 중...")
                filepath = download_video(url, playlist_dir)
                if filepath and os.path.exists(filepath):
                    downloaded_files.append(filepath)
                progress_bar.progress((idx + 1) / total)

            status_text.text("모든 영상 다운로드 완료!")
            st.success("🎉 모든 영상 다운로드가 완료되었습니다!")

            # zip 파일 경로
            zip_path = os.path.join(BASE_DOWNLOAD_DIR, "playlist_videos.zip")

            # 기존 zip 파일 삭제
            if os.path.exists(zip_path):
                os.remove(zip_path)

            status_text.text("ZIP 파일 생성 중...")
            zip_folder(playlist_dir, zip_path)
            status_text.text("ZIP 파일 생성 완료!")

            # ZIP 다운로드 버튼
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="📥 전체 영상 ZIP 파일 다운로드",
                    data=f,
                    file_name="playlist_videos.zip",
                    mime="application/zip"
                )
