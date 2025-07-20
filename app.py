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

@st.cache_data(show_spinner="🎥 영상 정보 불러오는 중...")
def fetch_metadata(url):
    try:
        yt = YouTube(url)
        # 지원 해상도는 progressive(영상+소리)만 필터링 후 추출
        progressive_resolutions = [s.resolution for s in yt.streams.filter(progressive=True, file_extension='mp4') if s.resolution]
        # 영상만 스트림 해상도
        video_only_resolutions = [s.resolution for s in yt.streams.filter(only_video=True, file_extension='mp4') if s.resolution]
        # 소리만은 해상도 상관없음
        resolutions = list(set(progressive_resolutions + video_only_resolutions))
        resolutions = [r for r in resolutions if r is not None]
        resolutions.sort(key=lambda x: int(x.replace('p','')), reverse=True)

        return {
            "title": yt.title,
            "length": yt.length,
            "thumbnail_url": yt.thumbnail_url,
            "progressive_res": progressive_resolutions,
            "video_only_res": video_only_resolutions,
            "resolutions": resolutions,
            "yt": yt
        }
    except:
        return None

def get_thumbnail(url):
    try:
        img_data = requests.get(url).content
        return Image.open(BytesIO(img_data))
    except:
        return None

def download_video(yt, resolution, format_type, progress_callback):
    try:
        stream = None
        if format_type == "영상+소리":
            # progressive 스트림 중에서 원하는 해상도
            stream = yt.streams.filter(progressive=True, file_extension='mp4', res=resolution).first()
        elif format_type == "영상만":
            # 영상만 스트림 중 원하는 해상도
            stream = yt.streams.filter(only_video=True, file_extension='mp4', res=resolution).first()
        elif format_type == "소리만":
            # 음성만 스트림 중 최고 비트레이트로 선택
            stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        if not stream:
            return False, "선택한 해상도 또는 형식이 지원되지 않습니다."

        total = stream.filesize or 1
        downloaded = 0

        def progress_func(stream, chunk, bytes_remaining):
            nonlocal downloaded
            downloaded = total - bytes_remaining
            percent = int(downloaded / total * 100)
            progress_callback(percent)

        yt.register_on_progress_callback(progress_func)

        filename = f"{yt.title}.{stream.subtype}"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        stream.download(output_path=DOWNLOAD_DIR, filename=filename)
        return True, filepath
    except Exception as e:
        return False, str(e)

# 입력창
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

    # 전체 옵션 선택
    st.subheader("⚙️ 전체 옵션")
    col1, col2 = st.columns(2)
    with col1:
        global_format = st.selectbox("전체 다운로드 형식", FORMAT_OPTIONS)
    with col2:
        # 모든 영상에서 지원하는 해상도 교집합으로 처리
        if video_data:
            common_res = set(video_data[0]["resolutions"])
            for v in video_data[1:]:
                common_res &= set(v["resolutions"])
            common_res = sorted(common_res, key=lambda x: int(x.replace('p','')), reverse=True)
        else:
            common_res = []
        if common_res:
            global_res = st.selectbox("전체 해상도 선택", common_res)
        else:
            global_res = None

    st.divider()
    st.subheader("📂 영상 목록")

    threads = []
    status_states = [("대기 중", 0) for _ in video_data]
    lock = threading.Lock()

    for i, v in enumerate(video_data):
        with st.container():
            cols = st.columns([1, 4, 2, 2, 2, 2])
            with cols[0]:
                thumb = get_thumbnail(v["thumbnail_url"])
                if thumb:
                    st.image(thumb.resize((120, 80)))
            with cols[1]:
                st.markdown(f"**{v['title']}**")
                mins, secs = divmod(v["length"], 60)
                st.caption(f"⏱️ {mins}분 {secs}초")
            with cols[2]:
                selected_format = st.selectbox(f"형식 {i+1}", FORMAT_OPTIONS, index=FORMAT_OPTIONS.index(global_format), key=f"format_{i}")
            with cols[3]:
                available_res = v["resolutions"]
                # 고화질 지원 안되는 해상도는 선택 불가 처리
                def res_disabled(res):
                    # 영상+소리 형식은 progressive_res에 있어야함
                    if selected_format == "영상+소리":
                        return res not in v["progressive_res"]
                    # 영상만은 video_only_res에 있어야함
                    elif selected_format == "영상만":
                        return res not in v["video_only_res"]
                    # 소리만은 해상도 상관없음 항상 False
                    else:
                        return False
                options = [(r, res_disabled(r)) for r in available_res]
                # 선택 기본값: global_res 있으면 그걸로, 없으면 첫번째
                default_res = global_res if global_res in available_res else (available_res[0] if available_res else None)
                selected_res = st.selectbox(
                    f"해상도 {i+1}",
                    [r for r,_ in options],
                    index=[r for r,_ in options].index(default_res) if default_res else 0,
                    key=f"res_{i}",
                    disabled=[d for _,d in options]
                )
            with cols[4]:
                if st.button("⬇️ 다운로드", key=f"btn_{i}"):
                    def update_progress(p):
                        with lock:
                            status_states[i] = ("⏬ 다운로드 중", p)
                    thread = threading.Thread(
                        target=lambda idx=i, fmt=selected_format, res=selected_res: (
                            download_video(video_data[idx]["yt"], res, fmt, lambda p: update_progress(p)),
                            status_states.__setitem__(idx, ("✅ 완료", 100))
                        )
                    )
                    threads.append(thread)
                    thread.start()
            with cols[5]:
                label, perc = status_states[i]
                st.progress(perc / 100, text=f"{label} ({perc}%)")

    st.divider()

    # 전체 다운로드 버튼
    if st.button("📥 전체 다운로드 시작"):
        for i, v in enumerate(video_data):
            fmt = global_format
            # 개별 영상 해상도 지원여부 체크 후 fallback
            if global_res and global_res in v["resolutions"]:
                res = global_res
            elif v["resolutions"]:
                res = v["resolutions"][0]
            else:
                res = None

            def update_progress(p, index=i):
                with lock:
                    status_states[index] = ("⏬ 다운로드 중", p)

            thread = threading.Thread(
                target=lambda idx=i, fmt=fmt, res=res: (
                    download_video(video_data[idx]["yt"], res, fmt, lambda p: update_progress(p, idx)),
                    status_states.__setitem__(idx, ("✅ 완료", 100))
                )
            )
            threads.append(thread)
            thread.start()
