import streamlit as st
import yt_dlp
import os
import shutil
import uuid
import tempfile
import time
from datetime import timedelta
import streamlit.components.v1 as components

st.set_page_config(page_title="YouTube 다운로드 앱", layout="wide")

# ----------------------------------------
# 기본 설정
# ----------------------------------------
DOWNLOAD_ROOT = os.path.join(tempfile.gettempdir(), "yt_downloads")
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)


def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def get_video_info(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def get_playlist_items(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'force_generic_extractor': False
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(playlist_url, download=False)
        return info_dict.get('entries', []), info_dict.get('title', "playlist")


def download_stream(video_url, quality, mode, file_ext):
    download_id = str(uuid.uuid4())[:8]
    output_dir = os.path.join(DOWNLOAD_ROOT, download_id)
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.time()

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, f'%(title)s.%(ext)s'),
        'quiet': True,
        'format': 'best',
        'noplaylist': True,
        'progress_hooks': [],
    }

    if mode == "영상+소리":
        ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'
    elif mode == "영상만":
        ydl_opts['format'] = f'bestvideo[height<={quality}]'
    elif mode == "소리만":
        ydl_opts['format'] = 'bestaudio'

    if file_ext == "mp3":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]

    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes', 1)
            downloaded = d.get('downloaded_bytes', 0)
            percent = int(downloaded / total_bytes * 100)
            eta = d.get("eta", 0)
            status_text.text(f"{percent}% | 예상 남은 시간: {timedelta(seconds=eta)}")
            progress_bar.progress(percent)
        elif d['status'] == 'finished':
            status_text.text("✅ 다운로드 완료됨")

    ydl_opts['progress_hooks'].append(progress_hook)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        status_text.error(f"⚠️ 오류 발생: {e}")
        return None

    end_time = time.time()
    duration = timedelta(seconds=int(end_time - start_time))
    progress_bar.empty()
    status_text.text(f"🎉 완료! 총 소요 시간: {duration}")

    for f in os.listdir(output_dir):
        if f.endswith(file_ext):
            return os.path.join(output_dir, f)
    return None


# ----------------------------------------
# 앱 UI 시작
# ----------------------------------------

st.title("YouTube 재생목록 다운로드")

tab1, tab2 = st.tabs(["🎥 단일 영상", "📑 재생목록"])

# -----------------------------
# 📑 재생목록 다운로드
# -----------------------------
with tab2:
    playlist_url = st.text_input("재생목록 링크를 입력하세요", placeholder="https://www.youtube.com/playlist?list=...")
    if playlist_url:
        with st.spinner("재생목록 분석 중..."):
            try:
                entries, playlist_title = get_playlist_items(playlist_url)
                if not entries:
                    st.warning("재생목록이 비어있거나 잘못된 링크입니다.")
                else:
                    st.success(f"{len(entries)}개의 영상 발견됨")

                    selected_video = st.selectbox(
                        "처리할 영상을 선택하세요", [f"{i+1}. {v['url'].split('v=')[-1]}" for i, v in enumerate(entries)]
                    )

                    if selected_video:
                        idx = int(selected_video.split(".")[0]) - 1
                        video_url = f"https://www.youtube.com/watch?v={entries[idx]['id']}"
                        st.video(video_url)

                        mode = st.selectbox("다운로드 방식", ["영상+소리", "영상만", "소리만"])
                        ext = "mp3" if mode == "소리만" else "mp4"

                        if mode != "소리만":
                            quality = st.selectbox("해상도 선택", ["144", "240", "360", "480", "720", "1080", "1440", "2160"], index=5)
                        else:
                            quality = None

                        if st.button("다운로드 시작"):
                            file_path = download_stream(video_url, quality, mode, ext)
                            if file_path:
                                st.success(f"파일 저장됨: {file_path}")
                                with open(file_path, "rb") as f:
                                    st.download_button("📥 파일 다운로드", data=f, file_name=os.path.basename(file_path))

            except Exception as e:
                st.error(f"오류 발생: {e}")
