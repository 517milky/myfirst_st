import streamlit as st
from pytube import YouTube
import os
import time
import uuid

# 🔧 저장 폴더 설정
SAVE_PATH = "./downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

# 🔤 스트림릿 UI
st.title("🎬 YouTube 영상 다운로드기")

url = st.text_input("YouTube 영상 링크를 입력하세요")

if url:
    try:
        yt = YouTube(url)
        st.subheader("🔎 영상 정보")
        st.write(f"**제목:** {yt.title}")
        st.write(f"**길이:** {yt.length // 60}분 {yt.length % 60}초")
        st.image(yt.thumbnail_url, use_container_width=True)  # ✅ 최신 옵션 반영

        download_type = st.radio("다운로드 방식 선택", ["🎞 영상 + 소리", "🎥 영상만", "🎵 소리만"])

        # 확장자 기본 설정
        default_ext = "mp4" if "소리" not in download_type else "mp3"
        file_ext = st.selectbox("🔽 저장 확장자 선택", ["mp4", "mkv", "webm", "mp3", "wav"], index=["mp4", "mkv", "webm", "mp3", "wav"].index(default_ext))

        # 화질 선택은 "영상 + 소리"인 경우에만 보여줌
        resolution = None
        if download_type == "🎞 영상 + 소리":
            resolutions = sorted({stream.resolution for stream in yt.streams.filter(progressive=True, file_extension="mp4") if stream.resolution}, reverse=True)
            if resolutions:
                resolution = st.selectbox("🎚 다운로드 화질 선택", resolutions)
            else:
                st.warning("해당 영상은 병합된 스트림(영상+소리)이 없습니다.")

        if st.button("📥 다운로드 시작"):
            start_time = time.time()
            unique_id = uuid.uuid4().hex[:8]
            file_name = f"download_{unique_id}.{file_ext}"
            output_path = os.path.join(SAVE_PATH, file_name)

            try:
                if download_type == "🎞 영상 + 소리":
                    stream = yt.streams.filter(progressive=True, file_extension="mp4", resolution=resolution).first()
                    if not stream:
                        st.error("선택한 화질의 영상+소리 스트림이 없습니다.")
                    else:
                        with st.spinner("다운로드 중..."):
                            stream.download(output_path=SAVE_PATH, filename=file_name)
                            time.sleep(1)

                elif download_type == "🎥 영상만":
                    stream = yt.streams.filter(only_video=True, file_extension=file_ext).order_by("resolution").desc().first()
                    if stream:
                        with st.spinner("영상 다운로드 중..."):
                            stream.download(output_path=SAVE_PATH, filename=file_name)
                            time.sleep(1)
                    else:
                        st.error("영상 스트림을 찾을 수 없습니다.")

                elif download_type == "🎵 소리만":
                    stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                    if stream:
                        with st.spinner("오디오 다운로드 중..."):
                            stream.download(output_path=SAVE_PATH, filename=file_name)
                            time.sleep(1)
                    else:
                        st.error("오디오 스트림을 찾을 수 없습니다.")

                elapsed_time = round(time.time() - start_time, 2)
                st.success(f"✅ 다운로드 완료! (소요 시간: {elapsed_time}초)")
                with open(output_path, "rb") as file:
                    st.download_button(label="⬇ 파일 다운로드", data=file, file_name=file_name, mime="application/octet-stream")

            except Exception as e:
                st.error(f"❌ 오류 발생: {e}")

    except Exception as e:
        st.error(f"❌ 영상 정보를 불러올 수 없습니다: {e}")
