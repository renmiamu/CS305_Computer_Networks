from flask import Flask, request, jsonify
import hashlib
import json

app = Flask(__name__)

# This will act as our in-memory tracker database
TRACKER_DB = {}

@app.route("/announce", methods=["GET", "POST"])
def announce():
    """ Handle announcements from seeders. """
    # Define a structure to store announcement information of seeders
    #从announcement里面获取信息
    try:
        if request.method == "POST":
            data = request.get_json(force=True)
        else:
            data = request.args

        info_hash = data.get("info_hash")
        files = data.get("files")
        port = data.get("port")

        if isinstance(files, str):
            files = files.split(",")

        seeder_info = {
            "ip": request.remote_addr,  # 自动获取客户端IP
            "port": port,
            "files": files
        }
        print(seeder_info)

        if  info_hash not in TRACKER_DB:
            TRACKER_DB[info_hash] = [seeder_info]
        else:
            existing_seeder=TRACKER_DB[info_hash]
            flag=True
            for seeder_info in TRACKER_DB[info_hash]:
                if seeder_info["ip"]== existing_seeder[info_hash]["ip"] and seeder_info["port"]== existing_seeder[info_hash]["port"]:
                   flag=False
            if flag:
                TRACKER_DB[info_hash].append(seeder_info)
        return jsonify({"status": "Seeder registered successfully"})
    except Exception as e:
        print(f"Error processing announcement: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    # Process the announcement received and store the received information

@app.route("/get_peers", methods=["GET"])
def get_seeders():
    """ Get the list of seeders for a given info_hash. """
    info_hash=request.args.get("info_hash")
    # if info_hash not in TRACKER_DB or not TRACKER_DB[info_hash]:
    #     return jsonify({
    #         "status": "success",  # 保持格式统一
    #         "info_hash": info_hash,
    #         "seeders": [],
    #         "count": 0
    #     }), 200
    seeders=TRACKER_DB[info_hash]
    response_data = {
        "status": "success",
        "info_hash": info_hash,
        "seeders": [{"ip": s["ip"], "port": s["port"],"files":s["files"]} for s in seeders],
    }
    return jsonify(response_data)

@app.route("/show_tracker_data", methods=["GET"])
def show_tracker_data():
    """ Show the entire tracker data. """
    json_result = {
        "status": "success",
        "data": TRACKER_DB
    }
    return jsonify(json_result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)