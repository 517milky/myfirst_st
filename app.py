import streamlit as st
from yt_dlp import YoutubeDL
import os
import uuid
import subprocess
from datetime import timedelta

st.set_page_config(page_title="YouTube Downloader", layout="centered")
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
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
    ydl_opts = {
        'format': format_id,
        'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',
        'quiet': True,
        'noplaylist': False,
        'merge_output_format': 'mp4',
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info

def download_high_quality(url):
    # 영상-only + 오디오-only 각각 다운로드 후 병합
    ydl_opts_video = {
        'format': 'bv[ext=mp4]+ba[ext=m4a]/bestvideo+bestaudio',
        'outtmpl': f'{DOWNLOAD_PATH}/video_{uuid.uuid4()}.mp4',
        'quiet': True,
    }
    ydl_opts_audio = {
        'format': 'ba[ext=m4a]/bestaudio',
        'outtmpl': f'{DOWNLOAD_PATH}/audio_{uuid.uuid4()}.m4a',
        'quiet': True,
    }
    with YoutubeDL(ydl_opts_video) as ydl:
        video_info = ydl.extract_info(url, download=True)
        video_path = ydl.prepare_filename(video_info)

    with YoutubeDL(ydl_opts_audio) as ydl:
        audio_info = ydl.extract_info(url, download=True)
        audio_path = ydl.prepare_filename(audio_info)

    output_path = f"{DOWNLOAD_PATH}/merged_{uuid.uuid4()}.mp4"
    merge_video_audio(video_path, audio_path, output_path)

    os.remove(video_path)
    os.remove(audio_path)

    return output_path

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

    formats = info.get('formats', [])

    # progressive (영상+오디오 같이 포함, 보통 360p 이하)
    progressive_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') != 'none' and f.get('format_note') != 'unknown']
    progressive_formats.sort(key=lambda x: x.get('height') or 0)

    # 영상 전용 (고화질 포함)
    video_only_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') == 'none' and f.get('ext') == 'mp4']
    video_only_formats.sort(key=lambda x: x.get('height') or 0)

    # 오디오 전용
    audio_only_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    audio_only_formats.sort(key=lambda x: x.get('abr') or 0)

    st.subheader("⚙️ 다운로드 옵션")
    dl_type = st.radio("다운로드 유형 선택:", ["영상+오디오 (360p 이하)", "영상만 (고화질 가능)", "오디오만"])

    selected_format = None

    if dl_type == "영상+오디오 (360p 이하)":
        if not progressive_formats:
            st.warning("영상+오디오 포함된 포맷이 없습니다.")
        options = {f['format_id']: f"{f.get('format_note', '')} - {format_bytes(f.get('filesize') or 0)}" for f in progressive_formats}
        selected_format = st.selectbox("화질 선택:", list(options.keys()), format_func=lambda x: options[x])

    elif dl_type == "영상만 (고화질 가능)":
        if not video_only_formats:
            st.warning("영상 전용 포맷이 없습니다.")
        options = {f['format_id']: f"{f.get('height', '')}p - {format_bytes(f.get('filesize') or 0)}" for f in video_only_formats}
        selected_format = st.selectbox("화질 선택:", list(options.keys()), format_func=lambda x: options[x])
        if selected_format:
            height = next((f.get('height', 0) for f in video_only_formats if f['format_id'] == selected_format), 0)
            if height >= 720:
                st.info("⏳ 고화질 다운로드 시 시간이 오래 걸릴 수 있습니다.")

    else:  # 오디오만
        if not audio_only_formats:
            st.warning("오디오 전용 포맷이 없습니다.")
        options = {f['format_id']: f"{f.get('abr', '')}kbps - {format_bytes(f.get('filesize') or 0)}" for f in audio_only_formats}
        selected_format = st.selectbox("음질 선택:", list(options.keys()), format_func=lambda x: options[x])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 다운로드 시작"):
            if dl_type == "영상만 (고화질 가능)":
                try:
                    with st.spinner("다운로드 중 (영상+오디오 병합)..."):
                        output_path = download_high_quality(url)
                    st.success("✅ 고화질 영상+오디오 다운로드 완료!")
                    with open(output_path, "rb") as f:
                        st.download_button("📥 파일 다운로드", f, file_name=os.path.basename(output_path))
                    os.remove(output_path)
                except Exception as e:
                    st.error(f"❌ 다운로드 오류: {e}")
            else:
                try:
                    with st.spinner("다운로드 중..."):
                        info_dl = download_media(url, selected_format)
                    filename = info_dl.get('title') + "." + info_dl.get('ext', 'mp4')
                    filepath = os.path.join(DOWNLOAD_PATH, filename)
                    st.success(f"✅ 다운로드 완료: {info_dl.get('title')}")
                    with open(filepath, "rb") as f:
                        st.download_button("📥 파일 다운로드", f, file_name=filename)
                except Exception as e:
                    st.error(f"❌ 다운로드 오류: {e}")

    with col2:
        st.write("💡 고화질 영상(1080p 이상)은 영상만 + 오디오만 스트림을 따로 다운받아\n"
                 "ffmpeg로 병합합니다.\n"
                 "⚠️ 시간이 오래 걸릴 수 있습니다.")
else:
    st.info("유튜브 영상 또는 재생목록 링크를 입력해주세요.")
