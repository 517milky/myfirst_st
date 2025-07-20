import streamlit as st
from yt_dlp import YoutubeDL
from datetime import timedelta
import threading

st.set_page_config(page_title="YouTube 재생목록 다운로드", layout="wide")

# 전역 상태
if "playlist_videos" not in st.session_state:
    st.session_state.playlist_videos = []
if "playlist_title" not in st.session_state:
    st.session_state.playlist_title = ""
if "selected" not in st.session_state:
    st.session_state.selected = set()
if "download_options" not in st.session_state:
    st.session_state.download_options = {}
if "loading_progress" not in st.session_state:
    st.session_state.loading_progress = 0.0
if "loading_text" not in st.session_state:
    st.session_state.loading_text = ""
if "all_selected" not in st.session_state:
    st.session_state.all_selected = False
if "all_download_mode" not in st.session_state:
    st.session_state.all_download_mode = "영상+소리"
if "all_quality" not in st.session_state:
    st.session_state.all_quality = "480p"

ALL_QUALITIES = ["144p", "240p", "360p", "480p", "720p", "1080p"]
DOWNLOAD_MODES = ["영상+소리", "영상만", "소리만"]

def get_video_info(url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

def get_playlist_info(url, progress_callback=None):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get("entries", [])
        videos = []
        total = len(entries)
        for i, entry in enumerate(entries):
            if progress_callback:
                progress_callback(i+1, total)
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            video_info = get_video_info(video_url)
            videos.append((video_info, video_url))
        return info.get("title", "재생목록"), videos

def show_loading_progress(count, total):
    st.session_state.loading_progress = count / total
    st.session_state.loading_text = f"영상 정보 불러오는 중... ({count}/{total})"

tab1, tab2 = st.tabs(["단일 영상", "재생목록"])

with tab1:
    st.info("단일 영상 탭은 링크 입력창이 없으니 one.py 사용하세요.")

with tab2:
    playlist_url = st.text_input("재생목록 URL 입력")

    progress_bar = st.progress(st.session_state.loading_progress)
    st.write(st.session_state.loading_text)

    if playlist_url and st.button("목록 불러오기 (오래 걸릴 수 있음)"):
        st.session_state.playlist_videos = []
        st.session_state.selected = set()
        st.session_state.download_options = {}
        st.session_state.playlist_title = ""
        st.session_state.loading_progress = 0.0
        st.session_state.loading_text = "불러오는 중..."

        def load_playlist():
            try:
                title, videos = get_playlist_info(playlist_url, progress_callback=show_loading_progress)
                st.session_state.playlist_title = title
                st.session_state.playlist_videos = videos
                st.session_state.loading_progress = 1.0
                st.session_state.loading_text = f"총 {len(videos)}개 영상 불러옴"
            except Exception as e:
                st.session_state.loading_text = f"오류 발생: {e}"

        threading.Thread(target=load_playlist).start()

    videos = st.session_state.playlist_videos
    if videos:
        st.write(f"재생목록: **{st.session_state.playlist_title}**")
        # 전체 선택 및 전체 옵션 UI
        col1, col2, col3, col4 = st.columns([1,1,1,1])
        with col1:
            all_sel = st.checkbox("전체 선택/해제", value=st.session_state.all_selected)
        with col2:
            all_mode = st.selectbox("전체 다운로드 방식", DOWNLOAD_MODES, index=DOWNLOAD_MODES.index(st.session_state.all_download_mode))
        with col3:
            all_qual = st.selectbox("전체 해상도", ALL_QUALITIES, index=ALL_QUALITIES.index(st.session_state.all_quality))
        with col4:
            if st.button("전체 영상에 옵션 적용"):
                # 전체 영상에 옵션 및 선택 적용
                st.session_state.all_selected = True
                st.session_state.selected = set(range(len(videos)))
                st.session_state.all_download_mode = all_mode
                st.session_state.all_quality = all_qual
                for idx, (info, url) in enumerate(videos):
                    st.session_state.download_options[url] = {
                        "mode": all_mode,
                        "quality": all_qual if all_mode != "소리만" else None
                    }

        # 개별 영상 리스트
        for idx, (info, url) in enumerate(videos):
            cols = st.columns([0.8, 3, 1, 2, 2, 1])
            with cols[0]:
                st.image(info['thumbnail'], width=80)
            with cols[1]:
                st.write(f"{idx+1}. {info['title']}")
            with cols[2]:
                st.write(str(timedelta(seconds=info.get('duration', 0))))
            with cols[3]:
                # 다운로드 방식 선택
                mode_current = st.session_state.download_options.get(url, {}).get("mode", DOWNLOAD_MODES[0])
                mode = st.selectbox(f"mode_{idx}", DOWNLOAD_MODES, index=DOWNLOAD_MODES.index(mode_current), key=f"mode_{idx}")
            with cols[4]:
                # 지원 해상도만 표시
                # 지원 해상도 필터링 함수
                def filter_quality(info, mode):
                    formats = info.get("formats", [])
                    available_heights = set()
                    for f in formats:
                        if f.get("height"):
                            available_heights.add(f["height"])
                    available_heights = sorted(available_heights)
                    def p_to_int(p):
                        return int(p.replace("p", ""))
                    filtered = [q for q in ALL_QUALITIES if p_to_int(q) in available_heights]
                    if mode == "소리만":
                        return []
                    return filtered
                qualities = filter_quality(info, mode)
                qual_current = st.session_state.download_options.get(url, {}).get("quality", qualities[0] if qualities else None)
                if qualities:
                    quality = st.selectbox(f"quality_{idx}", qualities, index=qualities.index(qual_current) if qual_current in qualities else 0, key=f"quality_{idx}")
                else:
                    quality = None
                    st.write("-")
            with cols[5]:
                # 선택 체크박스
                selected = st.checkbox("선택", key=f"select_{idx}", value=(idx in st.session_state.selected))
                if selected:
                    st.session_state.selected.add(idx)
                else:
                    st.session_state.selected.discard(idx)
            # 상태 반영
            st.session_state.download_options[url] = {"mode": mode, "quality": quality}

        # 개별 영상 미리보기는 목록 클릭 대신 버튼 따로 둠
        preview_idx = st.number_input("미리보기 할 영상 번호 입력", min_value=1, max_value=len(videos), step=1)
        if st.button("미리보기 재생"):
            st.video(videos[preview_idx-1][0].get("url"))

        # 개별 영상 추가 / 삭제
        add_url = st.text_input("목록에 영상 URL 추가")
        if st.button("영상 추가"):
            try:
                new_info = get_video_info(add_url)
                st.session_state.playlist_videos.append((new_info, add_url))
                st.success("영상 추가 완료")
            except Exception as e:
                st.error(f"영상 추가 실패: {e}")

        delete_idx = st.number_input("삭제할 영상 번호 입력", min_value=1, max_value=len(st.session_state.playlist_videos), step=1)
        if st.button("영상 삭제"):
            try:
                del st.session_state.playlist_videos[delete_idx-1]
                st.success("영상
