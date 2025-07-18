import streamlit as st
import subprocess
import os
import time
import uuid

st.set_page_config(page_title="YouTube 다운로더")
st.title("🎬 YouTube 영상 다운로드기")

url = st.text_input("YouTube 영상 URL을 입력하세요")
download_type = st.radio("다운로드 방식 선택", ["🎞️ 영상만", "🔊 소리만", "🎥 영상 + 소리"])

quality = st.selectbox("해상도 선택", ["1080p", "720p", "480p", "360p", "자동"], index=1)

if url and st.button("다운로드"):
    try:
        uid = uuid.uuid4().hex[:8]
        filename = f"download_{uid}.mp4"
        audio_filename = f"download_{uid}.m4a"

        quality_flag = {
            "1080p": "bestvideo[height<=1080]+bestaudio",
            "720p": "bestvideo[height<=720]+bestaudio",
            "480p": "bestvideo[height<=480]+bestaudio",
            "360p": "bestvideo[height<=360]+bestaudio",
            "자동": "best"
        }

        with st.spinner("다운로드 중..."):
            start = time.time()

            if download_type == "🎥 영상 + 소리":
                output = subprocess.run([
                    "yt-dlp",
                    "-f", quality_flag[quality],
                    "-o", filename,
                    url
                ], capture_output=True, text=True)

            elif download_type == "🎞️ 영상만":
                output = subprocess.run([
                    "yt-dlp",
                    "-f", f"bestvideo[height<={quality.replace('p', '')}]",
                    "-o", filename,
                    url
                ], capture_output=True, text=True)

            elif download_type == "🔊 소리만":
                output = subprocess.run([
                    "yt-dlp",
                    "-f", "bestaudio",
                    "-o", audio_filename,
                    "--extract-audio",
                    "--audio-format", "mp3",
                    url
                ], capture_output=True, text=True)
                filename = audio_filename.replace(".m4a", ".mp3")

            end = time.time()

        if output.returncode != 0:
            st.error("❌ 다운로드 실패:\n" + output.stderr)
        else:
            st.success(f"다운로드 완료! (소요 시간: {int(end - start)}초)")
            with open(filename, "rb") as f:
                st.download_button("⬇ 파일 다운로드", data=f, file_name=filename)

        # 파일 정리
        for f in [filename, audio_filename]:
            if os.path.exists(f):
                os.remove(f)

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
