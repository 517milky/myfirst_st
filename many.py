# many.py
import streamlit as st
import yt_dlp
import os
import concurrent.futures
import tempfile
import shutil
from datetime import timedelta

def fetch_playlist_flat(url):
    opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def fetch_video_info(url):
    opts = {'quiet': True, 'skip_download': True, 'noplaylist': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def download_video(url, mode, quality, out_dir, progress_callback=None):
    # format 코드 맵핑
    res_map = {
        "144p": "160",
        "240p": "133",
        "360p": "134",
        "480p": "135",
        "720p": "136",
        "1080p": "137",
    }
    # ffmpeg 병합 회피: 영상+소리는 480p 이하만 허용
    if mode == "영상+소리":
        allowed_heights = ["144", "240", "360", "480"]
        height_num = quality.replace("p", "")
        if height_num not in allowed_heights:
            height_num = "480"
        format_str = f'best[height<={height_num}][vcodec!=none][acodec!=none]/best'
    elif mode == "영상만":
        format_str = res_map.get(quality, "134")
    else:  # 소리만
        format_str = "bestaudio"

    ydl_opts = {
        'format': format_str,
        'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'progress_hooks': [progress_callback] if progress_callback else [],
        'postprocessors': [] 
    }

    if mode == "소리만":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
    return info

def main():
    st.title("YouTube 재생목록 다운로드기")

    playlist_url = st.text_input("YouTube 재생목록 URL 입력")

    if not playlist_url:
        st.info("재생목록 URL을 입력해주세요.")
        return

    with st.spinner("재생목록 영상 목록 불러오는 중..."):
        try:
            # 비동기로 재생목록 평탄 정보 로드
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(fetch_playlist_flat, playlist_url)
                playlist_info = future.result()
        except Exception as e:
            st.error(f"재생목록 정보를 불러올 수 없습니다: {e}")
            return

    videos = playlist_info.get('entries', [])
    playlist_title = playlist_info.get('title', 'playlist').replace(" ", "_")
    st.success(f"총 {len(videos)}개 영상 발견: '{playlist_title}'")

    # 영상별 선택, 다운로드 설정 저장용 리스트
    video_settings = []

    st.write("---")
    for i, vid in enumerate(videos):
        # 재생목록 평탄모드이므로 vid는 dict, url은 상대경로일 수 있으니 https://youtube.com/watch?v= 붙여서 완성
        vid_url = vid.get('url')
        if vid_url and not vid_url.startswith("http"):
            vid_url = f"https://www.youtube.com/watch?v={vid_url}"

        with st.expander(f"영상 {i+1} 미리보기 & 설정", expanded=False):
            try:
                info = fetch_video_info(vid_url)
                st.video(info.get('url'))

                st.write("길이:", str(timedelta(seconds=info.get('duration',0))))

                mode = st.radio("다운로드 방식", ["영상+소리", "영상만", "소리만"], key=f"mode_{i}")
                if mode in ["영상+소리", "영상만"]:
                    quality = st.selectbox("화질 선택", ["1080p", "720p", "480p", "360p"], index=2, key=f"quality_{i}")
                else:
                    quality = "최고 음질"
                
                selected = st.checkbox("이 영상 선택", key=f"select_{i}")
                video_settings.append((vid_url, mode, quality, selected))

            except Exception as e:
                st.error(f"영상을 불러오는 중 오류 발생: {e}")

    st.write("---")

    if st.button("선택한 영상들 다운로드"):
        selected_videos = [v for v in video_settings if v[3]]
        if not selected_videos:
            st.warning("다운로드할 영상을 하나 이상 선택하세요.")
            return

        os.makedirs(playlist_title, exist_ok=True)

        for idx, (url, mode, quality, _) in enumerate(selected_videos):
            st.write(f"{idx+1}. 다운로드 시작: {url}")

            progress_bar = st.progress(0, key=f"prog_{idx}")
            status_text = st.empty()

            def progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded = d.get('downloaded_bytes', 0)
                    percent = downloaded / total if total else 0
                    status_text.text(f"진행률: {percent*100:.1f}%")
                    progress_bar.progress(min(percent,1.0))
                elif d['status'] == 'finished':
                    progress_bar.progress(1.0)
                    status_text.text("✅ 다운로드 완료!")

            try:
                download_video(url, mode, quality, playlist_title, progress_callback=progress_hook)
            except Exception as e:
                st.error(f"다운로드 실패: {e}")

        st.success("모든 선택한 영상 다운로드 완료!")

if __name__ == "__main__":
    main()

