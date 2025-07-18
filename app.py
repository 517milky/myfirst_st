import streamlit as st
from pytube import YouTube
import os
import uuid
import subprocess

def clean_url(url):
    if url.startswith("https://wwwyoutube"):
        url = url.replace("wwwyoutube", "www.youtube")
    return url

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

def download_stream(youtube_obj, only_audio=False, high_quality=False):
    if only_audio:
        audio_stream = youtube_obj.streams.filter(only_audio=True).order_by("abr").desc().first()
        return audio_stream.download()
    if high_quality:
        video_stream = youtube_obj.streams.filter(progressive=False, file_extension="mp4").order_by("resolution").desc().first()
        audio_stream = youtube_obj.streams.filter(only_audio=True).order_by("abr").desc().first()
        if video_stream and audio_stream:
            st.info("⏳ 고화질 영상 및 오디오 다운로드 중입니다. 시간이 오래 걸릴 수 있습니다.")
            video_path = video_stream.download(filename_prefix="video_")
            audio_path = audio_stream.download(filename_prefix="audio_")
            output_path = f"merged_{uuid.uuid4()}.mp4"
            merge_video_audio(video_path, audio_path, output_path)
            os.remove(video_path)
            os.remove(audio_path)
            return output_path
    else:
        stream = youtube_obj.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
        return stream.download()

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("📥 YouTube 영상 다운로드")

url_input = st.text_input("🔗 YouTube 링크를 입력하세요:")

if url_input:
    url = clean_url(url_input)
    try:
        yt = YouTube(url)
        st.video(url)

        st.subheader("🎬 영상 정보")
        st.image(yt.thumbnail_url)
        st.write(f"**제목:** {yt.title}")
        st.write(f"**길이:** {yt.length}초")
        st.write(f"**채널:** {yt.author}")

        st.subheader("⬇️ 다운로드 옵션")
        col1, col2, col3 = st.columns(3)
        with col1:
            video_only = st.button("🎞️ 영상만 다운로드")
        with col2:
            audio_only = st.button("🎧 오디오만 다운로드")
        with col3:
            both_high = st.button("💎 고화질 영상+오디오 다운로드")

        if both_high:
            filepath = download_stream(yt, high_quality=True)
            st.success("✅ 다운로드 완료!")
            with open(filepath, "rb") as f:
                st.download_button("📥 영상 다운로드", f, file_name="merged_video.mp4")
            os.remove(filepath)

        elif video_only:
            filepath = download_stream(yt, only_audio=False, high_quality=False)
            st.success("✅ 다운로드 완료!")
            with open(filepath, "rb") as f:
                st.download_button("📥 영상 다운로드", f, file_name="video_only.mp4")
            os.remove(filepath)

        elif audio_only:
            filepath = download_stream(yt, only_audio=True)
            st.success("✅ 다운로드 완료!")
            with open(filepath, "rb") as f:
                st.download_button("📥 오디오 다운로드", f, file_name="audio_only.mp3")
            os.remove(filepath)

    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
