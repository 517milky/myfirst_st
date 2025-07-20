import streamlit as st
import yt_dlp
from PIL import Image
from io import BytesIO
import requests
import os

st.set_page_config(page_title="유튜브 재생목록 다운로드", layout="wide")
st.title("📥 유튜브 재생목록 다운로드")

FORMAT_OPTIONS = ["영상+소리", "영상만", "소리만"]

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def fetch_playlist_info(playlist_url):
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            entries = info.get("entries", [])
            title = info.get("title", "재생목록")
            # entries는 dict 리스트, 각 항목에 'url', 'title', 'duration', 'thumbnail' 등 있음
            return entries, title
    except Exception as e:
        return [], ""

def fetch_video_info(video_url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info
    except Exception as e:
        return None

def get_thumbnail_image(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

playlist_url = st.text_input("🔗 유튜브 재생목록 URL 입력")

if playlist_url:
    with st.spinner("재생목록 정보 불러오는 중..."):
        entries, playlist_title = fetch_playlist_info(playlist_url)

    if not entries:
        st.error("재생목록을 불러올 수 없거나 비어 있습니다.")
    else:
        total_videos = len(entries)
        st.success(f"총 {total_videos}개의 영상이 발견되었습니다.")
        st.markdown(f"### 재생목록명: {playlist_title}")

        # 진행률 표시
        progress_placeholder = st.empty()
        loaded_videos = []

        # 영상 정보 상세 불러오기
        detailed_video_data = []
        for idx, entry in enumerate(entries):
            video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
            info = fetch_video_info(video_url)
            if info:
                detailed_video_data.append(info)
            progress_placeholder.progress((idx + 1) / total_videos, text=f"영상 {idx + 1}/{total_videos} 불러오는 중...")
        progress_placeholder.empty()
        st.success(f"영상 목록이 모두 불러와졌습니다. 총 {len(detailed_video_data)}개 영상")

        # 전체 옵션
        st.subheader("⚙️ 전체 옵션")
        col1, col2 = st.columns(2)
        with col1:
            global_format = st.selectbox("전체 다운로드 형식", FORMAT_OPTIONS)
        with col2:
            # 공통 해상도 구하기 (모든 영상이 공통으로 지원하는 해상도)
            all_res_sets = [set(stream["format_note"] for stream in video["formats"] if stream.get("format_note")) for video in detailed_video_data]
            common_resolutions = set.intersection(*all_res_sets) if all_res_sets else set()
            common_resolutions = sorted(common_resolutions, reverse=True)
            if common_resolutions:
                global_res = st.selectbox("전체 해상도 선택", common_resolutions)
            else:
                global_res = None
                st.markdown("_공통 해상도 없음_")

        st.divider()
        st.subheader("📂 영상 목록")

        download_status = [("대기 중", 0) for _ in detailed_video_data]

        # 각 영상별 UI
        for i, video in enumerate(detailed_video_data):
            with st.container():
                cols = st.columns([1, 4, 2, 2, 2])

                # 썸네일
                thumb_url = video.get("thumbnail")
                if thumb_url:
                    thumb_img = get_thumbnail_image(thumb_url)
                    if thumb_img:
                        cols[0].image(thumb_img.resize((120, 70)), use_container_width=False)
                    else:
                        cols[0].write("썸네일 없음")
                else:
                    cols[0].write("썸네일 없음")

                # 제목 + 길이
                title = video.get("title", "제목 없음")
                length = video.get("duration", 0)
                mins, secs = divmod(length, 60)
                cols[1].markdown(f"**{title}**")
                cols[1].caption(f"⏱️ {mins}분 {secs}초")

                # 다운로드 형식 선택
                selected_format = cols[2].selectbox(f"형식 선택 {i+1}", FORMAT_OPTIONS, key=f"format_{i}")

                # 해상도 선택 (해당 영상이 지원하는 해상도만)
                available_res = sorted(set(stream["format_note"] for stream in video["formats"] if stream.get("format_note")), reverse=True)
                default_res = global_res if global_res in available_res else (available_res[0] if available_res else None)
                if default_res:
                    selected_res = cols[3].selectbox(f"해상도 선택 {i+1}", available_res, index=available_res.index(default_res), key=f"res_{i}")
                else:
                    selected_res = None
                    cols[3].write("해상도 없음")

                # 다운로드 버튼
                if cols[4].button("⬇️ 다운로드", key=f"btn_{i}"):
                    st.info(f"다운로드 기능은 여기에 구현하세요. 영상 {title}")

                # 진행도 표시 (예시)
                label, perc = download_status[i]
                st.progress(perc / 100, text=f"{label} ({perc}%)")

