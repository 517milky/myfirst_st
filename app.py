import streamlit as st
import subprocess
import os
import uuid
import time
from yt_dlp import YoutubeDL
import threading

# 다운로드 폴더
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="YouTube Downloader", layout="centered")

st.markdown("## 🎬 YouTube Downloader (yt_dlp 기반)")
url = st.text_input("YouTube 영상 URL을 입력하세요")

download_type = st.selectbox("다운로드 방식 선택", ["영상 + 소리", "영상만", "소리만"])
ext_default = "mp4" if download_type != "소리만" else "mp3"
file_ext = st.selectbox("저장 확장자", ["mp4", "webm", "mkv", "mp3"], index=["mp4", "webm", "mkv", "mp3"].index(ext_default))

quality = None
if download_type != "소리만":
    quality = st.selectbox("해상도 선택", ["1080p", "720p", "480p", "360p"])

if url:
    st.video(url, format="video/mp4")

    if st.button("다운로드 시작"):
        progress_text = st.empty()
        progress_bar = st.progress(0)

        def download():
            try:
                temp_id = str(uuid.uuid4())
                output_template = os.path.join(DOWNLOAD_DIR, f"{temp_id}.%(ext)s")
                
                # 형식 조건
                if download_type == "소리만":
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': output_template,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': file_ext,
                        }],
                        'noplaylist': True,
                        'quiet': True,
                        'progress_hooks': [progress_hook],
                        'merge_output_format': None
                    }
                elif download_type == "영상만":
                    res_map = {"1080p": "bestvideo[height<=1080]", "720p": "bestvideo[height<=720]", "480p": "bestvideo[height<=480]", "360p": "bestvideo[height<=360]"}
                    ydl_opts = {
                        'format': res_map[quality],
                        'outtmpl': output_template,
                        'noplaylist': True,
                        'quiet': True,
                        'progress_hooks': [progress_hook],
                        'merge_output_format': None
                    }
                else:  # 영상 + 소리
                    res_map = {"1080p": "bestvideo[height<=1080]+bestaudio", "720p": "bestvideo[height<=720]+bestaudio", "480p": "bestvideo[height<=480]+bestaudio", "360p": "bestvideo[height<=360]+bestaudio"}
                    ydl_opts = {
                        'format': res_map[quality],
                        'outtmpl': output_template,
                        'noplaylist': True,
                        'quiet': True,
                        'progress_hooks': [progress_hook],
                        'merge_output_format': None
                    }

                # 다운로드 시간 측정
                start_time = time.time()
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                elapsed = time.time() - start_time

                # 실제 파일 경로 탐색
                for f in os.listdir(DOWNLOAD_DIR):
                    if f.startswith(temp_id):
                        file_path = os.path.join(DOWNLOAD_DIR, f)
                        break

                progress_bar.progress(100)
                progress_text.markdown(f"✅ **다운로드 완료!** 파일 경로: `{file_path}` (소요시간: {int(elapsed)}초)")

                with open(file_path, "rb") as file:
                    st.download_button(
                        label="📥 파일 저장하기",
                        data=file,
                        file_name=os.path.basename(file_path),
                        mime="application/octet-stream"
                    )

            except Exception as e:
                progress_text.error(f"❌ 오류 발생: {e}")

        # 진행률 갱신
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    percent = int(downloaded / total * 100)
                    eta = d.get('eta', '?')
                    progress_bar.progress(percent)
                    progress_text.markdown(f"🔄 진행 중: **{percent}%**, 예상 남은 시간: **{eta}초**")
            elif d['status'] == 'finished':
                progress_bar.progress(100)
                progress_text.markdown("🛠️ 다운로드 준비 완료...")

        # 다운로드 시작 (스레드 분리로 UI 멈춤 방지)
        threading.Thread(target=download).start()
