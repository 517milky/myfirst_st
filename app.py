import streamlit as st
import os
import threading
from yt_dlp import YoutubeDL
from PIL import Image
from io import BytesIO
import requests

st.set_page_config(layout="wide")
st.title("📥 유튜브 재생목록 다운로드")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FORMAT_OPTIONS = ["영상+소리", "소리만"]
RESOLUTION_OPTIONS = ["best", "1080p", "720p", "480p", "360p", "240p"]

@st.cache_data(show_spinner="🎥 영상 정보 불러오는 중...")
def fetch_video_info(url):
    ydl_opts = {"quiet": True, "skip_download": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def get_playlist_videos(playlist_url):
    ydl_opts = {"quiet": True, "extract_flat": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        return info.get("entries", [])

def get_thumbnail(url):
    try:
        img_data = requests.get(url).content
        return Image.open(BytesIO(img_data))
    except:
        return None

def download_video(url, format_type, resolution, update_progress):
    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "quiet": True,
        "progress_hooks": [lambda d: update_progress(d)],
    }

    if format_type == "소리만":
        ydl_opts["format"] = "bestaudio"
    else:
        ydl_opts["format"] = resolution if resolution != "best" else "bestvideo+bestaudio"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        return False

# 🚀 시작
playlist_url = st.text_input("🔗 유튜브 재생목록 URL 입력")

if playlist_url:
    with st.spinner("🔍 재생목록 불러오는 중..."):
        entries = get_playlist_videos(playlist_url)

    if not entries:
        st.error("❌ 재생목록을 불러올 수 없습니다.")
    else:
        st.success(f"✅ 총 {len(entries)}개의 영상을 불러왔습니다.")
        st.divider()

        st.subheader("⚙️ 전체 옵션 설정")
        col1, col2 = st.columns(2)
        with col1:
            global_format = st.selectbox("전체 형식", FORMAT_OPTIONS)
        with col2:
            global_res = st.selectbox("전체 해상도", RESOLUTION_OPTIONS)

        st.divider()
        st.subheader("📂 영상 목록")

        download_states = ["대기 중"] * len(entries)
        progress_values = [0] * len(entries)

        def create_progress_callback(idx):
            def callback(d):
                if d["status"] == "downloading":
                    percent = d.get("_percent_str", "0.0%").strip()
                    try:
                        val = float(percent.replace("%", ""))
                        progress_values[idx] = val
                        download_states[idx] = f"⏬ 다운로드 중 ({percent})"
                    except:
                        pass
                elif d["status"] == "finished":
                    progress_values[idx] = 100
                    download_states[idx] = "✅ 완료"
            return callback

        for idx, entry in enumerate(entries):
            with st.container(border=True):
                cols = st.columns([1, 3, 2, 2, 2])
                with cols[0]:
                    thumb = get_thumbnail(entry.get("thumbnail", ""))
                    if thumb:
                        st.image(thumb.resize((100, 70)), use_container_width=True)
                with cols[1]:
                    st.markdown(f"**{entry['title']}**")
                with cols[2]:
                    fmt = st.selectbox(f"형식 {idx+1}", FORMAT_OPTIONS, key=f"fmt_{idx}")
                with cols[3]:
                    res = st.selectbox(f"해상도 {idx+1}", RESOLUTION_OPTIONS, key=f"res_{idx}")
                with cols[4]:
                    if st.button("⬇️ 다운로드", key=f"dl_{idx}"):
                        thread = threading.Thread(
                            target=lambda u=entry["url"], i=idx: download_video(
                                u, fmt, res, create_progress_callback(i)
                            )
                        )
                        thread.start()
                st.progress(progress_values[idx] / 100, text=download_states[idx])

        st.divider()
        if st.button("📥 전체 다운로드"):
            for idx, entry in enumerate(entries):
                thread = threading.Thread(
                    target=lambda u=entry["url"], i=idx: download_video(
                        u, global_format, global_res, create_progress_callback(i)
                    )
                )
                thread.start()
