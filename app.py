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

ALLOWED_RESOLUTIONS = ["best", "1080p", "360p"]

# yt_dlp 공통 옵션
YDL_COMMON = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": False,
}

@st.cache_data(show_spinner="🔗 재생목록 불러오는 중...")
def fetch_playlist(url):
    with YoutubeDL(YDL_COMMON) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            return [entry['url'] for entry in info['entries']]
        return []

@st.cache_data(show_spinner="📥 영상 메타데이터 가져오는 중...")
def fetch_video_info(url):
    try:
        with YoutubeDL(YDL_COMMON) as ydl:
            info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        resolutions = set()
        for fmt in formats:
            if fmt.get("height"):
                label = f"{fmt.get('height')}p"
                if label in ALLOWED_RESOLUTIONS:
                    resolutions.add(label)
        resolutions = sorted(resolutions, reverse=True)
        if "best" not in resolutions:
            resolutions.insert(0, "best")
        return {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "resolutions": resolutions,
            "url": url
        }
    except Exception:
        return None

def get_thumbnail_image(url):
    try:
        img_data = requests.get(url).content
        return Image.open(BytesIO(img_data))
    except:
        return None

def download_video(url, resolution, status_callback):
    opts = {
        "quiet": True,
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
    }

    if resolution != "best":
        opts["format"] = f"bestvideo[height={resolution[:-1]}]+bestaudio/best[height={resolution[:-1]}]"
    else:
        opts["format"] = "bestvideo+bestaudio/best"

    def hook(d):
        if d['status'] == 'downloading':
            percent = d.get("_percent_str", "").strip()
            status_callback(f"⏬ 다운로드 중... {percent}")
        elif d['status'] == 'finished':
            status_callback("✅ 완료")

    opts["progress_hooks"] = [hook]

    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        status_callback(f"❌ 실패: {str(e)}")

# ✅ 입력
playlist_url = st.text_input("🔗 유튜브 재생목록 URL 입력", "")

if playlist_url:
    video_urls = fetch_playlist(playlist_url)
    total = len(video_urls)

    st.info(f"총 {total}개의 영상이 감지되었습니다.")
    progress_bar = st.progress(0, text="영상 메타데이터 불러오는 중...")

    videos = []
    for idx, url in enumerate(video_urls):
        info = fetch_video_info(url)
        if info:
            videos.append(info)
        progress_bar.progress((idx + 1) / total, text=f"{idx + 1}/{total} 불러오는 중...")
    progress_bar.empty()

    st.success("🎉 모든 영상 정보가 불러와졌습니다!")

    st.subheader("⚙️ 전체 옵션")
    col1, col2 = st.columns(2)
    with col1:
        global_resolution = st.selectbox("전체 해상도 선택", ["best", "1080p", "360p"])
    with col2:
        if st.button("📥 전체 다운로드"):
            for idx, v in enumerate(videos):
                placeholder = st.empty()
                placeholder.text(f"{v['title']} - 대기 중")
                def callback(msg, pl=placeholder):
                    pl.text(f"{v['title']} - {msg}")
                threading.Thread(target=download_video, args=(v["url"], global_resolution, callback)).start()

    st.divider()
    st.subheader("📂 영상 목록")

    for i, v in enumerate(videos):
        with st.container(border=True):
            cols = st.columns([1, 4, 2, 2])
            with cols[0]:
                thumb = get_thumbnail_image(v["thumbnail"])
                if thumb:
                    st.image(thumb.resize((120, 90)), use_container_width=True)
            with cols[1]:
                st.markdown(f"**{v['title']}**")
                if v["duration"]:
                    mins, secs = divmod(v["duration"], 60)
                    st.caption(f"⏱️ {mins}분 {secs}초")
            with cols[2]:
                selected_res = st.selectbox("해상도 선택", v["resolutions"] or ["best"], key=f"res_{i}")
            with cols[3]:
                status_placeholder = st.empty()
                if st.button("⬇️ 다운로드", key=f"dl_{i}"):
                    status_placeholder.text(f"{v['title']} - 대기 중")
                    def update(msg, pl=status_placeholder):
                        pl.text(f"{v['title']} - {msg}")
                    threading.Thread(target=download_video, args=(v["url"], selected_res, update)).start()
