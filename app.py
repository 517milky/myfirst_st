import streamlit as st
import yt_dlp
import os
from urllib.parse import urlparse, parse_qs

# 제목
st.title("🎥 유튜브 다운로드기 (yt-dlp 기반)")

# 유튜브 링크 입력
url = st.text_input("유튜브 링크를 입력하세요:", "")

# 유효한 링크일 때
if "youtube.com/watch" in url or "youtu.be/" in url:
    try:
        # 유튜브 영상 ID 추출
        def extract_video_id(link):
            if "youtu.be" in link:
                return link.split("/")[-1].split("?")[0]
            parsed = urlparse(link)
            return parse_qs(parsed.query).get("v", [None])[0]
        
        video_id = extract_video_id(url)
        if video_id is None:
            st.error("❌ 영상 ID를 찾을 수 없습니다.")
        else:
            # 유튜브 임베드 (미리보기)
            st.video(f"https://www.youtube.com/embed/{video_id}")

            # 영상 정보 가져오기
            with st.spinner("🔍 영상 정보를 불러오는 중..."):
                ydl_opts = {"quiet": True, "skip_download": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

            title = info.get("title", "제목 없음")
            duration = info.get("duration", 0)
            formats = info.get("formats", [])

            st.success(f"✅ 영상 제목: {title}")
            
            # 다운로드 옵션
            mode = st.radio("다운로드 방식 선택:", ["영상+소리", "영상만", "소리만"])

            # 화질 리스트 필터링
            if mode == "영상만":
                filtered = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") == "none"]
            elif mode == "소리만":
                filtered = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
            else:
                filtered = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none"]

            quality_options = [
                f"{f['format_id']} - {f.get('ext', '')} - {f.get('resolution') or f.get('abr', '')} - {round(f.get('filesize', 0)/1024/1024, 2)}MB"
                for f in filtered if f.get("filesize")
            ]
            selected_quality = st.selectbox("화질 선택:", quality_options)

            # 선택한 포맷 아이디 추출
            selected_format_id = selected_quality.split(" - ")[0]
            selected_format_ext = selected_quality.split(" - ")[1]

            # 확장자 선택 (화질 선택 아래 위치)
            if mode == "소리만":
                default_ext = "mp3"
            else:
                default_ext = "mp4"
            ext = st.selectbox("저장할 확장자 선택:", [default_ext, "webm", "mkv", "mp4", "mp3"], index=0)

            if st.button("📥 다운로드 시작"):
                with st.spinner("⏳ 다운로드 중..."):
                    ydl_opts = {
                        "format": selected_format_id,
                        "outtmpl": f"%(title).80s.%(ext)s",
                        "merge_output_format": ext,
                        "quiet": True,
                        "postprocessors": [],
                    }

                    # ffmpeg 없이 병합 불가시 fallback 방지
                    if mode == "영상+소리" and selected_format_ext != ext:
                        st.warning(f"⚠️ 선택한 화질의 확장자({selected_format_ext})와 저장 확장자({ext})가 다르면 병합이 불가능할 수 있습니다.")

                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            result = ydl.download([url])
                        st.success("✅ 다운로드 완료")
                    except Exception as e:
                        st.error(f"❌ 오류 발생: {str(e)}")

    except Exception as e:
        st.error(f"❌ 영상 정보를 불러올 수 없습니다: {str(e)}")
else:
    st.info("🔗 유튜브 링크를 입력해주세요.")
