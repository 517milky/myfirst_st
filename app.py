import streamlit as st
import yt_dlp
import tempfile
import os
import time
import shutil
from urllib.parse import urlparse, parse_qs
import streamlit.components.v1 as components

st.set_page_config(page_title="YouTube 다운로드 웹앱", layout="wide")

def is_playlist(url):
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    return 'list' in query and 'watch' not in parsed_url.path

def get_video_info(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def get_formats(info, audio_only=False):
    formats = []
    for f in info['formats']:
        if audio_only:
            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                formats.append(f)
        else:
            if f.get('vcodec') != 'none':
                formats.append(f)
    return sorted(formats, key=lambda x: x.get('height', 0), reverse=True)

def show_video_preview(url):
    st.video(url)

def estimate_time(size_bytes, speed_bytes_per_sec):
    if speed_bytes_per_sec == 0:
        return "예상 불가"
    seconds = size_bytes / speed_bytes_per_sec
    return f"{int(seconds)}초"

def download_video(url, format_id, ext, progress_callback):
    ydl_opts = {
        'format': format_id,
        'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
        'merge_output_format': ext,
        'progress_hooks': [progress_callback],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.download([url])
        return info

st.title("YouTube 영상 / 재생목록 다운로드")

url = st.text_input("YouTube 링크 입력", placeholder="https://...")

if url:
    playlist_mode = is_playlist(url)
    st.success("재생목록입니다." if playlist_mode else "단일 영상입니다.")
    
    info = get_video_info(url)

    if playlist_mode:
        entries = info.get('entries', [])
        selected_videos = st.multiselect(
            "다운로드할 영상을 선택하세요:",
            options=[(i, v['title']) for i, v in enumerate(entries)],
            format_func=lambda x: entries[x[0]]['title']
        )

        if selected_videos:
            with st.spinner("다운로드 준비 중..."):
                for idx, _ in selected_videos:
                    video = entries[idx]
                    show_video_preview(video['webpage_url'])
                    subcol1, subcol2 = st.columns([3, 1])
                    with subcol1:
                        download_type = st.selectbox(f"{video['title']} - 다운로드 방식", ['영상+소리', '영상만', '소리만'], key=video['id'])
                        formats = get_formats(video, audio_only=(download_type == '소리만'))

                        if download_type != '소리만':
                            res_options = [f"{f['height']}p" for f in formats if 'height' in f]
                            chosen = st.selectbox("해상도 선택", res_options, key="res_"+video['id'])
                            selected_format = next((f for f in formats if f.get('height') and f"{f['height']}p" == chosen), formats[0])
                        else:
                            selected_format = formats[0]

                        ext = 'mp3' if download_type == '소리만' else 'mp4'
                        st.write(f"선택한 확장자: `{ext}`")

                    with subcol2:
                        download_btn = st.button("다운로드", key="dl_"+video['id'])
                        if download_btn:
                            progress = st.progress(0)
                            status = st.empty()
                            bytes_downloaded = 0
                            total_bytes = selected_format.get('filesize', 1)

                            def hook(d):
                                nonlocal bytes_downloaded, total_bytes
                                if d['status'] == 'downloading':
                                    bytes_downloaded = d.get('downloaded_bytes', 0)
                                    total_bytes = d.get('total_bytes', 1)
                                    percent = int(bytes_downloaded / total_bytes * 100)
                                    progress.progress(min(percent, 100))
                                    eta = estimate_time(total_bytes, d.get('speed', 1))
                                    status.text(f"{percent}% | 예상 소요 시간: {eta}")

                                if d['status'] == 'finished':
                                    status.text("다운로드 완료!")

                            download_video(video['webpage_url'], selected_format['format_id'], ext, hook)
    else:
        show_video_preview(info['webpage_url'])

        download_type = st.radio("다운로드 방식", ['영상+소리', '영상만', '소리만'])
        formats = get_formats(info, audio_only=(download_type == '소리만'))

        if download_type != '소리만':
            res_options = [f"{f['height']}p" for f in formats if 'height' in f]
            chosen = st.selectbox("해상도 선택", res_options)
            selected_format = next((f for f in formats if f.get('height') and f"{f['height']}p" == chosen), formats[0])
        else:
            selected_format = formats[0]

        ext = 'mp3' if download_type == '소리만' else 'mp4'
        st.write(f"다운로드 확장자: `{ext}`")

        if st.button("다운로드 시작"):
            progress = st.progress(0)
            status = st.empty()
            bytes_downloaded = 0
            total_bytes = selected_format.get('filesize', 1)

            def hook(d):
                nonlocal bytes_downloaded, total_bytes
                if d['status'] == 'downloading':
                    bytes_downloaded = d.get('downloaded_bytes', 0)
                    total_bytes = d.get('total_bytes', 1)
                    percent = int(bytes_downloaded / total_bytes * 100)
                    progress.progress(min(percent, 100))
                    eta = estimate_time(total_bytes, d.get('speed', 1))
                    status.text(f"{percent}% | 예상 소요 시간: {eta}")
                if d['status'] == 'finished':
                    status.text("다운로드 완료!")

            download_video(url, selected_format['format_id'], ext, hook)
            st.success(f"저장 위치: `{tempfile.gettempdir()}`")
