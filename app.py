import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import threading
import time
import uuid
import shutil

st.set_page_config(page_title="YouTube 다운로더", layout="wide")

DOWNLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "yt_downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ------------------ 유틸 함수 ------------------

def get_video_info(url):
    ydl_opts = {'quiet': True, 'extract_flat': False}
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def get_available_formats(video_info, only_audio=False):
    formats = []
    for fmt in video_info.get("formats", []):
        if only_audio:
            if fmt.get("vcodec") == "none":
                formats.append((fmt["format_id"], fmt["abr"], fmt["ext"]))
        else:
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                if fmt.get("height"):
                    formats.append((fmt["format_id"], fmt["height"], fmt["ext"]))
    return formats

def download_stream(url, format_id, filename, progress_cb):
    def hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            eta = d.get('eta', 0)
            progress_cb(downloaded, total_bytes, eta)
    ydl_opts = {
        'format': format_id,
        'outtmpl': filename,
        'progress_hooks': [hook],
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def format_eta(seconds):
    if not seconds: return "??s"
    minutes = seconds // 60
    return f"{minutes}m {seconds % 60}s" if minutes else f"{seconds}s"

# ------------------ 단일 영상 ------------------

st.title("🎬 YouTube 다운로드 웹앱")

st.subheader("단일 영상 다운로드")
single_url = st.text_input("YouTube 영상 주소를 입력하세요", key="single_input")

if single_url:
    try:
        info = get_video_info(single_url)
        st.video(info["url"])
        format_list = get_available_formats(info)
        format_choice = st.selectbox("해상도 선택", options=[f"{h}p" for _, h, _ in format_list])
        selected_format = [fid for fid, h, _ in format_list if f"{h}p" == format_choice][0]

        if st.button("📥 다운로드"):
            progress = st.progress(0)
            status = st.empty()
            start_time = time.time()

            def update_progress(downloaded, total, eta):
                percent = int((downloaded / total) * 100) if total else 0
                progress.progress(percent)
                status.text(f"{percent}% 진행 중... 예상 시간: {format_eta(eta)}")

            fname = os.path.join(DOWNLOAD_FOLDER, f"{uuid.uuid4()}.mp4")
            download_stream(single_url, selected_format, fname, update_progress)
            status.success(f"다운로드 완료: {fname}")
    except Exception as e:
        st.error(f"에러 발생: {e}")

# ------------------ 재생목록 ------------------

st.subheader("재생목록 다운로드")
playlist_url = st.text_input("YouTube 재생목록 주소를 입력하세요", key="playlist_input")

if playlist_url:
    with st.spinner("재생목록 분석 중..."):
        try:
            ydl_opts = {'quiet': True, 'extract_flat': True}
            with YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(playlist_url, download=False)
            entries = result['entries']
            total = len(entries)

            st.success(f"{total}개의 영상을 불러왔습니다.")

            all_states = {}
            download_progress_bars = {}

            for i, video in enumerate(entries):
                video_url = f"https://www.youtube.com/watch?v={video['id']}"
                container = st.container()
                cols = container.columns([1, 4, 2])
                with cols[0]:
                    st.image(video['thumbnails'][-1]['url'], width=80)
                with cols[1]:
                    toggle = st.toggle(f"{i+1}. {video['title']}", key=f"toggle_{i}")
                with cols[2]:
                    mode = st.selectbox(
                        "방식", ["영상+소리", "영상만", "소리만"], key=f"mode_{i}")
                    if mode != "소리만":
                        try:
                            detail_info = get_video_info(video_url)
                            av_formats = get_available_formats(detail_info, only_audio=False)
                            options = [f"{h}p" for _, h, _ in av_formats]
                            if not options:
                                st.write("❌ 해당 해상도 없음")
                                selected = None
                            else:
                                selected = st.selectbox("해상도", options, key=f"res_{i}")
                        except:
                            selected = None
                    else:
                        selected = "audio"

                # 미리보기 열기
                if toggle:
                    st.video(video_url)

                # 다운로드 버튼
                if st.button(f"⬇️ 다운로드 {i+1}번", key=f"download_{i}"):
                    pb = st.progress(0, text="0%")
                    eta = st.empty()

                    def update(downloaded, total, e):
                        percent = int((downloaded / total) * 100) if total else 0
                        pb.progress(percent, text=f"{percent}%")
                        eta.text(f"예상 시간: {format_eta(e)}")

                    try:
                        detail_info = get_video_info(video_url)
                        if selected == "audio":
                            audio_fmt = get_available_formats(detail_info, only_audio=True)[0][0]
                            file_ext = "mp3"
                            filename = os.path.join(DOWNLOAD_FOLDER, f"{uuid.uuid4()}.{file_ext}")
                            download_stream(video_url, audio_fmt, filename, update)
                        else:
                            fmt_id = [fid for fid, h, _ in get_available_formats(detail_info) if f"{h}p" == selected][0]
                            filename = os.path.join(DOWNLOAD_FOLDER, f"{uuid.uuid4()}.mp4")
                            download_stream(video_url, fmt_id, filename, update)
                        eta.success(f"✅ 완료: {filename}")
                    except Exception as e:
                        eta.error(f"에러 발생: {e}")

        except Exception as e:
            st.error(f"❌ 재생목록 처리 중 에러: {e}")
