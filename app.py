import streamlit as st
from pytube import YouTube
import time
import os
import uuid

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("🎬 YouTube 영상 다운로드기")

# --- 유저 입력 ---
url = st.text_input("유튜브 링크를 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

if url:
    try:
        yt = YouTube(url)
        st.markdown(f"**제목:** {yt.title}")
        st.markdown(f"**길이:** {yt.length // 60}분 {yt.length % 60}초")
    except Exception as e:
        st.error(f"❌ 영상 정보를 불러올 수 없습니다: {e}")
        st.stop()

    # --- 다운로드 설정 ---
    download_type = st.radio("다운로드 방식 선택", ["영상 + 소리", "영상만", "소리만"], horizontal=True)

    # 확장자 설정
    default_ext = "mp4" if download_type != "소리만" else "mp3"
    ext_options = ["mp4", "webm", "mkv"] if download_type != "소리만" else ["mp3", "m4a", "wav"]
    file_ext = st.selectbox("파일 확장자 선택", ext_options, index=ext_options.index(default_ext))

    # 화질 설정 (영상+소리인 경우만)
    selected_res = None
    if download_type == "영상 + 소리":
        available_streams = yt.streams.filter(progressive=True, file_extension=file_ext).order_by('resolution').desc()
        resolutions = [s.resolution for s in available_streams if s.resolution is not None]
        resolutions = sorted(set(resolutions), reverse=True)
        if resolutions:
            selected_res = st.selectbox("화질 선택", resolutions)
        else:
            st.warning("선택 가능한 화질이 없습니다.")
            st.stop()

    # 다운로드 버튼
    if st.button("📥 다운로드 시작"):
        start_time = time.time()
        st.info("⏬ 다운로드 중입니다...")

        try:
            filename = f"download_{uuid.uuid4().hex[:8]}.{file_ext}"

            if download_type == "영상 + 소리":
                stream = yt.streams.filter(progressive=True, file_extension=file_ext, resolution=selected_res).first()
            elif download_type == "영상만":
                stream = yt.streams.filter(only_video=True, file_extension=file_ext).order_by('resolution').desc().first()
            elif download_type == "소리만":
                stream = yt.streams.filter(only_audio=True, file_extension=file_ext).first()
            else:
                stream = None

            if not stream:
                st.error("❌ 해당 조건에 맞는 스트림을 찾을 수 없습니다.")
                st.stop()

            stream.download(filename=filename)

            elapsed = round(time.time() - start_time)
            st.success(f"✅ 다운로드 완료! (소요 시간: {elapsed}초)")
            with open(filename, "rb") as f:
                btn = st.download_button(
                    label="📁 다운로드 파일 저장",
                    data=f,
                    file_name=filename,
                    mime="video/mp4" if file_ext in ["mp4", "webm", "mkv"] else "audio/mpeg",
                    use_container_width=True,
                )
            os.remove(filename)

        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
