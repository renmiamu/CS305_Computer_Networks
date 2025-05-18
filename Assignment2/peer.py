import math
import socket, threading, argparse, os, json, time, struct, random, zlib

SEGMENT_SIZE = 512
ACK_TIMEOUT = 0.5
DROP_PROBABILITY = 0.05
ERROR_PROBABILITY = 0.05
WINDOW_SIZE = 4
MAX_RETRIES = 50
RECV_DIR = 'files'
COST_UPDATE_INTERVAL = 60

reassembly_buffers = {}
reassembly_expected = {}
unacked_segments = {}
retry_counts = {}
lock = threading.Lock()
distance_vector = {}
link_costs = {}
neighbor_dv_tables = {}
dv_lock = threading.Lock()

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

def listen(peer_id, ip, port, peers):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((ip, port))
    print(f"[{peer_id}] Listening on {ip}:{port}")
    while True:
        data, addr = udp_socket.recvfrom(4096)
        try:
            _ = json.loads(data.decode('utf-8'))
        except:
            handle_packet(data, addr, peer_id, peers)

def handle_packet(data, addr, peer_id, peers):
    header, payload = parse_packet(data)
    if random.random() < DROP_PROBABILITY:
        return
    if header["type"] == "DATA" and random.random() < ERROR_PROBABILITY:
        if payload:
            idx = random.randint(0, len(payload)-1)
            payload = payload[:idx] + bytes([(payload[idx] + 1) % 256]) + payload[idx+1:]

    if header["checksum"] != zlib.crc32(payload) & 0xffffffff or header["ttl"] <= 0:
        return
    header["ttl"] -= 1

    if header["dst"] == peer_id:
        if header["type"] == "DATA":
            store_segment(peer_id, header, payload)
            send_ack(header["src"], peer_id, header["seq"], peers)
        elif header["type"] == "ACK":
            with lock:
                key = (header["src"], header["seq"])
                if key in unacked_segments:
                    del unacked_segments[key]
        elif header["type"] == "DV":
            handle_dv_update(peer_id, header["src"], json.loads(payload), peers)
    else:
        next_hop = get_next_hop(peer_id, header["dst"], peers)
        if next_hop:
            new_packet = make_packet(header["type"], header["seq"], header["total"], header["src"], header["dst"], header["ttl"], payload)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(new_packet, next_hop)
            sock.close()

def send_file(peer_id, dst_id, filename, peers):
    with open(filename, 'rb') as f:
        data = f.read()
    total_segments = math.ceil(len(data) / SEGMENT_SIZE)
    base = 0
    next_seq = 0

    while base < total_segments:
        while next_seq < min(base + WINDOW_SIZE, total_segments):
            segment = data[next_seq*SEGMENT_SIZE:(next_seq+1)*SEGMENT_SIZE]
            send_segment(peer_id, dst_id, segment, next_seq, peers, total_segments)
            threading.Thread(target=ack_timekeeping, args=(peer_id, dst_id, segment, next_seq, peers, total_segments), daemon=True).start()
            next_seq += 1

        start = time.time()
        while True:
            with lock:
                window_acked = all((dst_id, seq) not in unacked_segments for seq in range(base, min(base+WINDOW_SIZE, total_segments)))
            if window_acked:
                base += WINDOW_SIZE
                break
            if time.time() - start > ACK_TIMEOUT:
                next_seq = base
                break
            time.sleep(0.01)

def send_segment(peer_id, dst_id, segment, seq, peers, total):
    next_hop = get_next_hop(peer_id, dst_id, peers)
    if next_hop is None:
        print(f"[{peer_id}] 无法找到到 {dst_id} 的下一跳，跳过该段 {seq}")
        return
    packet = make_packet("DATA", seq, total, peer_id, dst_id, 10, segment)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, next_hop)
    sock.close()
    with lock:
        unacked_segments[(dst_id, seq)] = (time.time(), packet)
        retry_counts[(dst_id, seq)] = 0

def ack_timekeeping(peer_id, dst_id, segment, seq, peers, total):
    retries = 0
    while retries < MAX_RETRIES:
        time.sleep(ACK_TIMEOUT)
        with lock:
            if (dst_id, seq) not in unacked_segments:
                return
            retries += 1
            retry_counts[(dst_id, seq)] = retries
        send_segment(peer_id, dst_id, segment, seq, peers, total)
    with lock:
        if (dst_id, seq) in unacked_segments:
            del unacked_segments[(dst_id, seq)]

def store_segment(peer_id, header, payload):
    key = (header["src"], header["dst"])
    with lock:
        if key not in reassembly_buffers:
            reassembly_buffers[key] = {}
            reassembly_expected[key] = header["total"]
        reassembly_buffers[key][header["seq"]] = payload
        if len(reassembly_buffers[key]) == header["total"]:
            reassemble_file(peer_id, key)

def reassemble_file(peer_id, key):
    os.makedirs(os.path.join(RECV_DIR, peer_id), exist_ok=True)
    filepath = os.path.join(RECV_DIR, peer_id, f"received_from_{key[0]}.txt")
    with open(filepath, 'wb') as f:
        for i in sorted(reassembly_buffers[key]):
            f.write(reassembly_buffers[key][i])
    print(f"[{peer_id}] Reassembled file saved to {filepath}")
    del reassembly_buffers[key]
    del reassembly_expected[key]

def send_ack(dst, src, seq, peers):
    packet = make_packet("ACK", seq, 1, src, dst, 10, b"ACK")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, tuple(peers[dst]))
    sock.close()

def handle_dv_update(peer_id, neighbor, dv_data, peers):
    with dv_lock:
        if peer_id not in distance_vector:
            distance_vector[peer_id] = {peer_id: 0}
        neighbor_dv_tables[neighbor] = dv_data
        updated = False
        for dest in peers:
            if dest == peer_id:
                continue
            min_cost = float('inf')
            for n in link_costs:
                if dest in neighbor_dv_tables.get(n, {}):
                    cost = link_costs[n] + neighbor_dv_tables[n][dest]
                    if cost < min_cost:
                        min_cost = cost
            if distance_vector[peer_id].get(dest, float('inf')) != min_cost:
                distance_vector[peer_id][dest] = min_cost
                updated = True
    if updated:
        broadcast_dv(peer_id, peers)

def broadcast_dv(peer_id, peers):
    with dv_lock:
        dv_payload = json.dumps(distance_vector[peer_id]).encode()
        for neighbor in link_costs:
            packet = make_packet("DV", 0, 1, peer_id, neighbor, 10, dv_payload)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(packet, tuple(peers[neighbor]))
            sock.close()

def get_next_hop(peer_id, dst, peers):
    with dv_lock:
        if dst == peer_id:
            return tuple(peers[peer_id])
        min_cost = float('inf')
        next_hop = None
        for neighbor in link_costs:
            if dst in neighbor_dv_tables.get(neighbor, {}):
                cost = link_costs[neighbor] + neighbor_dv_tables[neighbor][dst]
                if cost < min_cost:
                    min_cost = cost
                    next_hop = neighbor
        if next_hop is None:
            print(f"[{peer_id}] 未找到到 {dst} 的路径")
        return tuple(peers[next_hop]) if next_hop else None
def cost_update_thread(peer_id, peers):
    while True:
        time.sleep(COST_UPDATE_INTERVAL)
        updated = False
        with dv_lock:
            for neighbor in link_costs:
                # 模拟链路代价的轻微波动（±1，范围限制为1~10）
                delta = random.choice([-1, 0, 1])
                new_cost = max(1, min(10, link_costs[neighbor] + delta))
                if new_cost != link_costs[neighbor]:
                    print(f"[{peer_id}] 链路代价变化：{peer_id} -> {neighbor} = {link_costs[neighbor]} -> {new_cost}")
                    link_costs[neighbor] = new_cost
                    distance_vector[peer_id][neighbor] = new_cost
                    updated = True
        if updated:
            broadcast_dv(peer_id, peers)

def routes_print(peer_id):
    with dv_lock:
        print(f"[{peer_id}] 当前路由表：")
        for dest, cost in sorted(distance_vector[peer_id].items()):
            if dest == peer_id:
                continue
            next_hop = None
            min_cost = float('inf')
            for neighbor in link_costs:
                if dest in neighbor_dv_tables.get(neighbor, {}):
                    total_cost = link_costs[neighbor] + neighbor_dv_tables[neighbor][dest]
                    if total_cost < min_cost:
                        min_cost = total_cost
                        next_hop = neighbor
            if next_hop:
                print(f"  目标: {dest}, 路径: {peer_id} -> {next_hop} -> ..., 代价: {cost}")
            else:
                print(f"  目标: {dest}, 无法到达")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    peer_id = args.id
    config = load_config()
    ip, port = config["peers"][peer_id]
    peers = config["peers"]
    global link_costs
    link_costs = config["links"][peer_id]
    distance_vector[peer_id] = {peer_id: 0}
    for neighbor in link_costs:
        distance_vector[peer_id][neighbor] = link_costs[neighbor]
    broadcast_dv(peer_id, peers)

    os.makedirs(os.path.join(RECV_DIR, peer_id), exist_ok=True)
    threading.Thread(target=listen, args=(peer_id, ip, port, peers), daemon=True).start()
    threading.Thread(target=cost_update_thread, args=(peer_id, peers), daemon=True).start()

    while True:
        cmd = input(f"[{peer_id}] > ").strip()
        if cmd.startswith("send"):
            _, dst, filename = cmd.split()
            send_file(peer_id, dst, filename, peers)
        elif cmd == "routes":
            routes_print(peer_id)
        elif cmd.strip() == "check":
            found = False
            with lock:
                for key in reassembly_buffers:
                    if key[1] == peer_id:  # key = (src, dst)
                        found = True
                        received = sorted(reassembly_buffers[key].keys())
                        expected = reassembly_expected.get(key, max(received) + 1)
                        missing = [i for i in range(expected) if i not in received]
                        print(f"[{peer_id}] Receiving from {key[0]}:")
                        print(f"  Segments received: {received}")
                        print(f"  Segments missing: {missing}")
            if not found:
                print(f"[{peer_id}] 当前无正在重组的文件")
if __name__ == "__main__":
    main()