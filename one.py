import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import time

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("YouTube 영상 다운로드 웹앱")

url = st.text_input("YouTube 영상 링크 입력")

download_type = st.radio("다운로드 방식 선택", ("영상+소리", "영상만", "소리만"))

quality_options = ["144p", "240p", "360p", "480p", "720p", "1080p"]

if download_type == "소리만":
    quality = None
else:
    quality = st.selectbox("해상도 선택", quality_options)

if url:
    with st.spinner("영상 정보 불러오는 중..."):
        try:
            ydl_opts_info = {'quiet': True, 'skip_download': True}
            with YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
            st.video(info["url"], format="video/mp4")
        except Exception:
            st.error("❌ 영상 정보를 불러오지 못했습니다.")
            st.stop()

    if st.button("다운로드 시작"):
        with tempfile.TemporaryDirectory() as tmpdir:
            start_time = time.time()
            status_placeholder = st.empty()
            progress_bar = st.progress(0)

            def progress_hook(d):
                if d["status"] == "downloading":
                    total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded_bytes = d.get("downloaded_bytes", 0)
                    percent = downloaded_bytes / total_bytes if total_bytes else 0
                    elapsed = time.time() - start_time
                    speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                    eta = (total_bytes - downloaded_bytes) / speed if speed > 0 else 0
                    progress_bar.progress(min(percent, 1.0))
                    status_placeholder.text(f"다운로드 진행률: {percent*100:.1f}% | 예상 시간: {int(eta)}초")
                elif d["status"] == "finished":
                    progress_bar.progress(1.0)
                    status_placeholder.text("✅ 다운로드 완료!")

            if download_type == "소리만":
                ydl_opts = {
                    'format': 'bestaudio',
                    'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'progress_hooks': [progress_hook],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                }
            elif download_type == "영상만":
                res_map = {
                    "144p": "160",
                    "240p": "133",
                    "360p": "134",
                    "480p": "135",
                    "720p": "136",
                    "1080p": "137",
                }
                format_code = res_map.get(quality, "134")
                ydl_opts = {
                    'format': format_code,
                    'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'progress_hooks': [progress_hook],
                }
            else:  # 영상+소리
                allowed_heights = ["144", "240", "360", "480"]
                height_num = quality.replace("p","")
                if height_num not in allowed_heights:
                    height_num = "480"
                # 단일 포맷으로 병합 없이 다운로드
                ydl_opts = {
                    'format': f'best[height<={height_num}][vcodec!=none][acodec!=none]/best',
                    'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'progress_hooks': [progress_hook],
                }

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url)
                    filename = ydl.prepare_filename(info)
                with open(filename, "rb") as f:
                    st.download_button("📥 파일 저장", f, file_name=os.path.basename(filename))
            except Exception as e:
                st.error(f"❌ 오류 발생: {e}")
