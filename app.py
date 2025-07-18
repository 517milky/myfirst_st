import streamlit as st
import yt_dlp
import os

st.set_page_config(page_title="YouTube 다운로드", layout="centered")
st.title("🎬 YouTube 영상/재생목록 다운로드기")

download_path = "downloads"
os.makedirs(download_path, exist_ok=True)

def download_video(url):
    ydl_opts = {
        'outtmpl': f'{download_path}/%(title)s.%(ext)s',
        'format': 'best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', '영상')

# 쿼리 파라미터 자동 다운로드
query_params = st.experimental_get_query_params()
if 'video' in query_params:
    url = f"https://www.youtube.com/watch?v={query_params['video'][0]}"
    st.experimental_set_query_params()  # 파라미터 제거

    with st.spinner("자동 다운로드 중..."):
        try:
            title = download_video(url)
            st.success(f"✅ 자동 다운로드 완료: {title}")
        except Exception as e:
            st.error(f"❌ 자동 다운로드 오류: {str(e)}")

else:
    # 일반 입력 & 버튼 처리
    url = st.text_input("🔗 유튜브 영상 또는 재생목록 URL을 입력하세요:", "")

    if url and st.button("📥 다운로드 시작"):
        with st.spinner("다운로드 중..."):
            try:
                title = download_video(url)
                st.success(f"✅ 다운로드 완료: {title}")
                st.info(f"폴더 경로: `{os.path.abspath(download_path)}`")
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
