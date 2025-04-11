import os

mime_type={".png":"image/png",
           ".js":"application/javascript",
           ".css":"text/css",
           ".rar":"application/x-rar-compressed",
           ".mp4":"video/mp4",
           ".txt":"text/plain",
           ".jpg":"image/jpeg",
           ".MP3":"audio/mp3"}
directory_path=input("Enter the directory path: ")

for root, dirs, files in os.walk(directory_path):
    for file in files:
        root, ext = os.path.splitext(file)
        print(root+ext+"  "+mime_type[ext])