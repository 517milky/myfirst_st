import streamlit as st
import yt_dlp
import os
import uuid
import subprocess

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("📥 YouTube 영상 다운로드")

download_path = "downloads"
os.makedirs(download_path, exist_ok=True)

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

def get_video_info(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

def download_video_audio(url, format_id_video, format_id_audio):
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'format': f'{format_id_video}+{format_id_audio}',
        'quiet': True,
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info.get('title', 'video')

url = st.text_input("🔗 유튜브 영상 또는 재생목록 URL을 입력하세요:")

if url:
    try:
        info = get_video_info(url)
        st.markdown("### 🎥 영상 정보")
        st.write(f"**제목:** {info.get('title', '알 수 없음')}")
        st.write(f"**업로더:** {info.get('uploader', '알 수 없음')}")
        duration = info.get('duration')
        if duration:
            mins, secs = divmod(duration, 60)
            st.write(f"**길이:** {mins}분 {secs}초")
        st.video(url)

        # 화질 옵션 뽑기 (영상만)
        formats = info.get('formats', [])
        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') == 'none']
        video_formats = sorted(video_formats, key=lambda x: int(x.get('height') or 0))

        format_options = {}
        for f in video_formats:
            label = f"{f.get('format_id')} : {f.get('height')}p, {f.get('ext')}"
            format_options[label] = f.get('format_id')

        st.markdown("### ⚙️ 영상 화질 선택 (오디오 자동 포함, 고화질시 영상+오디오 분리 다운로드 후 병합)")
        selected_label = st.selectbox("화질 선택", list(format_options.keys()))
        selected_video_format = format_options[selected_label]

        # 오디오는 항상 최고 품질로
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        audio_formats = sorted(audio_formats, key=lambda x: int(x.get('abr') or 0), reverse=True)
        selected_audio_format = audio_formats[0].get('format_id') if audio_formats else None

        if st.button("📥 다운로드 시작"):
            st.info("⏳ 다운로드가 시작되었습니다. 고화질은 시간이 오래 걸릴 수 있습니다.")
            title = download_video_audio(url, selected_video_format, selected_audio_format)
            st.success(f"✅ 다운로드 완료: {title}")

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
