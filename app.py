import streamlit as st
from yt_dlp import YoutubeDL
from datetime import timedelta
import threading
import time

st.set_page_config(page_title="YouTube 재생목록 다운로드", layout="wide")

# ---------- 전역 변수 --------------
playlist_videos = []  # [(info_dict, url), ...]
download_progress = {}  # url : (percent, eta)
video_preview_url = None
selected_videos = set()
download_options = {}  # url : {'mode': ..., 'quality': ...}

# 해상도 옵션
ALL_QUALITIES = ["144p", "240p", "360p", "480p", "720p", "1080p"]
# 다운로드 방식 옵션
DOWNLOAD_MODES = ["영상+소리", "영상만", "소리만"]

# 지원 해상도 필터링 함수
def filter_quality(info, mode):
    # 영상의 available formats에서 지원 해상도 수집
    formats = info.get("formats", [])
    available_heights = set()
    for f in formats:
        if f.get("height"):
            available_heights.add(f["height"])
    available_heights = sorted(available_heights)
    # 스트림릿에서 표시할 해상도 리스트 생성 (height에 맞춰)
    # ALL_QUALITIES 중 지원하는 것만 반환
    def p_to_int(p):
        return int(p.replace("p", ""))
    filtered = [q for q in ALL_QUALITIES if p_to_int(q) in available_heights]
    if mode == "소리만":
        return []  # 소리만이면 해상도 선택 숨김
    return filtered

# 영상 개별 정보 가져오기
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

# 재생목록 정보 가져오기 (일괄 로드)
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
            # 진행 콜백 호출
            if progress_callback:
                progress_callback(i+1, total)
            # entry는 딕셔너리; url은 videoId가 아닌 전체 url 필요
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            video_info = get_video_info(video_url)
            videos.append((video_info, video_url))
        return info.get("title", "재생목록"), videos

# 진행률 콜백 UI용
def show_loading_progress(count, total):
    progress = count / total
    st.session_state["loading_progress"] = progress
    st.session_state["loading_text"] = f"영상 정보 불러오는 중... ({count}/{total})"

# ---------- UI 시작 --------------

st.title("📺 YouTube 재생목록 다운로드기")

tab1, tab2 = st.tabs(["단일 영상", "재생목록"])

# 단일 영상 탭: (요청대로 링크 입력창 없음)
with tab1:
    st.info("단일 영상 다운로드 기능은 별도 파일 (one.py)에서 처리합니다.")

# 재생목록 탭
with tab2:
    playlist_url = st.text_input("재생목록 URL 입력")

    # 재생목록 로딩 진행률 표시
    if "loading_progress" not in st.session_state:
        st.session_state["loading_progress"] = 0.0
    if "loading_text" not in st.session_state:
        st.session_state["loading_text"] = ""

    progress_bar = st.progress(st.session_state["loading_progress"])
    progress_text = st.empty()
    progress_text.text(st.session_state["loading_text"])

    if playlist_url:
        if st.button("목록 불러오기 (오래 걸릴 수 있음)"):
            st.session_state["playlist_videos"] = []
            st.session_state["selected_videos"] = set()
            st.session_state["download_options"] = {}
            st.session_state["video_preview_url"] = None
            st.session_state["loading_progress"] = 0.0
            st.session_state["loading_text"] = "불러오는 중..."

            # 실제 재생목록 로드 (스레드로 처리해 UI 멈춤 방지)
            def load_playlist():
                try:
                    title, videos = get_playlist_info(playlist_url, progress_callback=show_loading_progress)
                    st.session_state["playlist_title"] = title
                    st.session_state["playlist_videos"] = videos
                    st.session_state["loading_progress"] = 1.0
                    st.session_state["loading_text"] = f"총 {len(videos)}개 영상 불러옴"
                except Exception as e:
                    st.session_state["loading_text"] = f"오류 발생: {e}"

            threading.Thread(target=load_playlist).start()

    # 영상 목록 표시 (엑셀/커뮤니티 글 목록 느낌)
    videos = st.session_state.get("playlist_videos", [])
    if videos:
        # 전체 선택 박스
        all_selected = st.checkbox("전체 선택 / 해제", key="all_select")

        # 강제 전체 선택 처리
        if all_selected:
            st.session_state["selected_videos"] = set(range(len(videos)))
        else:
            # 전체 해제 시 선택 초기화
            st.session_state["selected_videos"] = set()

        # 목록 테이블 (가로 columns 배치)
        for idx, (info, url) in enumerate(videos):
            cols = st.columns([0.7, 3, 1, 1, 1])
            with cols[0]:
                st.image(info['thumbnail'], width=80)
            with cols[1]:
                # 제목 + 클릭 시 미리보기 토글
                if st.button(f"{idx+1}. {info['title']}", key=f"title_btn_{idx}"):
                    if st.session_state.get("video_preview_url") == url:
                        st.session_state["video_preview_url"] = None
                    else:
                        st.session_state["video_preview_url"] = url
            with cols[2]:
                st.write(str(timedelta(seconds=info.get('duration', 0))))
            with cols[3]:
                # 다운로드 방식 선택
                mode = st.selectbox(f"mode_{idx}", DOWNLOAD_MODES, key=f"mode_{idx}")
                download_options[url] = download_options.get(url, {})
                download_options[url]['mode'] = mode
            with cols[4]:
                # 해상도 선택 (모드에 따라 비활성화 처리)
                qualities = filter_quality(info, mode)
                if qualities:
                    quality = st.selectbox(f"quality_{idx}", qualities, key=f"quality_{idx}")
                else:
                    quality = None
                download_options[url]['quality'] = quality

            # 선택 체크박스
            selected = st.checkbox("선택", key=f"select_{idx}")
            if selected:
                st.session_state["selected_videos"].add(idx)
            else:
                st.session_state["selected_videos"].discard(idx)

            # 진행률 및 예상 시간 표시 (가상의 예시, 다운로드 시 업데이트)
            progress_placeholder = st.empty()
            progress_placeholder.text("진행률: - | 예상 시간: -")

            # 영상 미리보기 영역
            if st.session_state.get("video_preview_url") == url:
                st.video(info.get('url'))

        # 영상 추가 / 삭제
        add_url = st.text_input("목록에 영상 URL 추가")
        if st.button("영상 추가"):
            try:
                new_info = get_video_info(add_url)
                videos.append((new_info, add_url))
                st.success("영상 추가 완료")
            except Exception as e:
                st.error(f"영상 추가 실패: {e}")

        delete_idx = st.number_input("삭제할 영상 번호 입력", min_value=1, max_value=len(videos), step=1)
        if st.button("영상 삭제"):
            try:
                del videos[delete_idx-1]
                st.success("영상 삭제 완료")
            except Exception as e:
                st.error(f"영상 삭제 실패: {e}")

        # 전체 다운로드 버튼
        if st.button("선택한 영상 전체 다운로드"):
            selected_idxes = list(st.session_state.get("selected_videos", []))
            if not selected_idxes:
                st.warning("다운로드할 영상을 선택해주세요.")
            else:
                st.success(f"{len(selected_idxes)}개 영상 다운로드 시작")
                # 다운로드 로직 여기에 추가 (스레드로 처리 권장)
                # 각 영상별 진행률/예상 시간 갱신 가능하도록 구현

