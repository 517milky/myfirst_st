import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import time
import shutil
import streamlit.components.v1 as components
import urllib.parse
import uuid

# 페이지 설정
st.set_page_config(page_title="YouTube 다운로드", layout="wide")
st.title("YouTube 재생목록 다운로드")

# 경고 스타일
st.markdown("""
    <style>
        .warning {color: red; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# 입력
url_input = st.text_input("YouTube 재생목록 링크를 입력하세요.", placeholder="https://www.youtube.com/playlist?list=...")

# 목록 미리보기 기능
show_list = False
if st.button("🔍 목록 미리 확인"):
    st.warning("목록을 불러오는 데 시간이 걸릴 수 있습니다.")
    show_list = True

# 유일한 다운로드 디렉토리 생성
def make_unique_download_dir(playlist_title="playlist"):
    root = tempfile.gettempdir()
    safe_title = "".join(c if c.isalnum() else "_" for c in playlist_title)
    unique_id = str(uuid.uuid4())[:8]
    path = os.path.join(root, f"{safe_title}_{unique_id}")
    os.makedirs(path, exist_ok=True)
    return path

# 영상 정보 가져오기
def get_playlist_info(url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'playlistend': 100  # 최대 100개까지만
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

# 영상 개별 스트림 선택
def get_streams(video_url, mode):
    ydl_opts = {'quiet': True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get('formats', [])

    video_streams = []
    audio_streams = []
    for f in formats:
        if f.get("vcodec") != "none" and f.get("acodec") == "none":
            video_streams.append(f)
        elif f.get("acodec") != "none" and f.get("vcodec") == "none":
            audio_streams.append(f)
        elif f.get("acodec") != "none" and f.get("vcodec") != "none":
            if mode == "영상+소리":
                video_streams.append(f)

    if mode == "소리만":
        return sorted(audio_streams, key=lambda x: x.get("abr", 0), reverse=True)
    else:
        return sorted(video_streams, key=lambda x: x.get("height", 0), reverse=True)

# 미리보기
def preview_player(video_url):
    video_embed = f"""
    <video width="100%" height="250" controls autoplay muted>
        <source src="{video_url}" type="video/mp4">
        Your browser does not support HTML5 video.
    </video>
    """
    components.html(video_embed, height=270)

# 다운로드
def download_video(video_url, mode, resolution, path, ext, progress_callback):
    ydl_opts = {
        'quiet': True,
        'outtmpl': os.path.join(path, f"%(title)s.%(ext)s"),
        'format': f'bestvideo[height={resolution}]+bestaudio/best[height={resolution}]' if mode == "영상+소리" else
                  f'bestvideo[height={resolution}]' if mode == "영상만" else
                  'bestaudio/best',
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_callback]
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

# 다운로드 실행
if url_input:
    try:
        playlist_info = get_playlist_info(url_input)
        videos = playlist_info.get("entries", [])
        playlist_title = playlist_info.get("title", "Playlist")
        download_dir = make_unique_download_dir(playlist_title)

        if show_list:
            st.subheader("재생목록 영상 선택")
        selected_videos = []

        for i, v in enumerate(videos):
            video_title = v.get("title")
            video_url = v.get("url")
            full_url = f"https://www.youtube.com/watch?v={video_url}"

            with st.expander(f"🎞 영상 {i+1}", expanded=show_list):
                cols = st.columns([1, 2, 2, 2])
                with cols[0]:
                    preview_player(full_url)

                with cols[1]:
                    mode = st.selectbox(f"다운로드 방식 ({i+1})", ["영상+소리", "영상만", "소리만"], key=f"mode_{i}")

                with cols[2]:
                    if mode == "소리만":
                        resolution = "audio"
                        ext = "mp3"
                        st.markdown("🔈 최고 음질")
                    else:
                        streams = get_streams(full_url, mode)
                        options = [str(f.get("height")) for f in streams if "height" in f]
                        resolution = st.selectbox("해상도 선택", options, key=f"res_{i}")
                        ext = "mp4"

                with cols[3]:
                    download = st.checkbox("✅ 선택", key=f"check_{i}")
                    if download:
                        selected_videos.append({
                            "url": full_url,
                            "mode": mode,
                            "resolution": resolution,
                            "ext": ext,
                            "title": video_title
                        })

        if selected_videos:
            if st.button("⬇️ 바로 다운로드"):
                for idx, vid in enumerate(selected_videos):
                    st.write(f"🎬 영상 {idx+1} 다운로드 중...")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    start_time = time.time()

                    def progress_hook(d):
                        if d['status'] == 'downloading':
                            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                            downloaded = d.get('downloaded_bytes', 0)
                            if total_bytes:
                                percent = downloaded / total_bytes
                                progress_bar.progress(min(percent, 1.0))
                                elapsed = time.time() - start_time
                                if percent > 0:
                                    est = (elapsed / percent) - elapsed
                                    status_text.text(f"진행률: {percent*100:.2f}% | 예상 시간: {est:.1f}초")
                        elif d['status'] == 'finished':
                            progress_bar.progress(100)
                            status_text.text("완료!")

                    download_video(vid["url"], vid["mode"], vid["resolution"], download_dir, vid["ext"], progress_hook)

                st.success(f"✅ 모든 다운로드 완료!\n\n📁 저장 경로: `{download_dir}`")

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
