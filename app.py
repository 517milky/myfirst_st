import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import time
from threading import Thread

st.set_page_config(page_title="YouTube 다운로드 웹앱", layout="wide")

def format_bytes(size):
    # 바이트 단위 표시 포맷
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def download_hook(d):
    if d['status'] == 'downloading':
        current = d.get('_percent_str', '').strip()
        speed = d.get('_speed_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        st.session_state['progress'] = {
            'current': current,
            'speed': speed,
            'eta': eta
        }

def get_video_info(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

def render_video_preview(url):
    st.video(url)

def download_video(url, mode, resolution, file_format, output_dir):
    ydl_opts = {
        'quiet': True,
        'progress_hooks': [download_hook],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s')
    }

    if mode == 'video+audio':
        ydl_opts['format'] = f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]'
    elif mode == 'video':
        ydl_opts['format'] = f'bestvideo[height<={resolution}]'
    elif mode == 'audio':
        ydl_opts['format'] = 'bestaudio'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3' if file_format == 'mp3' else 'm4a'
        }]

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def playlist_info(playlist_url):
    ydl_opts = {'quiet': True, 'extract_flat': True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    return info

st.title("YouTube 다운로드 웹앱")

url = st.text_input("YouTube 링크를 입력하세요")

if url:
    if "playlist" in url:
        st.subheader("🔗 재생목록 처리")
        if st.button("목록 미리 확인"):
            st.warning("재생목록 확인은 시간이 오래 걸릴 수 있습니다.")
            with st.spinner("재생목록 불러오는 중..."):
                try:
                    playlist = playlist_info(url)
                    st.success(f"총 {len(playlist['entries'])}개 영상이 감지되었습니다.")
                    for idx, video in enumerate(playlist['entries'], start=1):
                        st.markdown(f"**{idx}.** [{video['title']}]({video['url']})")
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

        if st.button("바로 다운로드"):
            try:
                with st.spinner("재생목록 다운로드 중..."):
                    playlist = playlist_info(url)
                    output_dir = tempfile.mkdtemp()
                    for i, video in enumerate(playlist['entries']):
                        st.markdown(f"**({i+1}/{len(playlist['entries'])}) 다운로드 중...**")
                        download_video(video['url'], 'video+audio', '1080', 'mp4', output_dir)
                    st.success(f"다운로드 완료! 폴더: {output_dir}")
            except Exception as e:
                st.error(f"다운로드 오류: {str(e)}")

    else:
        st.subheader("🎬 단일 영상 다운로드")

        try:
            info = get_video_info(url)
            render_video_preview(info['webpage_url'])

            mode = st.radio("다운로드 방식 선택", ['video+audio', 'video', 'audio'])
            if mode == 'audio':
                file_format = st.selectbox("파일 형식", ['mp3', 'm4a'])
                resolution = None
            else:
                resolution = st.selectbox("해상도", ['2160', '1440', '1080', '720', '480', '360', '240'])
                file_format = 'mp4'

            if st.button("다운로드 시작"):
                st.session_state['progress'] = {}
                output_dir = tempfile.mkdtemp()

                def run_download():
                    download_video(url, mode, resolution, file_format, output_dir)

                thread = Thread(target=run_download)
                thread.start()

                progress_bar = st.progress(0)
                while thread.is_alive():
                    prog = st.session_state.get('progress', {})
                    percent_str = prog.get('current', '0%').replace('%', '')
                    try:
                        percent = float(percent_str) / 100
                        progress_bar.progress(min(max(percent, 0.0), 1.0))
                        st.write(
                            f"진행률: {prog.get('current', '?')} / 속도: {prog.get('speed', '?')} / 남은 시간: {prog.get('eta', '?')}초")
                    except:
                        pass
                    time.sleep(1)

                thread.join()
                st.success(f"다운로드 완료! 저장 폴더: {output_dir}")

        except Exception as e:
            st.error(f"영상 정보 불러오기 오류: {str(e)}")
