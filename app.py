import streamlit as st
from pytube import YouTube
import time
import os

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
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
            progress_bar.progress(percent)
            progress_text.text(f"📦 다운로드 중: {percent}%")

        yt.register_on_progress_callback(update_progress)

        stream = None

        if download_type == "🎞️ 영상만":
            video_streams = yt.streams.filter(only_video=True, file_extension='mp4').order_by("resolution").desc()
            resolutions = sorted({s.resolution for s in video_streams if s.resolution}, reverse=True)
            selected_resolution = st.selectbox("화질 선택", resolutions)
            stream = next((s for s in video_streams if s.resolution == selected_resolution), None)

        elif download_type == "🔊 소리만":
            audio_streams = yt.streams.filter(only_audio=True, file_extension='mp4').order_by("abr").desc()
            stream = audio_streams.first()

        elif download_type == "🎥 영상 + 소리":
            prog_streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by("resolution").desc()
            if not prog_streams:
                st.warning("⚠️ 이 영상은 영상+소리 스트림을 지원하지 않습니다.\n'영상만' 또는 '소리만'으로 시도해 주세요.")
            else:
                resolutions = sorted({s.resolution for s in prog_streams if s.resolution}, reverse=True)
                selected_resolution = st.selectbox("화질 선택", resolutions)
                stream = next((s for s in prog_streams if s.resolution == selected_resolution), None)

        if stream and st.button("📥 다운로드 시작"):
            filename = f"{yt.title}.{stream.mime_type.split('/')[-1]}"
            temp_path = "temp_file"

            with st.spinner("⌛ 다운로드 중..."):
                start = time.time()
                try:
                    stream.download(filename=temp_path)
                except Exception as e:
                    st.error(f"❌ 다운로드 실패: {e}")
                    st.stop()
                end = time.time()

            st.success(f"✅ 다운로드 완료! (소요 시간: {int(end - start)}초)")

            with open(temp_path, "rb") as f:
                st.download_button("⬇️ 파일 다운로드", data=f, file_name=filename, mime=stream.mime_type)

            # 임시 파일 삭제
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
