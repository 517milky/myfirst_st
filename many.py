import streamlit as st
import yt_dlp
import os
import tempfile
from datetime import timedelta
import threading
import time

st.set_page_config(page_title="재생목록 다운로드", layout="wide")

# 재생목록 파싱
def get_playlist_videos(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'force_generic_extractor': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        return info.get("entries", []), info.get("title", "재생목록")

# 개별 영상 다운로드
def download_video(video_url, mode, resolution, output_dir, progress_callback):
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'progress_hooks': [progress_callback],
    }

    if mode == "소리만":
        ydl_opts.update({
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
        })
    elif mode == "영상만":
        ydl_opts['format'] = f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]"
        ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoRemuxer', 'preferredformat': 'mp4'}]
    else:  # 영상+소리
        ydl_opts['format'] = f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]"
        ydl_opts['merge_output_format'] = 'mp4'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

# 각 영상 항목 UI
def video_item(video, idx, states):
    with st.expander(f"🎬 영상 {idx + 1}: {video['title']}"):
        st.video(video['url'])

        col1, col2 = st.columns(2)
        with col1:
            states[idx]["mode"] = st.selectbox(
                "다운로드 방식", ["영상+소리", "영상만", "소리만"],
                key=f"mode_{idx}"
            )
        with col2:
            if states[idx]["mode"] != "소리만":
                states[idx]["res"] = st.selectbox(
                    "해상도", ["2160", "1440", "1080", "720", "480", "360"],
                    index=2,
                    key=f"res_{idx}"
                )

        if st.button(f"⬇ 개별 다운로드", key=f"dl_{idx}"):
            states[idx]["trigger"] = True

# 전체 다운로드 쓰레드용
def threaded_download(video, idx, states, playlist_title, folder_path):
    start = time.time()
    def hook(d):
        if d['status'] == 'downloading':
            percent = d.get("_percent_str", "0.0%").strip()
            try:
                seconds = int(d.get("eta", 0))
                eta = str(timedelta(seconds=seconds))
            except:
                eta = "..."
            states[idx]["progress"] = percent
            states[idx]["eta"] = eta
        elif d['status'] == 'finished':
            states[idx]["progress"] = "100.0%"
            states[idx]["eta"] = "완료"

    try:
        mode = states[idx]["mode"]
        res = states[idx]["res"] if mode != "소리만" else None
        download_video(video['url'], mode, res, folder_path, hook)
    except Exception as e:
        states[idx]["eta"] = f"오류: {str(e)}"
    finally:
        elapsed = time.time() - start
        states[idx]["elapsed"] = str(timedelta(seconds=int(elapsed)))

# many.py 메인 함수
def main(url):
    videos, playlist_title = get_playlist_videos(url)

    if not videos:
        st.error("재생목록에서 영상을 찾을 수 없습니다.")
        return

    st.subheader(f"📂 재생목록: {playlist_title}")
    folder_path = os.path.join(tempfile.gettempdir(), playlist_title)
    os.makedirs(folder_path, exist_ok=True)

    states = [
        {"mode": "영상+소리", "res": "1080", "trigger": False, "progress": "0%", "eta": "", "elapsed": ""}
        for _ in videos
    ]

    # 전체 선택 기능
    all_mode = st.selectbox("🔄 전체 다운로드 방식", ["영상+소리", "영상만", "소리만"])
    if all_mode != "소리만":
        all_res = st.selectbox("🔄 전체 해상도", ["2160", "1440", "1080", "720", "480", "360"], index=2)
    if st.button("✅ 전체 설정 적용"):
        for s in states:
            s["mode"] = all_mode
            if all_mode != "소리만":
                s["res"] = all_res

    st.markdown("---")

    # 개별 UI 및 다운로드 실행
    for idx, video in enumerate(videos):
        video_item(video, idx, states)

    if st.button("⬇ 전체 다운로드 시작"):
        for idx, video in enumerate(videos):
            t = threading.Thread(target=threaded_download, args=(video, idx, states, playlist_title, folder_path))
            t.start()

    # 진행률 표시
    st.markdown("---")
    st.subheader("📊 다운로드 진행 상황")
    for idx, video in enumerate(videos):
        st.write(f"{idx + 1}. {video['title']}")
        st.progress(float(states[idx]["progress"].strip('%')) / 100)
        st.text(f"진행률: {states[idx]['progress']} / 예상 시간: {states[idx]['eta']} / 소요: {states[idx]['elapsed']}")

    st.success(f"📁 저장 폴더: {folder_path}")

