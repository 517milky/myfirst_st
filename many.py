# many.py

import streamlit as st
import yt_dlp
import os
import tempfile
from datetime import timedelta

# 영상 개별 stream 정보 로드 함수
def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

# 재생목록의 링크들만 가져오기 (빠름)
def get_playlist_video_urls(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # 🔥 핵심 옵션
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get('entries', [])
        return [entry['url'] for entry in entries], info.get('title', 'playlist')

def main():
    st.header("재생목록 다운로드")

    playlist_url = st.text_input("YouTube 재생목록 URL 입력")

    if playlist_url:
        with st.spinner("재생목록 영상 불러오는 중..."):
            try:
                urls, playlist_title = get_playlist_video_urls(playlist_url)
                st.success(f"총 {len(urls)}개의 영상 발견됨.")

                selected_videos = []
                all_download_options = {}

                for i, video_url in enumerate(urls):
                    with st.expander(f"영상 {i + 1}", expanded=False):
                        if st.checkbox(f"이 영상 선택", key=f"select_{i}"):
                            info = get_video_info(video_url)
                            st.video(info['url'])
                            st.write("길이:", str(timedelta(seconds=info['duration'])))
                            mode = st.radio(f"다운로드 방식 선택", ["영상+소리", "영상만", "소리만"], key=f"mode_{i}")
                            if mode in ["영상만", "영상+소리"]:
                                format = st.selectbox("해상도 선택", ["1080p", "720p", "480p", "360p"], key=f"res_{i}")
                            else:
                                format = "최고 음질"
                            all_download_options.append((video_url, mode, format))

                if st.button("선택한 영상들 다운로드"):
                    folder_name = playlist_title.replace(" ", "_")
                    os.makedirs(folder_name, exist_ok=True)

                    for video_url, mode, format in all_download_options:
                        st.write(f"다운로드 중: {video_url}")
                        st.progress(0)

                        # 여기에 다운로드 로직 삽입
                        # yt_dlp 사용하여 영상 저장
                        # ...

                    st.success("다운로드 완료!")
            except Exception as e:
                st.error(f"오류 발생: {e}")

if __name__ == "__main__":
    main()
