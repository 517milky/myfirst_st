import streamlit as st
import os
import threading
from pytube import YouTube, Playlist
from PIL import Image
from io import BytesIO
import requests
import time

st.set_page_config(layout="wide")
st.title("📥 유튜브 재생목록 다운로드")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FORMAT_OPTIONS = ["영상+소리", "영상만", "소리만"]

def fetch_playlist_urls(playlist_url):
    try:
        pl = Playlist(playlist_url)
        return list(pl.video_urls)
    except Exception:
        return []

@st.cache_data(show_spinner="📥 영상 정보 불러오는 중...")
def fetch_metadata(url):
    try:
        yt = YouTube(url)
        resolutions = list({s.resolution for s in yt.streams.filter(progressive=True, file_extension='mp4') if s.resolution})
        resolutions.sort(reverse=True)
        return {
            "title": yt.title or "제목 불러오기 실패",
            "length": yt.length,
            "thumbnail_url": yt.thumbnail_url,
            "resolutions": resolutions,
            "yt": yt
        }
    except:
        return {
            "title": "❌ 정보 불러오기 실패",
            "length": 0,
            "thumbnail_url": None,
            "resolutions": [],
            "yt": None
        }

def get_thumbnail(url):
    try:
        img_data = requests.get(url, timeout=5).content
        return Image.open(BytesIO(img_data))
    except:
        return None

def download_video(yt, resolution, format_type, progress_callback):
    try:
        if format_type == "영상+소리":
            stream = yt.streams.filter(progressive=True, file_extension='mp4', res=resolution).first()
        elif format_type == "영상만":
            stream = yt.streams.filter(only_video=True, file_extension='mp4', res=resolution).first()
        elif format_type == "소리만":
            stream = yt.streams.filter(only_audio=True).first()
        else:
            return False, "형식 오류"

        if not stream:
            return False, "선택한 해상도 없음"

        total = stream.filesize or 1
        downloaded = 0

        def progress_func(stream, chunk, remaining):
            nonlocal downloaded
            downloaded = total - remaining
            percent = int(downloaded / total * 100)
            progress_callback(percent)

        yt.register_on_progress_callback(progress_func)

        filename = f"{yt.title}.{stream.subtype}"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        stream.download(output_path=DOWNLOAD_DIR, filename=filename)
        return True, filepath
    except Exception as e:
        return False, str(e)

# 🔗 입력
playlist_url = st.text_input("🔗 유튜브 재생목록 URL 입력", "")

if playlist_url:
    video_urls = fetch_playlist_urls(playlist_url)
    total = len(video_urls)

    st.info(f"🔍 총 {total}개의 영상이 감지되었습니다.")
    progress_bar = st.progress(0, text="🎬 영상 목록 불러오는 중...")

    video_data = []
    for idx, url in enumerate(video_urls):
        meta = fetch_metadata(url)
        if meta:
            video_data.append(meta)
        progress_bar.progress((idx + 1) / total, text=f"📦 불러오는 중... ({idx + 1}/{total})")
    progress_bar.empty()

    st.success("🎉 모든 영상 정보가 불러와졌습니다!")

    # 전체 옵션 선택
    st.subheader("⚙️ 전체 옵션")
    col1, col2 = st.columns(2)
    with col1:
        global_format = st.selectbox("전체 다운로드 형식", FORMAT_OPTIONS)
    with col2:
        common_res = list({res for v in video_data for res in v['resolutions']})
        common_res.sort(reverse=True)
        global_res = st.selectbox("전체 해상도 선택", common_res)

    st.divider()
    st.subheader("📂 영상 목록")

    threads = []
    status_states = [("대기 중", 0) for _ in video_data]
    lock = threading.Lock()

    for i, v in enumerate(video_data):
        with st.container(border=True):
            cols = st.columns([1, 3, 2, 2, 2])
            with cols[0]:
                thumb = get_thumbnail(v["thumbnail_url"])
                if thumb:
                    st.image(thumb.resize((90, 60)))
            with cols[1]:
                st.markdown(f"**{v['title']}**")
                mins, secs = divmod(v["length"], 60)
                st.caption(f"⏱️ {mins}분 {secs}초")
            with cols[2]:
                selected_format = st.selectbox(f"형식 {i+1}", FORMAT_OPTIONS, key=f"format_{i}")
            with cols[3]:
                available_res = v["resolutions"]
                default_res = global_res if global_res in available_res else (available_res[0] if available_res else "N/A")
                selected_res = st.selectbox(f"해상도 {i+1}", available_res, index=available_res.index(default_res) if default_res in available_res else 0, key=f"res_{i}")
            with cols[4]:
                if st.button("⬇️ 다운로드", key=f"btn_{i}"):
                    def update_progress(p):
                        with lock:
                            status_states[i] = ("⏬ 다운로드 중", p)
                    def run_download():
                        success, _ = download_video(v["yt"], selected_res, selected_format, update_progress)
                        with lock:
                            status_states[i] = ("✅ 완료" if success else "❌ 실패", 100 if success else 0)
                    thread = threading.Thread(target=run_download)
                    thread.start()
                    threads.append(thread)

            # 진행도 표시
            label, perc = status_states[i]
            st.progress(perc / 100, text=f"{label} ({perc}%)")

    st.divider()

    # 전체 다운로드 버튼
    if st.button("📥 전체 다운로드 시작"):
        for i, v in enumerate(video_data):
            selected_format = global_format
            selected_res = global_res if global_res in v["resolutions"] else (v["resolutions"][0] if v["resolutions"] else "N/A")

            def update_progress(p, index=i):
                with lock:
                    status_states[index] = ("⏬ 다운로드 중", p)

            def run_download(idx=i):
                success, _ = download_video(v["yt"], selected_res, selected_format, lambda p: update_progress(p, idx))
                with lock:
                    status_states[idx] = ("✅ 완료" if success else "❌ 실패", 100 if success else 0)

            thread = threading.Thread(target=run_download)
            thread.start()
            threads.append(thread)
