ip_address = input("Enter ip address: ")
subnet_mask = input("Enter subnet mask: ")

ip_address_split = ip_address.split(".")
subnet_mask_split = subnet_mask.split(".")

flag_ip = True
flag_subnet = True

for i in ip_address_split:
    i=int(i)
    if i > 255 or i < 0:
        print("IP Address Illegal")
        flag_ip = False
        break

for i in subnet_mask_split:
    i=int(i)
    if i > 255 or i < 0:
        print("Subnet Mask Illegal")
        flag_subnet = False
        break

str_subnet=""
for i in subnet_mask_split:
    str_subnet+=str(bin(int(i)))[2:].zfill(8)

if "01" in str_subnet:
    print("Subnet Mask Illegal")
    flag_subnet = False


network=[0,0,0,0]
host_id=[0,0,0,0]
if flag_ip and flag_subnet:
    for i in range(4):
        network[i] = str(int(ip_address_split[i]) & int(subnet_mask_split[i]))
        subnet_mask_split[i]=str(~int(subnet_mask_split[i]))
    print(network[0]+"."+network[1]+"."+network[2]+"."+network[3])
    for i in range(4):
        host_id[i] = str(int(ip_address_split[i]) & int(subnet_mask_split[i]))
    if host_id[0]!="0":
        print(host_id[0]+"."+host_id[1]+"."+host_id[2]+"."+host_id[3])
    elif host_id[1]!="0":
        print(host_id[1]+"."+host_id[2]+"."+host_id[3])
    elif host_id[2]!="0":
        print(host_id[2]+"."+host_id[3])
    else:
        print(host_id[3])