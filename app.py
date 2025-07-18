import streamlit as st
from yt_dlp import YoutubeDL
import os
import uuid
import subprocess
from datetime import timedelta

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("🎬 YouTube 영상/재생목록 다운로드기")

DOWNLOAD_PATH = "downloads"
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

def fix_custom_url(url):
    if url.startswith("https://wwwyoutube.streamlit.app"):
        url = url.replace("https://wwwyoutube.streamlit.app", "https://www.youtube.com")
    elif url.startswith("https://wwwyoutube"):
        url = url.replace("wwwyoutube", "www.youtube")
    return url

def format_timedelta(seconds):
    return str(timedelta(seconds=int(seconds)))

def merge_video_audio(video_path, audio_path, output_path):
    command = [
        'ffmpeg',
        '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class ProgressHook:
    def __init__(self):
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.speed_text = st.empty()
        self.eta_text = st.empty()

    def hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes:
                percent = int(downloaded_bytes / total_bytes * 100)
                self.progress_bar.progress(percent)
                self.status_text.text(f"진행중... {percent}%")
                speed = d.get('speed', 0)
                if speed:
                    self.speed_text.text(f"속도: {format_bytes(speed)}/초")
                if speed and total_bytes and downloaded_bytes:
                    remaining = (total_bytes - downloaded_bytes) / speed
                    self.eta_text.text(f"남은 시간 예상: {format_timedelta(remaining)}")
        elif d['status'] == 'finished':
            self.progress_bar.progress(100)
            self.status_text.text("다운로드 완료!")
            self.speed_text.text("")
            self.eta_text.text("")

def format_bytes(size):
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def get_info(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def download_media(url, format_id):
    progress = ProgressHook()
    ydl_opts = {
        'format': format_id,
        'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',
        'progress_hooks': [progress.hook],
        'quiet': True,
        'noplaylist': False,
        'merge_output_format': 'mp4',
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info

def download_high_quality(url):
    progress = ProgressHook()
    temp_video = f"{DOWNLOAD_PATH}/video_{uuid.uuid4()}.mp4"
    temp_audio = f"{DOWNLOAD_PATH}/audio_{uuid.uuid4()}.m4a"
    output_path = f"{DOWNLOAD_PATH}/merged_{uuid.uuid4()}.mp4"

    ydl_video_opts = {
        'format': 'bv*[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio',
        'outtmpl': temp_video,
        'progress_hooks': [progress.hook],
        'quiet': True,
        'noplaylist': False,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegMerge',
        }],
    }

    with YoutubeDL(ydl_video_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    return info

input_url = st.text_input("🔗 유튜브 영상 또는 재생목록 URL을 입력하세요:", value="", placeholder="https://wwwyoutube.streamlit.app/watch?v=XXXX")

if input_url:
    url = fix_custom_url(input_url.strip())

    try:
        info = get_info(url)
    except Exception as e:
        st.error(f"❌ 영상 정보 불러오기 실패: {e}")
        st.stop()

    is_playlist = '_type' in info and info['_type'] == 'playlist'

    if is_playlist:
        st.subheader("📃 재생목록 정보")
        st.write(f"제목: {info.get('title')}")
        st.write(f"영상 수: {len(info.get('entries', []))}")
    else:
        st.subheader("🎥 영상 정보")
        st.video(url)
        st.write(f"제목: {info.get('title')}")
        st.write(f"채널: {info.get('uploader')}")
        dur = info.get('duration')
        if dur:
            st.write(f"길이: {format_timedelta(dur)}")
        # 썸네일 제거 (원하는 경우 여기에 출력 코드를 주석 처리 했습니다)

    formats = info.get('formats', [])

    prog_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') != 'none' and f.get('ext') == 'mp4']
    prog_formats.sort(key=lambda x: x.get('height') or 0)

    video_only_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') == 'none' and f.get('ext') == 'mp4']
    video_only_formats.sort(key=lambda x: x.get('height') or 0)

    audio_only_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    audio_only_formats.sort(key=lambda x: x.get('abr') or 0)

    st.subheader("⚙️ 다운로드 옵션")

    dl_type = st.radio("다운로드 유형 선택:", ["영상+오디오", "영상만", "오디오만"])

    selected_format = None

    if dl_type == "영상+오디오":
        options = {f"{f['format_id']}": f"{f.get('height', 'unknown')}p - {format_bytes(f.get('filesize', 0) or 0)}" for f in prog_formats}
        if not options:
            st.warning("영상+오디오 포함된 포맷이 없습니다.")
        selected_format = st.selectbox("화질 선택:", list(options.keys()), format_func=lambda x: options[x])

        if selected_format:
            height = next((f.get('height', 0) for f in prog_formats if f['format_id'] == selected_format), 0)
            if height >= 720:
                st.info("⏳ 고화질 다운로드 시 시간이 오래 걸릴 수 있습니다.")

    elif dl_type == "영상만":
        options = {f"{f['format_id']}": f"{f.get('height', 'unknown')}p - {format_bytes(f.get('filesize', 0) or 0)}" for f in video_only_formats}
        if not options:
            st.warning("영상 전용 포맷이 없습니다.")
        selected_format = st.selectbox("화질 선택:", list(options.keys()), format_func=lambda x: options[x])

        if selected_format:
            height = next((f.get('height', 0) for f in video_only_formats if f['format_id'] == selected_format), 0)
            if height >= 720:
                st.info("⏳ 고화질 다운로드 시 시간이 오래 걸릴 수 있습니다.")

    else:
        options = {f"{f['format_id']}": f"{f.get('abr', 'unknown')}kbps - {format_bytes(f.get('filesize', 0) or 0)}" for f in audio_only_formats}
        if not options:
            st.warning("오디오 전용 포맷이 없습니다.")
        selected_format = st.selectbox("음질 선택:", list(options.keys()), format_func=lambda x: options[x])

    if st.button("📥 다운로드 시작") and selected_format:
        try:
            with st.spinner("다운로드 중..."):
                if dl_type == "영상+오디오" and (next((f.get('height', 0) for f in prog_formats if f['format_id'] == selected_format), 0) >= 1080):
                    info_downloaded = download_high_quality(url)
                else:
                    info_downloaded = download_media(url, selected_format)

            st.success(f"✅ 다운로드 완료: {info_downloaded.get('title')}")
            filename = info_downloaded.get('title') + "." + info_downloaded.get('ext', 'mp4')
            filepath = os.path.join(DOWNLOAD_PATH, filename)
            with open(filepath, "rb") as f:
                st.download_button("📥 파일 다운로드", f, file_name=filename)
        except Exception as e:
            st.error(f"❌ 다운로드 중 오류 발생: {e}")

else:
    st.info("유튜브 영상 또는 재생목록 링크를 입력해주세요.")
