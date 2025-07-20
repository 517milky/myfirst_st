import streamlit as st
from yt_dlp import YoutubeDL
import threading
import os
from datetime import timedelta
from io import BytesIO
from PIL import Image
import requests

st.set_page_config(layout="wide")
st.title("📥 YouTube 재생목록 다운로드 (yt-dlp 기반)")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FORMAT_OPTIONS = ["영상+소리", "영상만", "소리만"]
RESOLUTIONS_ALL = ["1080p", "720p", "480p", "360p", "240p", "144p"]

def fetch_playlist_videos(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    entries = info.get('entries', [])
    playlist_title = info.get('title', '재생목록')
    video_urls = []
    for e in entries:
        if 'url' in e:
            video_urls.append("https://www.youtube.com/watch?v=" + e['url'])
    return playlist_title, video_urls

@st.cache_data(show_spinner="영상 정보 불러오는 중...")
def fetch_video_info(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    # 해상도 추출: video streams 중 height 값을 이용해 p 단위 변환
    formats = info.get('formats', [])
    res_set = set()
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('height'):
            res_set.add(f"{f['height']}p")
        elif f.get('vcodec') != 'none' and not f.get('acodec'):
            res_set.add(f"{f['height']}p")
        elif not f.get('vcodec') and f.get('acodec') != 'none':
            res_set.add("audio_only")
    res_list = sorted(list(res_set), key=lambda x: (x!="audio_only", int(x.replace('p','')) if x!="audio_only" else 0), reverse=True)

    return {
        'title': info.get('title'),
        'duration': info.get('duration'),
        'thumbnail': info.get('thumbnail'),
        'url': url,
        'resolutions': res_list,
        'formats': formats,
    }

def get_image_from_url(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

def download_thread(video_url, selected_format, selected_resolution, index, status_list, lock):
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'quiet': True,
        'progress_hooks': [],
    }
    if selected_format == "영상+소리":
        # best video+audio up to selected_resolution
        ydl_opts['format'] = f'bestvideo[height<={selected_resolution.replace("p","")}]+bestaudio/best[height<={selected_resolution.replace("p","")}]'
    elif selected_format == "영상만":
        ydl_opts['format'] = f'bestvideo[height<={selected_resolution.replace("p","")}]'
    else:  # 소리만
        ydl_opts['format'] = 'bestaudio'

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes', 0)
            percent = int(downloaded / total * 100)
            with lock:
                status_list[index] = f"다운로드 중... {percent}%"
        elif d['status'] == 'finished':
            with lock:
                status_list[index] = "다운로드 완료!"

    ydl_opts['progress_hooks'] = [progress_hook]

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        with lock:
            status_list[index] = f"오류: {str(e)}"

def main():
    playlist_url = st.text_input("🔗 YouTube 재생목록 URL 입력")

    if not playlist_url:
        st.info("위에 URL을 입력해주세요.")
        return

    with st.spinner("재생목록 영상 불러오는 중..."):
        try:
            playlist_title, video_urls = fetch_playlist_videos(playlist_url)
            total_videos = len(video_urls)
            st.success(f"총 {total_videos}개 영상 발견: '{playlist_title}'")
        except Exception as e:
            st.error(f"재생목록을 불러오지 못했습니다: {str(e)}")
            return

    video_infos = []
    for i, url in enumerate(video_urls):
        info = fetch_video_info(url)
        if info is None:
            continue
        video_infos.append(info)

    # 전체 옵션
    st.subheader("전체 다운로드 옵션")
    col1, col2 = st.columns(2)
    with col1:
        global_format = st.selectbox("전체 다운로드 형식", FORMAT_OPTIONS)
    with col2:
        # 전체 영상에서 가능한 해상도 교집합 구하기
        res_sets = [set(v['resolutions']) for v in video_infos if v['resolutions']]
        if res_sets:
            common_res = list(set.intersection(*res_sets))
        else:
            common_res = []
        common_res = [r for r in RESOLUTIONS_ALL if r in common_res]
        if not common_res:
            common_res = RESOLUTIONS_ALL
        global_res = st.selectbox("전체 해상도 선택", common_res)

    st.subheader("영상 목록")
    status_list = ["대기 중"] * len(video_infos)
    lock = threading.Lock()

    for idx, vinfo in enumerate(video_infos):
        cols = st.columns([1, 4, 1, 1, 1])

        # 썸네일
        thumb_img = get_image_from_url(vinfo['thumbnail'])
        if thumb_img:
            with cols[0]:
                st.image(thumb_img.resize((100, 60)))

        # 제목 및 길이
        with cols[1]:
            st.markdown(f"**{vinfo['title']}**")
            if vinfo['duration']:
                m, s = divmod(vinfo['duration'], 60)
                st.caption(f"길이: {m}분 {s}초")

        # 다운로드 형식 선택
        with cols[2]:
            selected_format = st.selectbox(f"형식 {idx}", FORMAT_OPTIONS, key=f"format_{idx}")

        # 해상도 선택
        with cols[3]:
            available_res = [r for r in vinfo['resolutions'] if r != "audio_only"]
            if not available_res:
                available_res = ["audio_only"]
            default_res = global_res if global_res in available_res else available_res[0]
            selected_res = st.selectbox(f"해상도 {idx}", available_res, index=available_res.index(default_res), key=f"res_{idx}")

        # 다운로드 버튼
        with cols[4]:
            if st.button("⬇️ 다운로드", key=f"download_{idx}"):
                threading.Thread(target=download_thread, args=(vinfo['url'], selected_format, selected_res, idx, status_list, lock), daemon=True).start()

        # 진행 상태 표시
        st.write(status_list[idx])

    st.divider()
    if st.button("전체 다운로드 시작"):
        for idx, vinfo in enumerate(video_infos):
            selected_format = global_format
            available_res = [r for r in vinfo['resolutions'] if r != "audio_only"]
            if not available_res:
                available_res = ["audio_only"]
            selected_res = global_res if global_res in available_res else available_res[0]
            threading.Thread(target=download_thread, args=(vinfo['url'], selected_format, selected_res, idx, status_list, lock), daemon=True).start()

if __name__ == "__main__":
    main()
