import streamlit as st
import yt_dlp
import time
from datetime import timedelta

def get_playlist_video_urls(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # 영상 URL만 빠르게 가져옴
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get('entries', [])
        return entries, info.get('title', 'playlist')

def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

# 기존 재생목록 탭 내 함수 대체용
def load_and_show_playlist(playlist_url):
    entries, playlist_title = get_playlist_video_urls(playlist_url)
    st.success(f"{len(entries)}개의 영상 발견됨: {playlist_title}")

    video_infos = []

    placeholder = st.empty()

    for i, entry in enumerate(entries):
        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
        with placeholder.container():
            st.write(f"영상 {i+1} 정보 로딩 중...")
        try:
            info = get_video_info(video_url)
            duration_str = str(timedelta(seconds=info.get('duration', 0)))
            with placeholder.container():
                st.write(f"영상 {i+1}: {info.get('title', '제목없음')} ({duration_str})")
                st.video(video_url)
        except Exception:
            with placeholder.container():
                st.write(f"영상 {i+1}: 정보 불러오기 실패")
        # 잠시 쉬었다가 다음 영상으로
        time.sleep(0.5)

    st.write("모든 영상 정보 로딩 완료.")

# 재생목록 탭 사용 예시
def playlist_tab():
    st.header("재생목록 다운로드")
    playlist_url = st.text_input("YouTube 재생목록 URL 입력")
    if playlist_url:
        load_and_show_playlist(playlist_url)

# 실제 앱 내 기존 탭 대신 이 함수를 호출해 사용하면 됩니다.
