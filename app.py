import streamlit as st
import yt_dlp
import os
import tempfile
import time
import threading
from urllib.parse import urlparse, parse_qs
import shutil

st.set_page_config(page_title="YouTube Downloader", layout="wide")

def is_playlist(url):
    query = parse_qs(urlparse(url).query)
    return 'list' in query

def format_bytes(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"

def get_video_info(url):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'force_generic_extractor': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def download_video(entry, download_type, resolution, output_dir, ext, progress_callback):
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'progress_hooks': [progress_callback],
        'quiet': True,
        'merge_output_format': ext,
    }

    if download_type == 'video+audio':
        ydl_opts['format'] = f'bestvideo[ext=mp4][height<={resolution}]+bestaudio[ext=m4a]/best[ext=mp4]'
    elif download_type == 'video':
        ydl_opts['format'] = f'bestvideo[ext=mp4][height<={resolution}]'
    elif download_type == 'audio':
        ydl_opts['format'] = 'bestaudio[ext=m4a]'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([entry['url']])

def download_with_progress(entry, download_type, resolution, ext, output_dir, slot):
    bytes_downloaded = 0
    total_bytes = 0
    start_time = time.time()

    def progress_hook(d):
        nonlocal bytes_downloaded, total_bytes
        if d['status'] == 'downloading':
            bytes_downloaded = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            elapsed = time.time() - start_time
            speed = bytes_downloaded / elapsed if elapsed > 0 else 0
            percent = (bytes_downloaded / total_bytes) * 100 if total_bytes else 0
            remaining = (total_bytes - bytes_downloaded) / speed if speed > 0 else 0
            slot.progress(percent / 100)
            slot.text(f"{percent:.1f}% • {format_bytes(bytes_downloaded)} / {format_bytes(total_bytes)} • 남은 시간: {remaining:.1f}초")

    try:
        download_video(entry, download_type, resolution, output_dir, ext, progress_hook)
        slot.text("✅ 다운로드 완료")
    except Exception as e:
        slot.text(f"❌ 실패: {str(e)}")

st.title("YouTube Downloader")

url = st.text_input("YouTube 영상 또는 재생목록 URL을 입력하세요:")

if url:
    if is_playlist(url):
        st.subheader("🎞️ 재생목록 영상들")

        info = get_video_info(url)
        videos = info.get('entries', [])
        temp_dir = tempfile.mkdtemp()
        folder_name = info.get('title') or 'YouTubePlaylist'
        output_dir = os.path.join(temp_dir, folder_name)
        os.makedirs(output_dir, exist_ok=True)

        selection = {}
        st.caption("아래에서 개별 영상마다 다운로드 방식 및 화질을 선택할 수 있습니다.")
        for i, video in enumerate(videos):
            with st.expander(f"{i+1}. {video['title']}", expanded=False):
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.video(f"https://www.youtube.com/watch?v={video['id']}")
                with col2:
                    download_type = st.selectbox(
                        f"다운로드 방식 ({video['title'][:15]}...)", 
                        ["video+audio", "video", "audio"], key=f"type_{i}"
                    )

                    if download_type == 'audio':
                        resolution = 'audio_only'
                        ext = 'mp3'
                    else:
                        resolution = st.selectbox("해상도 선택", ["2160", "1440", "1080", "720", "480", "360", "240", "144"], key=f"res_{i}")
                        ext = 'mp4'

                    selection[video['url']] = {
                        'entry': video,
                        'type': download_type,
                        'res': resolution,
                        'ext': ext,
                        'status_slot': st.empty()
                    }

        if st.button("전체 다운로드 시작"):
