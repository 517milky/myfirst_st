import streamlit as st
import yt_dlp
import os
import tempfile
import shutil
import time
import re
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────
st.set_page_config(layout="wide")
st.title("YouTube 영상 다운로드기")

# ─────────────────────────────────────
# 함수: YouTube URL이 재생목록인지 확인
# ─────────────────────────────────────
def is_playlist(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return "list" in query

# ─────────────────────────────────────
# 함수: 영상 정보 추출
# ─────────────────────────────────────
def get_video_info(url):
    ydl_opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

# ─────────────────────────────────────
# 함수: 다운로드 진행률 표시 콜백
# ─────────────────────────────────────
def progress_hook(pbar, status_text, bar_text, start_time):
    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            percent = downloaded / total if total else 0
            elapsed = time.time() - start_time
            speed = downloaded / elapsed if elapsed > 0 else 0
            eta = (total - downloaded) / speed if speed > 0 else 0
            pbar.progress(percent)
            bar_text.write(f"진행률: {percent*100:.2f}% | 남은 시간: {eta:.1f}초")
        elif d["status"] == "finished":
            status_text.success("다운로드 완료!")
    return hook

# ─────────────────────────────────────
# 함수: 영상 다운로드
# ─────────────────────────────────────
def download_video(url, format_id, only_audio, output_dir):
    info = get_video_info(url)
    video_id = info["id"]
    video_title = info["title"]
    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")

    # 오디오만 다운로드 시 mp3 고정
    postprocessors = []
    if only_audio:
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]

    start_time = time.time()
    pbar = st.progress(0)
    bar_text = st.empty()
    status_text = st.empty()

    ydl_opts = {
        "format": format_id,
        "outtmpl": output_template,
        "progress_hooks": [progress_hook(pbar, status_text, bar_text, start_time)],
        "postprocessors": postprocessors,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    final_file = None
    for file in os.listdir(output_dir):
        if file.startswith(video_id):
            final_file = os.path.join(output_dir, file)
            break
    return final_file

# ─────────────────────────────────────
# 함수: 재생목록 링크에서 모든 영상 URL 추출
# ─────────────────────────────────────
def extract_playlist_entries(url):
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("entries", []), info.get("title", "playlist")

# ─────────────────────────────────────
# 사용자 입력
# ─────────────────────────────────────
url = st.text_input("YouTube 링크를 입력하세요:")

if url:
    if is_playlist(url):
        entries, playlist_title = extract_playlist_entries(url)
        st.subheader(f"🎵 재생목록: {playlist_title}")
        folder = tempfile.mkdtemp()
        selected = []

        for idx, entry in enumerate(entries):
            with st.expander(f"{idx+1}. {entry['title']}"):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.video(f"https://www.youtube.com/watch?v={entry['id']}")
                with col2:
                    with st.form(f"form_{entry['id']}"):
                        st.write("다운로드 옵션 선택")
                        download_mode = st.radio("형식", ["영상+소리", "영상만", "소리만"], key=entry['id'])
                        only_audio = download_mode == "소리만"
                        if only_audio:
                            format_id = "bestaudio"
                        else:
                            formats = get_video_info(f"https://www.youtube.com/watch?v={entry['id']}")["formats"]
                            resolutions = sorted(set(
                                f"{f['format_id']} ({f['height']}p)" for f in formats
                                if f.get("height") and f["vcodec"] != "none"
                            ), key=lambda x: int(re.search(r"(\d+)p", x).group(1)), reverse=True)
                            format_id = st.selectbox("해상도 선택", resolutions, key=f"res_{entry['id']}")
                            format_id = format_id.split()[0]
                        submit = st.form_submit_button("다운로드")
                        if submit:
                            file_path = download_video(f"https://www.youtube.com/watch?v={entry['id']}", format_id, only_audio, folder)
                            if file_path:
                                st.success("✅ 다운로드 성공")
                                st.download_button("파일 저장", open(file_path, "rb"), file_name=os.path.basename(file_path))
    else:
        info = get_video_info(url)
        st.video(f"https://www.youtube.com/watch?v={info['id']}")
        download_mode = st.radio("형식", ["영상+소리", "영상만", "소리만"])
        only_audio = download_mode == "소리만"
        if only_audio:
            format_id = "bestaudio"
        else:
            formats = info["formats"]
            resolutions = sorted(set(
                f"{f['format_id']} ({f['height']}p)" for f in formats
                if f.get("height") and f["vcodec"] != "none"
            ), key=lambda x: int(re.search(r"(\d+)p", x).group(1)), reverse=True)
            format_id = st.selectbox("해상도 선택", resolutions)
            format_id = format_id.split()[0]

        if st.button("다운로드 시작"):
            folder = tempfile.mkdtemp()
            file_path = download_video(url, format_id, only_audio, folder)
            if file_path:
                st.success("✅ 다운로드 성공")
                st.download_button("파일 저장", open(file_path, "rb"), file_name=os.path.basename(file_path))
