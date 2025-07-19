from pytube import YouTube

url = "https://www.youtube.com/shorts/eycVVvODZhU"  # 예: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
yt = YouTube(url)
print(yt.title)
