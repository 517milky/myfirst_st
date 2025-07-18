import streamlit as st
import yt_dlp
import os

st.set_page_config(page_title="YouTube 다운로드", layout="centered")
st.title("🎬 YouTube 영상/재생목록 다운로드기")

download_path = "downloads"
os.makedirs(download_path, exist_ok=True)

progress_bar = st.progress(0)

def download_hook(d):
    if d['status'] == 'downloading':
        downloaded_bytes = d.get('downloaded_bytes', 0)
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        if total_bytes:
            progress = min(int(downloaded_bytes / total_bytes * 100), 100)
            progress_bar.progress(progress)

def download_video(url):
    ydl_opts = {
        'outtmpl': f'{download_path}/%(title)s.%(ext)s',
        'format': 'best',
        'quiet': True,
        'progress_hooks': [download_hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', '영상')

query_params = st.query_params

# 쿼리 파라미터에서 video ID 추출 후 유튜브 전체 링크 생성
default_url = ""
if 'video' in query_params:
    video_id = query_params['video'][0]
    default_url = f"https://www.youtube.com/watch?v={video_id}"

# 입력창에 기본값 세팅
url = st.text_input("🔗 유튜브 영상 또는 재생목록 URL을 입력하세요:", value=default_url)

if url and st.button("📥 다운로드 시작"):
    with st.spinner("다운로드 중..."):
        try:
            title = download_video(url)
            st.success(f"✅ 다운로드 완료: {title}")
            st.info(f"폴더 경로: `{os.path.abspath(download_path)}`")
        except Exception as e:
            st.error(f"❌ 오류 발생: {str(e)}")
