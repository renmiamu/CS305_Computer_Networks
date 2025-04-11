import os
import requests
import hashlib
import bencodepy
from flask import Flask, request, send_file

TRACKER_URL = "http://127.0.0.1:5001"

app = Flask(__name__)

def get_peer_folder(port):
    """ Returns the folder path for a specific peer and ensures it exists. """
    folder = "peer_" + str(port)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder

def get_info_hash(torrent_file_path):
    """Returns the info_hash and piece list of the torrent file."""
    try:
        # Read the torrent file
        with open(torrent_file_path, 'rb') as f:  # 以二进制模式打开
            data = f.read()
        # Decode the torrent data (bencode format)
        decoded_data =bencodepy.decode(data)

        # Extract the 'info' dictionary
        info_dict =decoded_data[b'info']

        # Generate the SHA1 hash of the 'info' part of the torrent
        bencode = bencodepy.encode(info_dict)
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

def get_peers_from_tracker(info_hash):
    """ Requests the tracker for a list of seeders with the given info_hash. """
    try:
        params = {'info_hash': info_hash}
        response = requests.get(f"{TRACKER_URL}/get_peers", params=params)
        if response.status_code != 200:
            print(f"Error getting peers from tracker: {response.status_code}")
        else:
            data = response.json()
            print(data)
            return data["seeders"]
    except Exception as e:
        print(f"Error retrieving peers from tracker: {e}")
        return []

def download_file(file_name, peer_ip, peer_port, local_port):
    """ Downloads a file from another peer and saves it in this peer's folder. """
    try:
       peer_folder = get_peer_folder(local_port)
       download_url = f"http://{peer_ip}:{peer_port}/download"
       params = {'files': file_name}
       response = requests.get(download_url, params=params)
       if response.status_code != 200:
           print(f"Error downloading file from {download_url}: {response.status_code}")
       else:
           folder = get_peer_folder(local_port)
           file_path = os.path.join(folder, file_name)
           with open(file_path, "wb") as f:
               f.write(response.content)
           print(f" File downloaded: {file_name}, saved to: {file_path}")
    except Exception as e:
        print(f"⚠️ Error downloading file: {e}")

def request_file(info_hash):
    """ Requests a file from other peers based on info_hash. """

    print(f"🔍 Fetching peers for info_hash: {info_hash}...")


    # First, get the list of seeders from the tracker
    seeders = get_peers_from_tracker(info_hash)

    # Second, download the shared file from one of the seeders
    ip=seeders[0]["ip"]
    port=seeders[0]["port"]
    file_name=seeders[0]["files"][0]
    download_file(file_name, ip, port, 6882)

def run_peer():
    """ Starts the requester's server. """

    port = 6882

    # First, create a folder for the requester
    peer_folder = get_peer_folder(port)
    print(f"Peer running on port {port}, sharing folder: {peer_folder}")

    print(f"Peer is running. You can now request or download the file.")

    # Second, read the torrent file and obtain its info_hash
    torrent_file_path = input("Enter the path to the torrent file for the requested file(e.g:'./peer_6882/example.txt.torrent'): ")
    # torrent_file_path = f"./peer_6882/example.txt.torrent"
    info_hash, piece_list = get_info_hash(torrent_file_path)

    # Finally, request a file based on the info_hash
    request_file(info_hash)
    
if __name__ == "__main__":
    run_peer()