import streamlit as st
import yt_dlp
import os
import math
from datetime import timedelta

st.set_page_config(page_title="YouTube 다운로드", layout="centered")
st.title("🎬 YouTube 영상/재생목록 다운로드기")

download_path = "downloads"
os.makedirs(download_path, exist_ok=True)

progress_bar = st.progress(0)

class DownloadProgress:
    def __init__(self):
        self.total_bytes = None
        self.downloaded_bytes = 0
        self.elapsed_seconds = 0
        self.start_time = None

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            self.downloaded_bytes = d.get('downloaded_bytes', 0)
            self.total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if not self.start_time:
                self.start_time = d.get('elapsed', 0)
            self.elapsed_seconds = d.get('elapsed', 0)
            if self.total_bytes:
                progress = min(int(self.downloaded_bytes / self.total_bytes * 100), 100)
                progress_bar.progress(progress)
        elif d['status'] == 'finished':
            progress_bar.progress(100)

def format_bytes(size):
    # 바이트 단위를 사람이 읽기 편한 단위로 변환
    # https://stackoverflow.com/a/1094933/10628285 참고
    power = 2**10
    n = 0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    while size > power and n < len(units)-1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def format_timedelta(seconds):
    return str(timedelta(seconds=int(seconds)))

def get_video_info(url, format_id=None):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    if format_id:
        ydl_opts['format'] = format_id

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def download_video(url, format_id=None, progress_obj=None):
    ydl_opts = {
        'outtmpl': f'{download_path}/%(title)s.%(ext)s',
        'format': format_id or 'best',
        'quiet': True,
        'progress_hooks': [progress_obj.progress_hook] if progress_obj else [],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', '영상')

query_params = st.query_params

default_url = ""
if 'v' in query_params:
    default_url = f"https://www.youtube.com/watch?v={query_params['v'][0]}"
elif 'video' in query_params:
    default_url = f"https://www.youtube.com/watch?v={query_params['video'][0]}"

url = st.text_input("🔗 유튜브 영상 또는 재생목록 URL을 입력하세요:", value=default_url)

if url:
    try:
        # 영상 정보 미리 받아오기
        info = get_video_info(url)
        st.markdown(f"### 🎥 영상 정보")
        st.write(f"**제목:** {info.get('title', '알 수 없음')}")
        st.write(f"**업로더:** {info.get('uploader', '알 수 없음')}")
        duration = info.get('duration')
        if duration:
            st.write(f"**길이:** {format_timedelta(duration)}")
        view_count = info.get('view_count')
        if view_count:
            st.write(f"**조회수:** {view_count:,}회")
        description = info.get('description', '')
        if description:
            st.write(f"**설명:** {description[:300]}{'...' if len(description) > 300 else ''}")

        # 지원하는 포맷들 나열 (영상+음성, 영상만, 음성만)
        formats = info.get('formats', [])
        # 영상+음성만 필터링, 파일 크기 크기순 정렬
        video_audio_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
        video_audio_formats.sort(key=lambda x: x.get('filesize') or 0)

        format_options = {}
        st.write("### ⚙️ 다운로드 화질 선택")
        for f in video_audio_formats:
            fmt_id = f.get('format_id')
            resolution = f.get('format_note') or f.get('height') or 'Unknown'
            filesize = f.get('filesize') or f.get('filesize_approx') or 0
            filesize_str = format_bytes(filesize) if filesize else "알 수 없음"
            label = f"{resolution} - {filesize_str}"
            format_options[fmt_id] = label

        selected_format = st.selectbox("다운로드할 화질을 선택하세요:", options=list(format_options.keys()), format_func=lambda x: format_options[x])

        if st.button("📥 다운로드 시작"):
            progress_obj = DownloadProgress()
            with st.spinner("다운로드 중..."):
                title = download_video(url, format_id=selected_format, progress_obj=progress_obj)
                st.success(f"✅ 다운로드 완료: {title}")
                st.info(f"폴더 경로: `{os.path.abspath(download_path)}`")

    except yt_dlp.utils.DownloadError as de:
        st.error(f"❌ 다운로드 오류: {de}")
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
else:
    st.info("다운로드할 유튜브 영상 또는 재생목록 URL을 입력하세요.")
