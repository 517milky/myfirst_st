# app.py
import streamlit as st
from pytube import YouTube
import os
import uuid
import subprocess

def clean_url(url):
    if url.startswith("https://wwwyoutube.streamlit.app"):
        url = url.replace("https://wwwyoutube.streamlit.app", "https://www.youtube.com")
    elif url.startswith("https://wwwyoutube"):
        url = url.replace("wwwyoutube", "www.youtube")
    return url

def merge_video_audio(video_path, audio_path, output_path):
    command = [
        'ffmpeg',
        '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def download_stream(youtube_obj, only_audio=False, high_quality=False):
    if only_audio:
        audio_stream = youtube_obj.streams.filter(only_audio=True).order_by("abr").desc().first()
        return audio_stream.download()
    if high_quality:
        video_stream = youtube_obj.streams.filter(progressive=False, file_extension="mp4").order_by("resolution").desc().first()
        audio_stream = youtube_obj.streams.filter(only_audio=True).order_by("abr").desc().first()
        if video_stream and audio_stream:
            st.info("⏳ 고화질 영상 및 오디오 다운로드 중입니다. 시간이 오래 걸릴 수 있습니다.")
            video_path = video_stream.download(filename_prefix="video_")
            audio_path = audio_stream.download(filename_prefix="audio_")
            output_path = f"merged_{uuid.uuid4()}.mp4"
            merge_video_audio(video_path, audio_path, output_path)
            os.remove(video_path)
            os.remove(audio_path)
            return output_path
        else:
            raise Exception("고화질 영상 또는 오디오 스트림을 찾을 수 없습니다.")
    else:
        # progressive 스트림에서 최고 화질(360p 이하)
        stream = youtube_obj.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
        return stream.download()

def format_bytes(size):
    power = 2**10
    n = 0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    while size > power and n < len(units)-1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def get_available_formats(youtube_obj):
    formats = []
    # progressive 스트림 (영상+오디오 같이 있음) - 보통 360p 이하
    prog_streams = youtube_obj.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc()
    for s in prog_streams:
        filesize = s.filesize or s.filesize_approx or 0
        filesize_str = format_bytes(filesize) if filesize > 0 else "알 수 없음"
        label = f"{s.resolution} (영상+오디오) - {filesize_str}"
        formats.append(("prog_" + s.itag, label, s.itag))

    # 영상-only 스트림 (고화질)
    video_only_streams = youtube_obj.streams.filter(progressive=False, file_extension="mp4", only_video=True).order_by("resolution").desc()
    for s in video_only_streams:
        filesize = s.filesize or s.filesize_approx or 0
        filesize_str = format_bytes(filesize) if filesize > 0 else "알 수 없음"
        label = f"{s.resolution} (영상 전용) - {filesize_str}"
        formats.append(("video_" + s.itag, label, s.itag))

    # 오디오-only 스트림
    audio_streams = youtube_obj.streams.filter(only_audio=True).order_by("abr").desc()
    for s in audio_streams:
        filesize = s.filesize or s.filesize_approx or 0
        filesize_str = format_bytes(filesize) if filesize > 0 else "알 수 없음"
        label = f"{s.abr} kbps (오디오 전용) - {filesize_str}"
        formats.append(("audio_" + s.itag, label, s.itag))

    return formats

st.set_page_config(page_title="YouTube 다운로더", layout="centered")
st.title("📥 YouTube 영상 다운로드")

url_input = st.text_input("🔗 YouTube 링크를 입력하세요:")

if url_input:
    url = clean_url(url_input)
    try:
        yt = YouTube(url)
        st.video(url)

        st.subheader("🎬 영상 정보")
        st.image(yt.thumbnail_url)
        st.write(f"**제목:** {yt.title}")
        st.write(f"**길이:** {yt.length}초")
        st.write(f"**채널:** {yt.author}")

        st.subheader("⬇️ 다운로드 옵션")

        formats = get_available_formats(yt)

        # 화질 선택박스 (progressive + video-only + audio-only 모두 나열)
        option_labels = [f[1] for f in formats]
        selected_index = st.selectbox("다운로드할 화질/형식을 선택하세요:", range(len(option_labels)), format_func=lambda x: option_labels[x])

        selected_tag_prefix, selected_label, selected_itag = formats[selected_index]

        # 고화질 영상+오디오 별도 처리
        if st.button("💎 고화질 영상+오디오 다운로드 (별도 합침)"):
            try:
                video_stream = yt.streams.get_by_itag(selected_itag)
                if not video_stream or video_stream.is_progressive:
                    st.error("고화질 영상-only 스트림을 선택해주세요.")
                else:
                    audio_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
                    if not audio_stream:
                        st.error("오디오 스트림을 찾을 수 없습니다.")
                    else:
                        st.info("⏳ 고화질 영상 및 오디오 다운로드 중입니다. 시간이 오래 걸릴 수 있습니다.")
                        video_path = video_stream.download(filename_prefix="video_")
                        audio_path = audio_stream.download(filename_prefix="audio_")
                        output_path = f"merged_{uuid.uuid4()}.mp4"
                        merge_video_audio(video_path, audio_path, output_path)
                        os.remove(video_path)
                        os.remove(audio_path)
                        st.success("✅ 다운로드 완료!")
                        with open(output_path, "rb") as f:
                            st.download_button("📥 영상+오디오 합친 파일 다운로드", f, file_name="merged_video.mp4")
                        os.remove(output_path)
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")

        else:
            if st.button("🎞️ 선택한 화질/형식 다운로드"):
                try:
                    stream = yt.streams.get_by_itag(selected_itag)
                    if not stream:
                        st.error("선택한 스트림을 찾을 수 없습니다.")
                    else:
                        st.info("⏳ 다운로드 중입니다...")
                        filepath = stream.download()
                        st.success("✅ 다운로드 완료!")
                        with open(filepath, "rb") as f:
                            st.download_button("📥 다운로드", f, file_name=os.path.basename(filepath))
                        os.remove(filepath)
                except Exception as e:
                    st.error(f"❌ 오류 발생: {str(e)}")

    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
else:
    st.info("다운로드할 YouTube 영상 또는 재생목록 URL을 입력하세요.")
