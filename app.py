import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import time
from datetime import timedelta

st.set_page_config(page_title="YouTube 다운로더", layout="wide")
st.title("📺 YouTube 다운로드 (재생목록 지원)")

# 재생목록 감지
def is_playlist(url):
    return "playlist?" in url or "&list=" in url

# 영상 개별 stream 정보 로드 함수
def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

# 재생목록의 링크들만 가져오기
def get_playlist_video_urls(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get('entries', [])
        return [entry['url'] for entry in entries], info.get('title', 'playlist')

# 다운로드
def download_video(url, mode, quality, progress_callback):
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, '%(title)s.%(ext)s')
        if mode == "소리만":
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'outtmpl': outtmpl,
                'quiet': True,
                'progress_hooks': [progress_callback],
            }
        elif mode == "영상만":
            res_map = {
                "144p": "160", "240p": "133", "360p": "134",
                "480p": "135", "720p": "136", "1080p": "137",
            }
            format_code = res_map.get(quality, "134")
            ydl_opts = {
                'format': format_code,
                'outtmpl': outtmpl,
                'quiet': True,
                'progress_hooks': [progress_callback],
            }
        else:  # 영상+소리
            height = ''.join(filter(str.isdigit, quality or '480'))
            ydl_opts = {
                'format': f'best[height<={height}][vcodec!=none][acodec!=none]/best',
                'outtmpl': outtmpl,
                'quiet': True,
                'progress_hooks': [progress_callback],
            }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)

        with open(filename, "rb") as f:
            st.download_button("📥 다운로드", f, file_name=os.path.basename(filename))

# 단일 영상 처리
def handle_single_video(url):
    info = get_video_info(url)
    st.video(info["url"])
    st.write("📄 제목:", info["title"])
    st.write("⏱️ 길이:", str(timedelta(seconds=info["duration"])))

    download_type = st.radio("다운로드 방식", ("영상+소리", "영상만", "소리만"))
    if download_type != "소리만":
        quality = st.selectbox("해상도 선택", ["144p", "240p", "360p", "480p"])
    else:
        quality = None

    progress_bar = st.empty()
    status_text = st.empty()

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            percent = downloaded / total if total else 0
            eta = d.get("eta", 0)
            progress_bar.progress(min(percent, 1.0))
            status_text.text(f"진행률: {percent*100:.1f}% | 남은 시간: {eta}s")
        elif d["status"] == "finished":
            progress_bar.progress(1.0)
            status_text.text("✅ 다운로드 완료!")

    if st.button("📥 다운로드 시작"):
        download_video(url, download_type, quality, progress_hook)

# 재생목록 처리
def handle_playlist(url):
    st.info("🔍 영상 목록 불러오는 중...")
    urls, playlist_title = get_playlist_video_urls(url)
    st.success(f"총 {len(urls)}개 영상 발견됨")
    st.progress(0)

    all_videos = []
    for i, video_url in enumerate(urls):
        try:
            info = get_video_info(video_url)
            all_videos.append((info, video_url))
        except Exception:
            continue
        st.progress((i+1) / len(urls))

    st.subheader("📝 영상 목록")
    for idx, (info, video_url) in enumerate(all_videos):
        with st.expander(f"{idx+1}. {info['title']}"):
            st.image(info['thumbnail'], width=160)
            st.write("길이:", str(timedelta(seconds=info['duration'])))
            st.video(info["url"])

            mode = st.radio("방식", ["영상+소리", "영상만", "소리만"], key=f"mode_{idx}")
            if mode != "소리만":
                height_options = ["144p", "240p", "360p", "480p"]
                st.write("🔽 선택 가능한 해상도만 표시됩니다.")
                quality = st.selectbox("해상도", height_options, key=f"q_{idx}")
            else:
                quality = None

            pbar = st.empty()
            pstatus = st.empty()

            def progress_hook(d):
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    percent = downloaded / total if total else 0
                    eta = d.get("eta", 0)
                    pbar.progress(min(percent, 1.0))
                    pstatus.text(f"진행률: {percent*100:.1f}% | ETA: {eta}s")
                elif d["status"] == "finished":
                    pbar.progress(1.0)
                    pstatus.text("✅ 완료!")

            if st.button("⬇ 개별 다운로드", key=f"dlbtn_{idx}"):
                download_video(video_url, mode, quality, progress_hook)

# 메인 실행
url_input = st.text_input("🔗 YouTube 링크 입력")

if url_input:
    if is_playlist(url_input):
        handle_playlist(url_input)
    else:
        handle_single_video(url_input)
