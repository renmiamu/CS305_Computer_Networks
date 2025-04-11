import os

import requests
import threading
import hashlib
import bencodepy
import shutil

from flask import Flask, request, send_file, Response

TRACKER_URL = "http://127.0.0.1:5001"
ANNOUNCE_URL = "http://127.0.0.1:5001/announce"

app = Flask(__name__)

def get_peer_folder(port):
    """ Returns the folder path for a specific peer and ensures it exists. """
    folder = "peer_" + str(port)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def create_torrent(file_name):
    """ Create a .torrent file for the given file. """

    # Check whether the file exists
    if os.path.exists(file_name)==False:
        return

    # Prepare torrent metadata ('piece length': 1024 * 1024)

    file_size = os.path.getsize(file_name)
    piece_length = 1024*1024
    pieces = b""  # 初始化空二进制字符串
    with open(file_name, "rb") as f:  # 以二进制模式打开文件
        while chunk := f.read(piece_length):  # 循环读取分片
            pieces += hashlib.sha1(chunk).digest()  # 计算哈希并拼接
    torrent_data = {
        'announce':ANNOUNCE_URL,
        'info':{
            'length':file_size,
            'name':file_name,
            'piece length':piece_length,
            'pieces': pieces
        }
    }

    # Compute the info_hash (SHA1 of the 'info' dictionary)
    info=torrent_data['info']
    bencode=bencodepy.encode(info)
    info_hash = hashlib.sha1(bencode).hexdigest()

    # Create the .torrent file
    new_file_name="./"+os.path.basename(file_name)+".torrent"
    os.makedirs(os.path.dirname(new_file_name), exist_ok=True)
    with open(new_file_name, "wb") as f:
        f.write(bencodepy.encode(torrent_data))
    return new_file_name

def get_info_hash(torrent_file_path):
    """Returns the info_hash and piece list of the torrent file."""
    try:
        # Read the torrent file

        with open(torrent_file_path, 'rb') as f:  # 以二进制模式打开
            data = f.read()
        # Decode the torrent data (bencode format)
        decoded_data = bencodepy.decode(data)

        # Extract the 'info' dictionary
        info_dict =decoded_data[b'info']

        # Generate the SHA1 hash of the 'info' part of the torrent
        bencode=bencodepy.encode(info_dict)
        info_hash = hashlib.sha1(bencode).hexdigest()

        # Extract the pieces in the torrent
        piece_list=[]
        pieces = info_dict[b'pieces']
        for i in range(0,len(pieces),20):
            piece_list.append(pieces[i:i+20].hex())

        return info_hash, piece_list
    
    except Exception as e:
        print(f"Error getting info_hash from {torrent_file_path}: {e}")
        return None, []

def announce_to_tracker(info_hash, port, shared_files):
    """ Sends an announcement to the tracker with the peer's shared files. """
    params = {
        'info_hash': info_hash,
        'port': port,
        'files': ",".join(shared_files)
    }

    # Send the announcement to the tracker
    try:
        response = requests.post(f"{TRACKER_URL}/announce", json=params)
        if response.status_code != 200:
            print(f"Error announcement from tracker: {response.status_code}")
        else:
            print("Successfully announced to tracker")

    except Exception as e:
        print(f"Failed to announce to tracker: {e}")

@app.route("/download", methods=["GET"])
def download():
    """ Serves a file to other peers upon request. """
    file_name = request.args.get("files")
    folder_path = get_peer_folder(6881)
    file_path = os.path.join(folder_path, file_name)
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            print(f" File read successfully.")
            return Response(data, mimetype="application/octet-stream")
        else:
            print(f" File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f" Error while sending file: {e}")
        return "Internal Server Error", 500


def run_peer():
    """ Starts the seeder's server and announces it to the tracker. """

    port = 6881  # Prompt user for port

    # First creat a folder for the seeder, and move the shared file into the folder.
    peer_folder = get_peer_folder(port)
    print(f"Peer running on port {port}, sharing folder: {peer_folder}")
    shared_file = input("Enter the name of the shared file: ")
    shutil.copy(shared_file, peer_folder)

    # Then, create a torrent file of the shared file, and share it with the requester directly.
    new_file=create_torrent(shared_file)
    shutil.copy(new_file, peer_folder)
    requester_folder = get_peer_folder(6882)
    shutil.copy(new_file, requester_folder)
    print(f".torrent file copied to requester folder: {requester_folder}")
    # Finally, send an announcement to register the shared files with the tracker.
    torrent_file_path="./"+peer_folder+"/"+os.path.basename(new_file)
    info_hash, piece_list = get_info_hash(torrent_file_path)
    shared_files=[]
    shared_files.append(shared_file)
    announce_to_tracker(info_hash, port, shared_files)

    # Start Flask server for file sharing
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)).start()

    print(f"Peer is running. You can now request or download the file.")

if __name__ == "__main__":
    run_peer()