import streamlit as st
import yt_dlp
import tempfile
import os
import subprocess
import threading
import time
from streamlit.runtime.scriptrunner import add_script_run_ctx
import base64

# ──────────────── 설정 ────────────────
st.set_page_config(page_title="YouTube 다운로드", layout="centered")
st.title("🎬 유튜브 영상 다운로드기")
st.caption("※ 고화질 영상은 준비 및 다운로드에 시간이 다소 소요됩니다.")

# ──────────────── 세션 상태 초기화 ────────────────
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'status_text' not in st.session_state:
    st.session_state.status_text = ""

# ──────────────── 함수 정의 ────────────────
def format_seconds(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}분 {s}초" if m else f"{s}초"

def download_youtube(url, download_type, resolution=None):
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, f"%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": output_path,
        "quiet": True,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "format": "bestaudio/best" if download_type == "audio" else "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "postprocessors": [],
        "noprogress": True,
    }

    if download_type == "audio":
        ydl_opts["format"] = "bestaudio"
        ydl_opts["postprocessors"].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
        output_ext = ".mp3"
    else:
        if resolution:
            ydl_opts["format"] = f"bestvideo[height={resolution}]+bestaudio/best[height={resolution}]"
        output_ext = ".mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get("id", "")
            downloaded_path = os.path.join(temp_dir, f"{video_id}{output_ext}")
            return downloaded_path
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
        return None

def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
        downloaded = d.get('downloaded_bytes', 0)
        percent = int(downloaded / total * 100)
        st.session_state.progress = percent
        eta = d.get('eta')
        if eta:
            st.session_state.status_text = f"⏳ 다운로드 중... {percent}% | 남은 시간: {format_seconds(eta)}"
        else:
            st.session_state.status_text = f"⏳ 다운로드 중... {percent}%"
    elif d['status'] == 'finished':
        st.session_state.status_text = "✅ 다운로드 완료!"

def get_video_info(url):
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        st.error(f"❌ 영상 정보를 불러올 수 없습니다: {e}")
        return None

def run_download(url, download_type, resolution):
    downloaded_file = download_youtube(url, download_type, resolution)
    if downloaded_file:
        st.success("✅ 다운로드가 완료되었습니다.")
        st.write(f"📁 저장 위치: `{downloaded_file}`")
        with open(downloaded_file, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            file_name = os.path.basename(downloaded_file)
            dl_ext = file_name.split(".")[-1]
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">👉 파일 다운로드 ({dl_ext.upper()})</a>'
            st.markdown(href, unsafe_allow_html=True)

# ──────────────── UI ────────────────
url = st.text_input("유튜브 링크를 입력하세요", placeholder="https://www.youtube.com/watch?v=...")
if url:
    info = get_video_info(url)
    if info:
        st.video(url)

        download_type = st.radio("다운로드 방식 선택", ["영상 + 소리", "영상만", "소리만"], horizontal=True)

        resolution = None
        if download_type != "소리만":
            resolutions = sorted({f.get("height") for f in info["formats"] if f.get("height")}, reverse=True)
            common_res = [str(r) + "p" for r in resolutions if r in [2160, 1440, 1080, 720, 480, 360]]
            resolution = st.selectbox("해상도 선택", common_res, index=common_res.index("1080p") if "1080p" in common_res else 0)
            resolution = resolution.replace("p", "")

        if st.button("📥 다운로드 시작"):
            st.session_state.progress = 0
            st.session_state.status_text = "🚀 다운로드 준비 중..."
            progress_bar = st.progress(0)
            status_text = st.empty()

            def threaded_download():
                run_download(url, 
                             "audio" if download_type == "소리만" else ("video" if download_type == "영상만" else "both"), 
                             resolution)
            thread = threading.Thread(target=threaded_download)
            add_script_run_ctx(thread)
            thread.start()

            while thread.is_alive():
                progress_bar.progress(min(st.session_state.progress, 100))
                status_text.markdown(st.session_state.status_text)
                time.sleep(0.5)
            progress_bar.progress(100)
            status_text.markdown("✅ 완료!")
