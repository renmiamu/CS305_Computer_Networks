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
            store_segment(peer_id, header, payload)
            send_ack(header["src"],peer_id,header["seq"],peers)
            print(f"[{peer_id}] 已发送ACK确认seq={header['seq']}")

        if header["type"]=="ACK":
            with lock:
                if header["seq"] in unacked_segments:
                    del unacked_segments[header["seq"]]
                    print(f"[{peer_id}] 收到seq={header['seq']}的ACK确认")

        # if header["type"]=="DV":
        if header["type"]=="DV":
            handle_dv_update(peer_id,header["src"], json.loads(payload), peers)

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
    segments={}
    for seq in range(total_segments):
        start = seq * SEGMENT_SIZE
        end = start + SEGMENT_SIZE
        segment_data = file_data[start:end]
        segments[seq] = segment_data

    print(f"开始发送文件 {filename} (大小: {file_size} 字节, 共 {total_segments} 段)")
    #滑动窗口传输
    base = 0  # 窗口起始序号
    next_seq = 0  # 下一个要发送的序号
    window_size = min(WINDOW_SIZE, total_segments)  # 动态窗口大小
    while base < total_segments:
        # 2.1 发送窗口内的所有段
        while next_seq < min(base+window_size,total_segments):
            send_segment(peer_id,dst_id,segments[next_seq],next_seq,peers,total=total_segments)
            print(f"[{peer_id}] 发送段 {next_seq}/{total_segments - 1} (窗口: {base}-{base + window_size - 1})")
            next_seq += 1

        #等待ack或超时
        start_time = time.time()
        while True:
            with lock:
                # 1. 确定窗口内的序列号范围
                start = base
                end = min(base + window_size, total_segments)
                seq_range = range(start, end)
                # 2. 对每个序列号进行检查
                checks = []
                for seq in seq_range:
                    # 检查该序列号是否不在未确认字典中
                    is_acked = seq not in unacked_segments
                    checks.append(is_acked)
                # 3. 判断是否全部已确认
                acked_in_window = all(checks)
            if acked_in_window:
                base += window_size
                window_size = min(WINDOW_SIZE, total_segments - base)  # 动态调整窗口
                print(f"[{peer_id}] 窗口推进至 {base}-{base + window_size - 1}")
                break

            # 超时处理
            if time.time() - start_time > ACK_TIMEOUT:
                print(f"[{peer_id}] 窗口 {base}-{base + window_size - 1} 确认超时，重传...")
                next_seq = base  # 回退到窗口起始位置重传
                break
            time.sleep(0.01)  # 避免CPU忙等待
            # 3. 传输完成
            print(f"[{peer_id}] 文件 {filename} 所有段发送完成")
            return True


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

# --- Segment Retransmission ---
def ack_timekeeping(peer_id, dst_id, segment, seq, peers, total):
    # TODO: Create a timer to calculate the time to receive a segment's ACK
    # TODO: Resend the segment if its ACK is not received before timeout.
    retry_count = retry_counts[seq]
    ack_received = False
    while not ack_received and retry_count < MAX_RETRIES:
        #发送时间
        send_time=time.time()
        # 发送数据段（首次发送或重传）
        send_segment(peer_id, dst_id, segment, seq, peers, is_retry=(retry_count > 0), total=total)
        #等待ack
        while time.time() - send_time < ACK_TIMEOUT:
            with lock:
                if seq not in unacked_segments:
                    ack_received = True
                    break
            time.sleep(0.01)  # 避免忙等待
            retry_count += 1
            with lock:
                retry_counts[seq] = retry_count
                print(f"[{peer_id}] 段 {seq}/{total} 超时 (重试 {retry_count}/{MAX_RETRIES})")
    with lock:
        if seq in unacked_segments:
            del unacked_segments[seq]
    print(f"[{peer_id}] 错误: 段 {seq}/{total} 达到最大重试次数")
    return ack_received

# --- Segment Reception, Reassembly and ACK ---
def store_segment(peer_id, header, payload):
    # TODO: Store the received segment and trigger reassembly if complete
    # 多线程环境下对reassembly_buffers安全访问
    with lock:
        if header["src"] not in reassembly_buffers:
            reassembly_buffers[header["src"]] = {}
            reassembly_expected[header["src"]] = header["total"]
        reassembly_buffers[header["src"]][header["seq"]] = payload

        if len(reassembly_buffers[header["src"]])==header["total"]:
            print(f"[{peer_id}] 所有分片接收完成，准备重组文件")
            reassemble_file(peer_id)  # 触发重组


def reassemble_file(peer_id):
    # TODO: Write reassembled segments into a file, namely 'received_file.txt', and store it in the peer's folder.
    try:
        with lock:
            #检查是否存在该发送方的分片数据
            if peer_id not in reassembly_buffers:
                print(f"[重组错误] 未找到 {peer_id} 的分片缓存")
                return
            total_expected = reassembly_expected[peer_id]
            received_segments = reassembly_buffers[peer_id]
            received_count = len(received_segments)
            #验证完整性
            if received_count != total_expected:
                print(f"[重组警告] {peer_id} 的分片不完整（收到{received_count}/{total_expected}）")
                return
            #按序列号排序
            sorted_segments = sorted(received_segments.items(), key=lambda x: x[0])
            #合并数据
            file_data=b""
            for seq, data in sorted_segments:
                file_data += data
            os.makedirs(RECV_DIR, exist_ok=True)
            filename="received_file.txt"
            filepath = os.path.join(RECV_DIR, filename)
            #写入数据
            with open(filepath, "wb") as f:
                f.write(file_data)
            print(f"[重组成功] 已保存 {filepath} （大小: {len(file_data)} 字节）")
            #清理缓存
            del reassembly_buffers[peer_id]
            del reassembly_expected[peer_id]
    except Exception as e:
        print(f"[重组错误] 处理 {peer_id} 的文件时出错: {str(e)}")

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
    with dv_lock:
        #如果distancevector没有初始化
        if peer_id not in distance_vector:
            distance_vector[peer_id] = {peer_id:0}
            for n in peers:
                if n != peer_id:
                    distance_vector[peer_id][n]=float('inf')
        neighbor_dv_tables[neighbor]=dv_data

        updated=False
        for dest in distance_vector[peer_id]:
            if dest == peer_id:
                continue

            # Find minimum cost across all neighbors
            min_cost = float('inf')
            for n in link_costs[peer_id]:
                if dest in neighbor_dv_tables.get(n, {}):
                    total_cost = link_costs[peer_id][n] + neighbor_dv_tables[n][dest]
                    if total_cost < min_cost:
                        min_cost = total_cost

            # Update if found better path
            if min_cost != distance_vector[peer_id][dest]:
                distance_vector[peer_id][dest] = min_cost
                updated = True

    # Then, broadcast the local DV to neighbours if it is changed.
        if updated:
            broadcast_dv(peer_id, peers)


def broadcast_dv(peer_id, peers):
    # TODO: Broadcast DV to neighbors
    with dv_lock:
        if peer_id not in distance_vector:
            return
        for neighbor in link_costs[peer_id]:
            print(f"[{peer_id}] Broadcasting DV to {neighbor}: {distance_vector[peer_id]}")

def routes_print(peer_id):
    # TODO: Print routes to other peers
    with dv_lock:
        if peer_id not in distance_vector:
            print(f"[{peer_id}] No routing information available")
            return
        print(f"\nRouting table for {peer_id}:")
        print("{:<15} {:<10} {:<15}".format("Destination", "Cost", "Next Hop"))
        print("-" * 40)

        for dest, cost in distance_vector[peer_id].items():
            if dest==peer_id:
                continue
            next_hop = get_next_hop(peer_id, dest)
            print("{:<15} {:<10} {:<15}".format(
                dest,
                cost if cost != float('inf') else "∞",
                next_hop if next_hop else "Unreachable"
            ))


def get_next_hop(peer_id, dst):
    # TODO: Lookup the next hop for a given destination based on the local DV
    if dst == peer_id:
        return None     #local delivery

    with dv_lock:
        if peer_id not in distance_vector or dst not in distance_vector[peer_id]:
            return None

        min_cost=distance_vector[peer_id][dst]
        if min_cost == float('inf'):
            return None
        # Find which neighbor provides the minimum cost path
        for neighbor in link_costs[peer_id]:
            if (dst in neighbor_dv_tables.get(neighbor, {}) and
                link_costs[peer_id][neighbor] + neighbor_dv_tables[neighbor][dst] == min_cost):
                return neighbor
        return None

def cost_update_thread(peer_id, peers):
    while True:
        time.sleep(COST_UPDATE_INTERVAL)
        # TODO: Randomly change link costs and recompute DV
        with dv_lock:
            for neighbor in list(link_costs[peer_id]):
                if random.random()<0.3:     #30% chance to change a link cost
                    old_cost = link_costs[peer_id][neighbor]
                    new_cost = max(1, old_cost * random.uniform(0.5, 1.5))
                    link_costs[peer_id][neighbor] = new_cost
                    print(f"[{peer_id}] Updated cost to {neighbor}: {old_cost} -> {new_cost}")

            # Trigger DV recomputation
            for neighbor in neighbor_dv_tables:
                # Simulate receiving DVs from neighbors again
                handle_dv_update(peer_id, neighbor, neighbor_dv_tables[neighbor], peers)

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
