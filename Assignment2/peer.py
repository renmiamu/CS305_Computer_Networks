import math
import socket, threading, argparse, os, json, time, struct, random, zlib

# --- Constants ---
SEGMENT_SIZE = 512
ACK_TIMEOUT = 0.5
DROP_PROBABILITY = 0.05
ERROR_PROBABILITY = 0.05
WINDOW_SIZE = 4 # Slipping window size for sending segments
MAX_RETRIES = 50 # The maximum times of resending a packet
RECV_DIR = 'files' # Folder to store peers' received files
COST_UPDATE_INTERVAL = 60 # the updating interval of link cost between peers

# --- Global State ---
reassembly_buffers = {} # Store received segments
reassembly_expected = {} # Record the number of segments to be received
unacked_segments = {} # Record segments that have not been acked
retry_counts = {} # Record the times of resending a segment
lock = threading.Lock()
distance_vector = {} # Store the local DV
link_costs = {} # Store a peer's link costs with neighbours
neighbor_dv_tables = {} # Store DVs of neighbours
dv_lock = threading.Lock()

# --- Packet Helpers ---
def make_packet(pkt_type, seq, total, src, dst, ttl, payload):
    checksum = zlib.crc32(payload) & 0xffffffff
    header = {
        "type": pkt_type,
        "seq": seq,
        "total": total,
        "src": src,
        "dst": dst,
        "ttl": ttl,
        "checksum": checksum
    }
    header_bytes = json.dumps(header).encode()
    return struct.pack("!I", len(header_bytes)) + header_bytes + payload

def parse_packet(data):
    header_len = struct.unpack("!I", data[:4])[0]
    header = json.loads(data[4:4+header_len].decode())
    payload = data[4+header_len:]
    return header, payload

def load_config():
    with open("config.json") as f:
        return json.load(f)

# --- Listener and Packet Receiver (TODO)---
#peer_id: 当前节点的标识符
#peers: 用于存储节点信息的字典
def listen(peer_id, ip, port, peers):
    # TODO: Create a UDP socket, bind it, and listen for incoming packets
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (ip, port)
    udp_socket.bind(server_address)
    print(f"节点 {peer_id} 正在监听 {ip}:{port}")
    #接收数据
    while True:
        data, address = udp_socket.recvfrom(1024)
        message = json.loads(data.decode('utf-8'))
        sender_id = message.get('peer_id')
        if (sender_id not in peers and sender_id != peer_id):
            peers[sender_id] =[ip, port]

def handle_packet(data, addr, peer_id, peers):
    header, payload = parse_packet(data)

    # Simulating packet drop
    if random.random() < DROP_PROBABILITY:
        return
    # Simulating packet corruption
    if header["type"] == "DATA" and random.random() < ERROR_PROBABILITY and len(payload) > 0:
        idx = random.randint(0, len(payload) - 1)
        corrupted = (payload[idx] + 1) % 256
        payload = payload[:idx] + bytes([corrupted]) + payload[idx+1:]

    # TODO: Parse packet and handle DATA, ACK, DV types
    # TODO: If packet is not for this peer, forward it to next hop

    # You can refer to the following logic:
        # First,
            ## Check the validity of the received packets based on checksum
            ## Drop the packets if TTL is reached
    if header["checksum"] != zlib.crc32(payload) & 0xffffffff:
        print("checksum error")
        return

    if header["ttl"]<=0:
        print("ttl reached")
        return

    header["ttl"]-=1

        # Second, if the packet is received correctly and peer_id is the destination, then
            ## If the packet type is DATA, record the payload and reply to the sender with an ACK
            ## If the packet type is ACK, record the ACK 
            ## If the packet type is DV, implement the handle_dv_update function to update the local DV
    if header["dst"]==peer_id:
        if header["type"]=="DATA":
            #多线程环境下对reassembly_buffers安全访问
            with lock:
                if header["src"] not in reassembly_buffers:
                    reassembly_buffers[header["src"]] = []
                reassembly_buffers[header["src"]][header["seq"]] = payload
                reassembly_expected[header["src"]]=header["total"]
            send_ack(header["src"],peer_id,header["seq"],peers)
            print(f"[{peer_id}] 已发送ACK确认seq={header['seq']}")

        if header["type"]=="ACK":
            with lock:
                if header["seq"] in unacked_segments:
                    del unacked_segments[header["seq"]]
                    print(f"[{peer_id}] 收到seq={header['seq']}的ACK确认")

        # if header["type"]=="DV":

    else:
        # 5. 需要转发的数据包
        print(f"[{peer_id}] 转发目标为{header['dst']}的数据包")
        next_hop = get_next_hop(peer_id, peers["dst"])
        if next_hop and header["ttl"]>0:
            print(f"[{peer_id}] 转发目标为{header['dst']}的数据包")
            next_hop = get_next_hop(peer_id, header["dst"])
            if next_hop and header["ttl"] > 0:
                # 构造新数据包（更新TTL后）
                new_packet = make_packet(
                    pkt_type=header["type"],
                    seq=header["seq"],
                    total=header["total"],
                    src=header["src"],
                    dst=header["dst"],
                    ttl=header["ttl"],
                    payload=payload
                )
                # 转发到下一跳
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(new_packet, next_hop)
                sock.close()
                print(f"[{peer_id}] 已转发数据包到 {next_hop}")
            else:
                print(f"[{peer_id}] 无可用路由或TTL不足，丢弃数据包")





        # If the packet is received correctly and peer_id is not the destination, then
            ## Forward the packet to the next hop or drop the packet if TTL is reached

# --- File Transmission (TODO)---
def send_file(peer_id, dst_id, filename, peers):
    # TODO: Segment the file and send using sliding window
    # TODO: Print out the information that all segments have been sent successfully
    # 读取文件内容
    with open(filename, 'rb') as f:
        file_data = f.read()
    file_size = len(file_data)
    total_segments = math.ceil(file_size / SEGMENT_SIZE)

    print(f"开始发送文件 {filename} (大小: {file_size} 字节, 共 {total_segments} 段)")


    pass

def send_segment(peer_id, dst_id, segment, seq, peers, is_retry=False, total=-1):
    # TODO: Send a segment to the next hop using the local DV
    next_hop=get_next_hop(peer_id, peers[peer_id])
    packet = make_packet(
        pkt_type="DATA",
        seq=seq,
        total=total,
        src=peer_id,
        dst=dst_id,
        ttl=10,
        payload=segment
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, next_hop)
    sock.close()

    if not is_retry:
        with lock:
            unacked_segments[seq] = (time.time(), packet)
            retry_counts[seq] = 0
    else:
        retry_counts[seq]+=1


    pass

# --- Segment Retransmission ---
def ack_timekeeping(peer_id, dst_id, segment, seq, peers, total):
    # TODO: Create a timer to calculate the time to receive a segment's ACK
    # TODO: Resend the segment if its ACK is not received before timeout.
    pass

# --- Segment Reception, Reassembly and ACK ---
def store_segment(peer_id, header, payload):
    # TODO: Store the received segment and trigger reassembly if complete
    pass

def reassemble_file(peer_id):
    # TODO: Write reassembled segments into a file, namely 'received_file.txt', and store it in the peer's folder.
    pass

def send_ack(dst, src, seq, peers):
    # TODO: Send ACK back to source for correctly-received segment
    ack_packet=make_packet(
        pkt_type="ACK",
        seq=seq,
        total=1,
        src=src,
        dst=dst,
        ttl=10,
        payload=b"ACK"
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(ack_packet, peers[dst])
    sock.close()

# --- Distance Vector Routing ---
def handle_dv_update(peer_id, neighbor, dv_data, peers):
    # TODO: Apply Bellman-Ford updates to update the local DV after receiving DV estimates from neighbours.
    # Then, broadcast the local DV to neighbours if it is changed.
    pass

def broadcast_dv(peer_id, peers):
    # TODO: Broadcast DV to neighbors
    pass

def routes_print(peer_id):
    # TODO: Print routes to other peers
    pass

def get_next_hop(peer_id, dst):
    # TODO: Lookup the next hop for a given destination based on the local DV

    pass

def cost_update_thread(peer_id, peers):
    while True:
        time.sleep(COST_UPDATE_INTERVAL)
        # TODO: Randomly change link costs and recompute DV
        pass

# --- Main Function ---
def main():

    # Create a new peer with the given configuration (defined in config.json)
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    args = parser.parse_args()

    peer_id = args.id
    config = load_config()
    ip, port = config["peers"][peer_id]
    peers = config["peers"]
    global link_costs
    link_costs = config["links"][peer_id]
    distance_vector[peer_id] = {peer_id: (0, peer_id)}

    print(f"[{peer_id}] Starting...")
    os.makedirs(os.path.join(RECV_DIR, peer_id), exist_ok=True)

    threading.Thread(target=listen, args=(peer_id, ip, port, peers), daemon=True).start()# Create a UDP socket and start listening
    threading.Thread(target=cost_update_thread, args=(peer_id, peers), daemon=True).start()# Update link costs periodically

    while True:
        cmd = input(f"[{peer_id}] > ")
        # Send files to other peers, e.g., "send Peer5 input.txt"
        if cmd.startswith("send"):
            _, dst, filename = cmd.strip().split()
            send_file(peer_id, dst, filename, peers)
        
        # Check the segments that has been received and non-received
        elif cmd.strip() == "check":
            if peer_id in reassembly_buffers:
                received = sorted(reassembly_buffers[peer_id].keys())
                expected = reassembly_expected.get(peer_id, max(received)+1)
                missing = [i for i in range(expected) if i not in received]
                print(f"[{peer_id}] Segments received: {received}")
                print(f"[{peer_id}] Segments missing: {missing}")
            else:
                print(f"[{peer_id}] No active transfer buffer")

        # Check the routes to other peers
        elif cmd.strip() == "routes":
            routes_print(peer_id)

if __name__ == "__main__":
    main()
