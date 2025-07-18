import streamlit as st
import yt_dlp
import os
import time
from datetime import timedelta
from urllib.parse import urlencode

st.set_page_config(page_title="YouTube 다운로드", layout="centered")
st.title("🎬 YouTube 영상/재생목록 다운로드기")

download_path = "downloads"
os.makedirs(download_path, exist_ok=True)

progress_bar = st.progress(0)
download_speed_text = st.empty()
eta_text = st.empty()

class DownloadProgress:
    def __init__(self):
        self.total_bytes = None
        self.downloaded_bytes = 0
        self.start_time = None

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            self.downloaded_bytes = d.get('downloaded_bytes', 0)
            self.total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if self.start_time is None:
                self.start_time = time.time()
            if self.total_bytes and self.downloaded_bytes:
                progress = min(int(self.downloaded_bytes / self.total_bytes * 100), 100)
                progress_bar.progress(progress)
                elapsed = time.time() - self.start_time
                speed = self.downloaded_bytes / elapsed if elapsed > 0 else 0
                remaining_bytes = self.total_bytes - self.downloaded_bytes
                eta_seconds = remaining_bytes / speed if speed > 0 else 0
                download_speed_text.text(f"속도: {format_bytes(speed)}/초")
                eta_text.text(f"남은 시간 예상: {format_timedelta(eta_seconds)}")
        elif d['status'] == 'finished':
            progress_bar.progress(100)
            download_speed_text.text("")
            eta_text.text("")

def format_bytes(size):
    power = 2**10
    n = 0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    while size > power and n < len(units)-1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def format_timedelta(seconds):
    return str(timedelta(seconds=int(seconds)))

def get_video_info(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

# 쿼리 파라미터에서 유튜브 id 등 정보 추출해서 유튜브 링크 생성
def get_url_from_query_params():
    params = st.query_params
    if not params:
        return ""
    # 유튜브 영상 id
    v = params.get('v', [None])[0]
    if not v:
        return ""
    # 나머지 파라미터 복사 (list 형태 -> 단일값)
    others = {k: v[0] for k, v in params.items() if k != 'v'}
    query_str = urlencode(others) if others else ""
    base_url = f"https://www.youtube.com/watch?v={v}"
    if query_str:
        base_url += "&" + query_str
    return base_url

if "url_input" not in st.session_state:
    st.session_state["url_input"] = get_url_from_query_params()

url = st.text_input("🔗 유튜브 영상 또는 재생목록 URL을 입력하세요:", value=st.session_state.get("url_input", ""))

if url:
    try:
        info = get_video_info(url)
        st.markdown("### 🎥 영상 정보")
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

        formats = info.get('formats', [])
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
                title = yt_dlp.YoutubeDL({
                    'outtmpl': f'{download_path}/%(title)s.%(ext)s',
                    'format': selected_format,
                    'quiet': True,
                    'progress_hooks': [progress_obj.progress_hook],
                }).extract_info(url, download=True)
                st.success(f"✅ 다운로드 완료: {title.get('title', '영상')}")
                st.info(f"폴더 경로: `{os.path.abspath(download_path)}`")

    except yt_dlp.utils.DownloadError as de:
        st.error(f"❌ 다운로드 오류: {de}")
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
else:
    st.info("다운로드할 유튜브 영상 또는 재생목록 URL을 입력하세요.")
