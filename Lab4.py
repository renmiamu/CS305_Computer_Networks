import socket
import struct


def ip_to_str(ip_bytes):
    return ".".join(str(b) for b in ip_bytes)


def calc_udp_checksum(src_ip, dst_ip, udp_pkt):
    pseudo_header = struct.pack('!4s4sBBH',
                                socket.inet_aton(src_ip),
                                socket.inet_aton(dst_ip),
                                0,
                                socket.IPPROTO_UDP,
                                len(udp_pkt))

    udp_pkt = udp_pkt[:6] + b'\x00\x00' + udp_pkt[8:]  # 校验和字段置 0
    full_packet = pseudo_header + udp_pkt

    if len(full_packet) % 2 == 1:
        full_packet += b'\x00'

    sum1 = 0
    for i in range(0, len(full_packet), 2):
        word = (full_packet[i] << 8) + full_packet[i + 1]
        sum1 += word
    print(f"sum1 = {hex(sum1)}")

    sum2 = (sum1 & 0xffff) + (sum1 >> 16)
    print(f"sum2 = {hex(sum2)}")

    sum3 = (sum2 & 0xffff) + (sum2 >> 16)
    print(f"sum3 = {hex(sum3)}")

    checksum = ~sum3 & 0xffff
    print(f"Calculated checksum = {hex(checksum)}")
    return checksum


def process_packet_from_hex(hex_str):
    # 移除地址列和空格，拼接成纯 hex 字节
    hex_str = ''.join(line[6:].replace(' ', '') for line in hex_str.strip().splitlines())
    pkt_bytes = bytes.fromhex(hex_str)

    # IP 首部起始：Ethernet 头为14字节
    ip_start = 14
    ip_header = pkt_bytes[ip_start:ip_start + 20]

    # 解析 IP 地址
    src_ip = socket.inet_ntoa(ip_header[12:16])
    dst_ip = socket.inet_ntoa(ip_header[16:20])

    # 解析 UDP 报文
    udp_start = ip_start + 20
    udp_header = pkt_bytes[udp_start:udp_start + 8]
    udp_payload = pkt_bytes[udp_start + 8:]

    src_port, dst_port, udp_len, udp_checksum = struct.unpack('!HHHH', udp_header)
    udp_segment = pkt_bytes[udp_start:udp_start + udp_len]

    # 输出基本信息
    print(f"Source IP: {src_ip}")
    print(f"Destination IP: {dst_ip}")
    print(f"Source Port: {src_port}")
    print(f"Destination Port: {dst_port}")
    print(f"UDP Length: {udp_len}")
    print(f"UDP Header Checksum in packet: {hex(udp_checksum)}")

    # 校验和计算
    calc_sum = calc_udp_checksum(src_ip, dst_ip, udp_segment)
    print(f"Checksum match: {calc_sum == udp_checksum}")

    # 示例调用：把你输入的 hex 粘贴进去
hex_data = """
0000   01 00 5e 7f ff fa 8e cb a7 68 d9 63 08 00 45 00
0010   00 85 42 f1 40 00 01 11 ab 0c 0a 20 91 50 ef ff
0020   ff fa 08 98 08 98 00 71 6a ca 4d 2d 53 45 41 52
0030   43 48 20 2a 20 48 54 54 50 2f 31 2e 31 0d 0a 6f
0040   70 65 6e 49 64 3a 31 62 61 31 33 31 62 38 61 32
0050   34 33 36 32 38 66 0d 0a 64 65 76 69 63 65 49 64
0060   3a 63 39 38 66 35 30 0d 0a 53 65 72 76 69 63 65
0070   3a 63 6f 6d 2e 76 69 76 6f 2e 76 64 66 73 2e 64
0080   65 76 69 63 65 2e 64 69 73 63 6f 76 65 72 79 0d
0090   0a 0d 0a
"""

process_packet_from_hex(hex_data)
