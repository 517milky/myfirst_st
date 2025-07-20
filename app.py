import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import time
from datetime import timedelta

# 썸네일 크기를 줄이고 텍스트와 선택지를 표 형식으로 배치하는 커스텀 UI 함수
def render_playlist_table(all_videos):
    selected_indices = []
    download_options = {}

    st.markdown("<style>td, th {padding: 5px;}</style>", unsafe_allow_html=True)
    for idx, (info, video_url) in enumerate(all_videos):
        cols = st.columns([1, 5, 2, 2, 2])  # 썸네일, 제목, 길이, 다운로드 방식, 해상도

        with cols[0]:
            st.image(info['thumbnail'], width=80)
        with cols[1]:
            st.markdown(f"**{idx+1}. {info['title']}**")
        with cols[2]:
            st.write(str(timedelta(seconds=info['duration'])))
        with cols[3]:
            mode = st.selectbox(f"방식 {idx}", ["영상+소리", "영상만", "소리만"], key=f"mode_{idx}")
        with cols[4]:
            if mode != "소리만":
                quality = st.selectbox(f"해상도 {idx}", ["144p", "240p", "360p", "480p"], key=f"quality_{idx}")
            else:
                quality = None

        selected = st.checkbox(f"선택 {idx}", key=f"select_{idx}")
        if selected:
            selected_indices.append(idx)
            download_options[idx] = (mode, quality)

        st.markdown("---")

    return selected_indices, download_options

# 재생목록 영상 불러오기, 다운로드 함수는 기존과 동일

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
                "480p": "135",
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

# 메인 앱
def main():
    st.title("YouTube 재생목록 다운로드")

    playlist_url = st.text_input("재생목록 URL 입력")

    if playlist_url:
        with st.spinner("영상 목록 불러오는 중... 오래 걸릴 수 있습니다. 잠시만 기다려 주세요."):
            urls, playlist_title = get_playlist_video_urls(playlist_url)
            st.success(f"총 {len(urls)}개 영상 발견됨")

            all_videos = []
            progress_bar = st.progress(0)

            for i, url in enumerate(urls):
                try:
                    info = get_video_info(url)
                    all_videos.append((info, url))
                except:
                    continue
                progress_bar.progress((i+1)/len(urls))

            selected_indices, download_opts = render_playlist_table(all_videos)

            if st.button("선택한 영상들 다운로드"):
                for idx in selected_indices:
                    info, video_url = all_videos[idx]
                    mode, quality = download_opts[idx]

                    progress_placeholder = st.empty()
                    progress_bar_dl = st.progress(0)

                    def progress_hook(d):
                        if d["status"] == "downloading":
                            total = d.get("total_bytes") or d.get("total_bytes_estimate")
                            downloaded = d.get("downloaded_bytes", 0)
                            percent = downloaded / total if total else 0
                            eta = d.get("eta", 0)
                            progress_bar_dl.progress(min(percent, 1.0))
                            progress_placeholder.text(f"진행률: {percent*100:.1f}% | ETA: {eta}s")
                        elif d["status"] == "finished":
                            progress_bar_dl.progress(1.0)
                            progress_placeholder.text("✅ 다운로드 완료!")

                    download_video(video_url, mode, quality, progress_hook)

if __name__ == "__main__":
    main()
