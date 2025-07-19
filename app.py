import streamlit as st
from yt_dlp import YoutubeDL
import os
import uuid
import time
import shutil

st.set_page_config(page_title="YouTube Downloader", layout="centered")
st.title("🎬 YouTube 영상 다운로드기")

url = st.text_input("YouTube 링크를 입력하세요.")

# 선택 옵션
download_type = st.radio("다운로드 방식 선택", ["🎥 영상 + 소리", "🎞 영상만", "🔊 소리만"])

# 화질 선택 (영상+소리 or 영상만)
quality = None
if download_type in ["🎥 영상 + 소리", "🎞 영상만"]:
    quality = st.selectbox("화질 선택", ["1080p", "720p", "480p", "360p", "240p", "144p"], index=1)

# 확장자 설정
if download_type == "🔊 소리만":
    default_ext = "mp3"
    audio_ext = st.selectbox("확장자 선택", ["mp3", "wav", "m4a"], index=0)
elif download_type in ["🎥 영상 + 소리", "🎞 영상만"]:
    default_ext = "mp4"
    video_ext = st.selectbox("확장자 선택", ["mp4", "mkv", "webm"], index=0)

# 썸네일 및 정보 출력
if url:
    try:
        ydl = YoutubeDL({'quiet': True})
        info = ydl.extract_info(url, download=False)
        st.subheader(info['title'])
        st.markdown(f"채널: {info.get('uploader', 'N/A')}  \n길이: {int(info['duration'] // 60)}분 {int(info['duration'] % 60)}초")
        if 'thumbnail' in info:
            st.image(info['thumbnail'], use_container_width=True)
    except Exception as e:
        st.error(f"❌ 영상 정보를 불러올 수 없습니다: {e}")
        st.stop()

if st.button("📥 다운로드 시작"):
    if not url:
        st.warning("URL을 먼저 입력하세요.")
        st.stop()

    start_time = time.time()
    with st.spinner("다운로드 중..."):

        temp_id = str(uuid.uuid4())[:8]
        output_dir = f"downloads_{temp_id}"
        os.makedirs(output_dir, exist_ok=True)

        if download_type == "🎥 영상 + 소리":
            format_selector = f"bestvideo[height<={quality[:-1]}]+bestaudio/best"
            ext = video_ext
        elif download_type == "🎞 영상만":
            format_selector = f"bestvideo[height<={quality[:-1]}]"
            ext = video_ext
        else:
            format_selector = "bestaudio"
            ext = audio_ext

        output_template = os.path.join(output_dir, f"output.%(ext)s")

        ydl_opts = {
            'format': format_selector,
            'outtmpl': output_template,
            'quiet': True,
            'merge_output_format': ext if download_type == "🎥 영상 + 소리" else None,
            'postprocessors': []
        }

        if download_type == "🔊 소리만":
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': ext,
                'preferredquality': '192',
            })

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # 다운로드한 파일 찾기
            downloaded_files = os.listdir(output_dir)
            if not downloaded_files:
                st.error("❌ 다운로드된 파일을 찾을 수 없습니다.")
                shutil.rmtree(output_dir)
                st.stop()

            file_path = os.path.join(output_dir, downloaded_files[0])
            filename = f"youtube_download.{ext}"
            end_time = time.time()

            st.success(f"✅ 다운로드 완료! (소요 시간: {int(end_time - start_time)}초)")
            with open(file_path, 'rb') as f:
                st.download_button("📁 파일 다운로드", f, file_name=filename)

        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
        finally:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
