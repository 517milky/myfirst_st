import streamlit as st
from yt_dlp import YoutubeDL
import os
import tempfile
import shutil
import time

def get_playlist_info(url):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

def download_video(video_url, output_path, format_code):
    ydl_opts = {
        'format': format_code,
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

st.title("YouTube 재생목록 다운로드")

playlist_url = st.text_input("재생목록 링크를 입력하세요")

if playlist_url:
    col1, col2 = st.columns(2)
    
    with col1:
        show_list = st.button("📄 목록 미리 확인")
    with col2:
        quick_download = st.button("⬇️ 바로 다운로드")
    
    if show_list:
        st.warning("재생목록 정보 로딩에 시간이 걸릴 수 있습니다. 잠시만 기다려주세요.")
        try:
            playlist_info = get_playlist_info(playlist_url)
            video_list = playlist_info.get("entries", [])
            st.success(f"총 {len(video_list)}개의 영상이 발견되었습니다.")
            
            for idx, video in enumerate(video_list):
                with st.expander(f"{idx+1}. {video['title']}"):
                    st.video(f"https://www.youtube.com/watch?v={video['id']}")
        except Exception as e:
            st.error("재생목록 정보를 불러오는 중 오류가 발생했습니다.")
    
    if quick_download:
        with st.spinner("전체 영상 다운로드 중..."):
            try:
                playlist_info = get_playlist_info(playlist_url)
                video_list = playlist_info.get("entries", [])

                with tempfile.TemporaryDirectory() as tmpdir:
                    folder_name = playlist_info.get('title', 'playlist')
                    folder_path = os.path.join(tmpdir, folder_name)
                    os.makedirs(folder_path, exist_ok=True)

                    for video in video_list:
                        video_url = f"https://www.youtube.com/watch?v={video['id']}"
                        download_video(video_url, folder_path, 'best[height<=720][ext=mp4]/best')
                    
                    final_path = os.path.join(os.getcwd(), f"{folder_name}.zip")
                    shutil.make_archive(base_name=final_path.replace('.zip', ''), format='zip', root_dir=folder_path)

                    st.success("모든 영상이 다운로드 및 압축되었습니다.")
                    with open(final_path, "rb") as f:
                        st.download_button(
                            label="압축된 재생목록 다운로드 (.zip)",
                            data=f,
                            file_name=f"{folder_name}.zip",
                            mime="application/zip"
                        )
            except Exception as e:
                st.error("다운로드 중 오류가 발생했습니다.")
