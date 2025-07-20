import streamlit as st
import yt_dlp
import tempfile
import os
import threading
import time
from datetime import timedelta
import urllib.parse

st.set_page_config(page_title="YouTube Downloader", layout="centered")

st.title("🎬 YouTube Downloader")

url = st.text_input("🔗 YouTube 링크를 입력하세요:")

download_type = st.radio(
    "💾 다운로드 방식 선택",
    ("영상+소리", "영상만", "소리만"),
    horizontal=True
)

quality_options = ["144p", "360p", "480p", "720p", "1080p", "2160p"]
quality = None
if download_type != "소리만":
    quality = st.selectbox("📺 원하는 화질을 선택하세요:", quality_options)
else:
    st.markdown("🎵 **최고 음질로 고정됩니다.**")

# 영상 미리보기 iframe
def embed_video(video_id):
    st.components.v1.html(
        f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" '
        'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
        'gyroscope; picture-in-picture" allowfullscreen></iframe>', height=315
    )

def format_eta(seconds):
    return str(timedelta(seconds=int(seconds)))

def download_progress(d):
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        percent = downloaded / total_bytes if total_bytes else 0
        speed = d.get('speed', 0)
        eta = d.get('eta', 0)

        if speed:
            time_remaining = format_eta(eta)
            download_progress_bar.progress(min(int(percent * 100), 100))
            st.session_state["download_status"] = f"🔄 {int(percent * 100)}% 완료, 예상 시간: {time_remaining}"
        else:
            st.session_state["download_status"] = "🔄 다운로드 중..."

    elif d['status'] == 'finished':
        st.session_state["download_status"] = "✅ 다운로드 완료!"

def get_video_info(video_url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info
    except Exception as e:
        st.error(f"❌ 영상 정보를 불러올 수 없습니다: {e}")
        return None

if url:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    video_id = query.get("v", [""])[0]
    if video_id:
        embed_video(video_id)
    else:
        st.warning("⚠️ 올바른 유튜브 링크를 입력해주세요.")

    info = get_video_info(url)
    if info:
        st.subheader(f"📄 영상 제목: {info['title']}")
        st.markdown(f"🕒 길이: {int(info['duration'] // 60)}분 {int(info['duration'] % 60)}초")

    if st.button("⬇️ 다운로드 시작"):
        download_progress_bar = st.progress(0)
        st.session_state["download_status"] = "⏳ 다운로드 준비 중..."
        status_placeholder = st.empty()

        ydl_opts = {
            'progress_hooks': [download_progress],
            'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'format': None,
        }

        if download_type == "영상+소리":
            ydl_opts['format'] = f"bestvideo[height<={quality.replace('p','')}]+bestaudio/best"
        elif download_type == "영상만":
            ydl_opts['format'] = f"bestvideo[height<={quality.replace('p','')}]"
        else:  # 소리만
            ydl_opts['format'] = "bestaudio"

        def run_download():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                st.session_state["download_finished"] = True
            except Exception as e:
                st.error(f"❌ 오류 발생: {e}")
                st.session_state["download_finished"] = False

        st.session_state["download_finished"] = False
        thread = threading.Thread(target=run_download)
        thread.start()

        while thread.is_alive():
            time.sleep(0.5)
            status_placeholder.markdown(st.session_state.get("download_status", "🔄 다운로드 진행 중..."))

        if st.session_state["download_finished"]:
            # 다운로드된 파일 찾기
            downloaded_files = [
                f for f in os.listdir(tempfile.gettempdir())
                if f.lower().endswith(".mp4") or f.lower().endswith(".webm") or f.lower().endswith(".m4a") or f.lower().endswith(".mp3")
            ]
            downloaded_files.sort(key=lambda f: os.path.getmtime(os.path.join(tempfile.gettempdir(), f)), reverse=True)

            if downloaded_files:
                file_path = os.path.join(tempfile.gettempdir(), downloaded_files[0])
                st.success("✅ 다운로드가 완료되었습니다!")
                st.write(f"📁 저장 위치: `{file_path}`")
                with open(file_path, "rb") as f:
                    st.download_button(
                        label="📥 파일 다운로드",
                        data=f,
                        file_name=os.path.basename(file_path),
                        mime="video/mp4" if file_path.endswith(".mp4") else "audio/mp3"
                    )
            else:
                st.error("❌ 다운로드된 파일을 찾을 수 없습니다.")
