import streamlit as st
from pytube import YouTube
import time

st.set_page_config(page_title="YouTube 다운로더")
st.title("🎬 YouTube 영상 다운로드기")

url = st.text_input("YouTube 영상 URL을 입력하세요")
download_type = st.radio("다운로드 방식 선택", ["🎞️ 영상만", "🔊 소리만", "🎥 영상 + 소리"])

if url:
    try:
        yt = YouTube(url)

        st.video(url)
        st.success(f"제목: {yt.title}")

        progress_text = st.empty()
        progress_bar = st.progress(0)

        def update_progress(stream, chunk, bytes_remaining):
            total = stream.filesize
            downloaded = total - bytes_remaining
            percent = int(downloaded / total * 100)
            progress_bar.progress(percent, text=f"{percent}% 완료")

        yt.register_on_progress_callback(update_progress)

        stream = None

        if download_type == "🎞️ 영상만":
            video_streams = yt.streams.filter(only_video=True, file_extension='mp4').order_by("resolution").desc()
            resolutions = sorted({s.resolution for s in video_streams if s.resolution}, reverse=True)
            selected_resolution = st.selectbox("화질 선택", resolutions)

            stream = next((s for s in video_streams if s.resolution == selected_resolution), None)

        elif download_type == "🔊 소리만":
            audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').order_by("abr").desc().first()
            stream = audio_stream

        elif download_type == "🎥 영상 + 소리":
            prog_streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by("resolution").desc()
            resolutions = sorted({s.resolution for s in prog_streams if s.resolution}, reverse=True)
            selected_resolution = st.selectbox("화질 선택", resolutions)

            stream = next((s for s in prog_streams if s.resolution == selected_resolution), None)

        if stream and st.button("다운로드"):
            filename = f"{yt.title}.mp4" if "video" in stream.mime_type else f"{yt.title}.mp3"

            with st.spinner("다운로드 중..."):
                start = time.time()
                stream.download(filename="temp_file")
                end = time.time()

            st.success(f"다운로드 완료! (소요 시간: {int(end - start)}초)")

            with open("temp_file", "rb") as f:
                st.download_button("파일 다운로드", data=f, file_name=filename, mime=stream.mime_type)

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
