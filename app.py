from pytube import YouTube

url = "여기에 네가 넣은 유튜브 링크"  # 예: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
yt = YouTube(url)
print(yt.title)
