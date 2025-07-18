import streamlit as st
from pytube import YouTube, Playlist
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import time
import io

st.set_page_config(page_title="YouTube Downloader", layout="centered")

st.title("📥 YouTube 영상 & 재생목록 다운로드기")
st.markdown("유튜브 링크를 입력하거나, 유튜브 링크를 `wwwyoutube`로 바꾼 후 접속해보세요!")

# 입력창: 유튜브 링크
url_input = st.text_input("유튜브 영상 또는 재생목록 링크를 입력하세요", key="url_input")

# URL 복원: wwwyoutube → www.youtube
def normalize_url(url):
    if url.startswith("https://wwwyoutube"):
        url = url.replace("https://wwwyoutube", "https://www.youtube")
    elif url.startswith("http://wwwyoutube"):
        url = url.replace("http://wwwyoutube", "https://www.youtube")
    return url

# Streamlit Query Parameter에서 링크 자동 복원
def get_url_from_query():
    query_params = st.query_params
    if "v" in query_params:
        params = dict(query_params)
        parsed = urlparse("https://www.youtube.com/watch")
        return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
    return None

# 자동 링크 복원
if not url_input:
    restored_url = get_url_from_query()
    if restored_url:
        st.session_state.url_input = normalize_url(restored_url)
        url_input = st.session_state.url_input

if url_input:
    url_input = normalize_url(url_input)

    try:
        if "playlist" in url_input:
            playlist = Playlist(url_input)
            st.success(f"재생목록 이름: {playlist.title} ({len(playlist.video_urls)}개 영상)")
            for video_url in playlist.video_urls:
                st.write(f"- {video_url}")
        else:
            yt = YouTube(url_input)

            st.subheader(f"🎬 {yt.title}")
            st.write(f"⏱ 길이: {yt.length // 60}분 {yt.length % 60}초")
            st.video(url_input)

            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
            qualities = [f"{s.resolution} - {round(s.filesize / (1024 * 1024), 2)}MB" for s in stream]
            selected_quality = st.selectbox("화질 선택", options=qualities)

            selected_stream = stream[qualities.index(selected_quality)]

            if st.button("📥 다운로드"):
                buffer = io.BytesIO()
                with st.spinner("다운로드 중..."):
                    start = time.time()
                    selected_stream.stream_to_buffer(buffer)
                    end = time.time()

                buffer.seek(0)
                st.success(f"✅ 다운로드 완료! (시간: {round(end - start, 2)}초)")
                st.download_button(label="💾 파일 저장하기", data=buffer, file_name=f"{yt.title}.mp4", mime="video/mp4")

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
