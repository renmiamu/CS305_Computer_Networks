import struct;

ip_header=input("Enter the IP header : ")
#4500003c9fa60000800100007f0000017f000001
#450001d1f93f0000ff112fd60a20a5eae00000fb
binary_header=bytes.fromhex(ip_header)
unpacked_data = struct.unpack("20B", binary_header)
ttl=unpacked_data[8]
ip_from_1=str(unpacked_data[-8])
ip_from_2=str(unpacked_data[-7])
ip_from_3=str(unpacked_data[-6])
ip_from_4=str(unpacked_data[-5])
ip_to_1=str(unpacked_data[-4])
ip_to_2=str(unpacked_data[-3])
ip_to_3=str(unpacked_data[-2])
ip_to_4=str(unpacked_data[-1])
print("ttl:",ttl)
print("source address:"+ip_from_1+"."+ip_from_2+"."+ip_from_3+"."+ip_from_4)
print("destination address:"+ip_to_1+"."+ip_to_2+"."+ip_to_3+"."+ip_to_4)

