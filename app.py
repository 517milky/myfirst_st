import streamlit as st
from yt_dlp import YoutubeDL
from PIL import Image
import requests
from io import BytesIO
import threading
import os
import time

st.set_page_config(page_title="YouTube 재생목록 다운로더", layout="wide")
st.title("📥 YouTube 재생목록 다운로드")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FORMAT_OPTIONS = ["영상+소리", "영상만", "소리만"]

# --- 영상 정보 추출 ---
@st.cache_data(show_spinner=False)
def fetch_playlist_info(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    entries = info.get('entries', [])
    title = info.get('title', '재생목록')
    return entries, title

@st.cache_data(show_spinner=False)
def fetch_video_details(video_url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
    return info

def get_thumbnail_image(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

def format_duration(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m)}분 {int(s)}초"

# --- 다운로드 함수 ---
def download_video(info, format_choice, resolution, progress_callback=None):
    url = info['webpage_url']

    # 영상+소리, 영상만, 소리만 필터링 포맷 지정
    if format_choice == "영상+소리":
        # best video+audio with height limit
        if resolution == "최고":
            fmt = "bestvideo+bestaudio/best"
        else:
            height_num = int(resolution.replace("p",""))
            fmt = f"bestvideo[height<={height_num}]+bestaudio/best"
    elif format_choice == "영상만":
        if resolution == "최고":
            fmt = "bestvideo"
        else:
            height_num = int(resolution.replace("p",""))
            fmt = f"bestvideo[height<={height_num}]"
    elif format_choice == "소리만":
        fmt = "bestaudio"
    else:
        fmt = "best"

    ydl_opts = {
        'format': fmt,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'quiet': True,
        'progress_hooks': [],
        'noplaylist': True,
    }

    if progress_callback:
        def hook(d):
            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                if total_bytes:
                    percent = downloaded_bytes / total_bytes
                    progress_callback(percent)
            elif d['status'] == 'finished':
                progress_callback(1.0)
        ydl_opts['progress_hooks'] = [hook]

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True, ""
    except Exception as e:
        return False, str(e)

# --- UI ---

playlist_url = st.text_input("유튜브 재생목록 URL을 입력하세요")

if playlist_url:
    with st.spinner("재생목록 정보 불러오는 중..."):
        entries, playlist_title = fetch_playlist_info(playlist_url)

    if not entries:
        st.error("재생목록을 불러올 수 없거나 비어 있습니다.")
    else:
        st.success(f"총 {len(entries)}개의 영상이 발견되었습니다.")
        st.markdown(f"### 재생목록명: {playlist_title}")

        # 전체 옵션
        st.markdown("### 전체 다운로드 옵션")
        global_format = st.selectbox("전체 다운로드 형식 선택", FORMAT_OPTIONS, index=0)
        global_res_input = ["최고", "1080p", "720p", "480p", "360p", "240p", "144p"]
        global_resolution = st.selectbox("전체 해상도 선택 (소리만 선택 시 무시됨)", global_res_input, index=0)

        # 영상별 옵션 저장
        video_settings = []

        st.markdown("### 영상 목록")
        container = st.container()

        for i, entry in enumerate(entries):
            video_url = entry.get('url') or entry.get('id')
            if not video_url:
                continue

            # 상세정보 한번씩만 불러오기 (필요하면 개선 가능)
            video_info = fetch_video_details(video_url)
            if not video_info:
                continue

            cols = container.columns([1, 4, 2, 2, 2])

            # 썸네일
            thumb_url = video_info.get('thumbnail', None)
            if thumb_url:
                thumb_img = get_thumbnail_image(thumb_url)
                if thumb_img:
                    cols[0].image(thumb_img.resize((120, 70)), use_column_width=False)

            # 제목 및 길이
            cols[1].write(f"**{video_info.get('title', '제목 없음')}**")
            duration = video_info.get('duration', 0)
            cols[1].write(f"⏰ {format_duration(duration)}")

            # 다운로드 형식 선택 (기본 전체 옵션에 따름)
            format_sel = cols[2].selectbox(f"형식 {i}", FORMAT_OPTIONS, index=FORMAT_OPTIONS.index(global_format), key=f"format_{i}")

            # 해상도 선택: 소리만이면 선택 불가 처리
            if format_sel == "소리만":
                cols[3].write("해상도 없음")
                resolution_sel = "최고"
            else:
                # 해당 영상의 mp4 해상도 목록 구하기
                ydl_opts = {'quiet': True, 'skip_download': True}
                with YoutubeDL(ydl_opts) as ydl:
                    formats = ydl.extract_info(video_url, download=False)['formats']
                resolutions = sorted(set(
                    f.get('height', 0) for f in formats
                    if f.get('ext') == 'mp4' and f.get('vcodec') != 'none'
                ), reverse=True)
                resolution_strings = [f"{r}p" for r in resolutions if r > 0]
                if not resolution_strings:
                    resolution_strings = ["최고"]
                if global_resolution in resolution_strings:
                    default_idx = resolution_strings.index(global_resolution)
                else:
                    default_idx = 0
                resolution_sel = cols[3].selectbox(f"해상도 {i}", resolution_strings, index=default_idx, key=f"res_{i}")

            # 다운로드 버튼 및 진행률 표시
            progress_bar = cols[4].progress(0)
            download_button = cols[4].button("⬇️ 다운로드", key=f"btn_{i}")

            video_settings.append({
                'info': video_info,
                'format': format_sel,
                'resolution': resolution_sel,
                'progress_bar': progress_bar,
                'download_button': download_button,
                'index': i,
            })

        # 개별 다운로드 처리
        def run_download(v):
            def progress_callback(p):
                v['progress_bar'].progress(p)

            success, err = download_video(v['info'], v['format'], v['resolution'], progress_callback)
            if success:
                v['progress_bar'].progress(1.0)
            else:
                st.error(f"{v['info']['title']} 다운로드 실패: {err}")

        # 개별 다운로드 버튼 클릭시 스레드로 실행
        for v in video_settings:
            if v['download_button']:
                threading.Thread(target=run_download, args=(v,)).start()

        # 전체 다운로드 버튼
        if st.button("📥 전체 영상 다운로드 시작"):
            def download_all():
                for v in video_settings:
                    def progress_callback(p):
                        v['progress_bar'].progress(p)
                    success, err = download_video(v['info'], v['format'], v['resolution'], progress_callback)
                    if not success:
                        st.error(f"{v['info']['title']} 다운로드 실패: {err}")

            threading.Thread(target=download_all).start()
