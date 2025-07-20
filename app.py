import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import time

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("YouTube 영상 다운로드 웹앱")

url = st.text_input("YouTube 영상 링크 입력")

download_type = st.radio("다운로드 방식 선택", ("영상+소리", "영상만", "소리만"))

def get_available_qualities(url, download_type):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    formats = info.get('formats', [])

    qualities = set()
    if download_type == "소리만":
        return []  # 화질 선택 숨김 처리
    elif download_type == "영상만":
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') == 'none' and f.get('ext') == 'mp4':
                height = f.get('height')
                if height:
                    qualities.add(f"{height}p")
    else:
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                height = f.get('height')
                if height:
                    qualities.add(f"{height}p")

    qualities = list(qualities)
    qualities.sort(key=lambda x: int(x.replace('p','')))
    return qualities

quality = None
if url:
    qualities = get_available_qualities(url, download_type)
    if download_type != "소리만":
        if qualities:
            quality = st.selectbox("해상도 선택", qualities)
        else:
            st.warning("지원하는 해상도가 없습니다.")
            quality = None

if url and (download_type == "소리만" or quality):
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

            ydl_opts = {'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'), 'quiet': True, 'progress_hooks': [progress_hook]}

            if download_type == "소리만":
                ydl_opts.update({
                    'format': 'bestaudio',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            elif download_type == "영상만":
                ydl_opts['format'] = f'bestvideo[height={int(quality.replace("p",""))}][ext=mp4]'
            else:
                ydl_opts['format'] = f'bestvideo[height={int(quality.replace("p",""))}]+bestaudio/best[height={int(quality.replace("p",""))}]'

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url)
                    filename = ydl.prepare_filename(info)
                # 저장 경로 표시 제거했음
                with open(filename, "rb") as f:
                    st.download_button("📥 파일 저장", f, file_name=os.path.basename(filename))
            except Exception as e:
                st.error(f"❌ 오류 발생: {e}")
