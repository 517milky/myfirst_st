import streamlit as st
import os
import subprocess
import uuid
import glob
import time
import json

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("🎬 YouTube 영상 다운로드기")

def clean_url(url):
    if url.startswith("https://wwwyoutube.streamlit.app"):
        url = url.replace("https://wwwyoutube.streamlit.app", "https://www.youtube.com")
    elif url.startswith("https://wwwyoutube"):
        url = url.replace("wwwyoutube", "www.youtube")
    return url

url_input = st.text_input("YouTube 영상 URL을 입력하세요:")

download_type = st.radio("다운로드 방식 선택", ["🎞️ 영상만", "🔊 소리만", "🎥 영상 + 소리"])

quality = None
if download_type in ["🎞️ 영상만", "🎥 영상 + 소리"]:
    quality = st.selectbox("화질 선택", ["1080p", "720p", "480p", "360p", "자동"])

def get_ytdlp_cmd(url, dtype, quality, uid):
    base_cmd = ["yt-dlp", "-o", f"yt_{uid}.%(ext)s", url]

    if dtype == "🎥 영상 + 소리":
        if quality == "자동":
            base_cmd += ["-f", "bestvideo+bestaudio"]
        else:
            base_cmd += ["-f", f"bv[height<={quality.replace('p','')}]+ba/b[height<={quality.replace('p','')}]"]
    elif dtype == "🎞️ 영상만":
        if quality == "자동":
            base_cmd += ["-f", "bestvideo"]
        else:
            base_cmd += ["-f", f"bv[height<={quality.replace('p','')}]"]
    elif dtype == "🔊 소리만":
        base_cmd += ["-f", "bestaudio"]

    base_cmd += ["--merge-output-format", "mp4", "--no-warnings", "--no-playlist"]
    return base_cmd

def get_video_info(url):
    cmd = ["yt-dlp", "--skip-download", "--print", "%(title)s||%(thumbnail)s||%(duration_string)s", url]
    try:
        output = subprocess.check_output(cmd, text=True).strip()
        title, thumbnail, duration = output.split("||")
        return {"title": title, "thumbnail": thumbnail, "duration": duration}
    except Exception as e:
        return None

if url_input:
    url = clean_url(url_input)
    info = get_video_info(url)

    if info:
        st.image(info["thumbnail"], use_column_width=True)
        st.markdown(f"**제목:** {info['title']}")
        st.markdown(f"**재생시간:** {info['duration']}")
    else:
        st.warning("⚠️ 영상을 불러오는 데 실패했습니다.")

    uid = uuid.uuid4().hex[:8]

    if st.button("다운로드 시작"):
        status_placeholder = st.empty()
        progress_bar = st.progress(0)

        estimated_time_map = {"1080p": "15~30초", "720p": "10~20초", "480p": "8~15초", "360p": "5~10초", "자동": "10~20초"}
        estimated_time = estimated_time_map.get(quality, "10~20초")

        status_placeholder.info(f"⏳ 다운로드 중... 예상 소요 시간: {estimated_time}")

        cmd = get_ytdlp_cmd(url, download_type, quality, uid)

        start_time = time.time()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        line_count = 0
        for line in process.stdout:
            line_count += 1
            if line_count % 10 == 0:
                progress = min(line_count // 5, 100)
                progress_bar.progress(progress)

        process.wait()
        end_time = time.time()

        if process.returncode != 0:
            status_placeholder.error("❌ 다운로드 실패. 로그를 확인하세요.")
        else:
            progress_bar.progress(100)
            status_placeholder.success(f"✅ 다운로드 완료! (실제 소요 시간: {int(end_time - start_time)}초)")

            files = glob.glob(f"yt_{uid}.*")
            if not files:
                st.error("❌ 다운로드된 파일을 찾을 수 없습니다.")
            else:
                filepath = files[0]
                ext = os.path.splitext(filepath)[-1].lower()
                if download_type == "🔊 소리만":
                    final_name = f"{info['title']}.mp3"
                    mime = "audio/mp3"
                else:
                    final_name = f"{info['title']}.mp4"
                    mime = "video/mp4"

                with open(filepath, "rb") as f:
                    st.download_button("📥 파일 다운로드", data=f, file_name=final_name, mime=mime)

                os.remove(filepath)
