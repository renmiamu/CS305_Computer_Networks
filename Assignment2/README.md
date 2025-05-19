# Assignment 2 report

### Introduction

This assignment involves building a P2P file transfer system by implementing a simplified Reliable Data Transfer (RDT) protocol and a Distance Vector (DV) routing algorithm at the application layer. Using UDP, the system ensures reliable file transmission and supports multi-hop routing between peers.

This code implements a peer-to-peer file transfer system over UDP with two main features:

- **Reliable Data Transfer (RDT):** Files are split into segments with sequence numbers, sent using a sliding window. Lost or corrupted packets are detected and retransmitted based on ACKs and timeouts.
- **Distance Vector (DV) Routing:** Peers exchange routing information to compute shortest paths. Messages are forwarded across multiple hops based on updated link costs.

The system simulates unreliable networks with packet loss and errors, and supports user commands to send files, check routes, and monitor file reception.

### Testing

#### 1. running five peers.

```shell
#take peer1 as an example
python peer.py --id Peer1
```

After entering a command, a `files/Peer_{id}` directory is created.

![image-20250519221650565](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519221650565.png)

And we could enter the command mode of each peer.

![image-20250519221815463](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519221815463.png)

![image-20250519221833155](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519221833155.png)

![image-20250519221847120](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519221847120.png)

![image-20250519221905679](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519221905679.png)

![image-20250519221917819](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519221917819.png)

#### 2. send input.txt to Peer5 in Peer1 terminal

```shell
send Peer5 input.txt
```

After the command, we could see a file named `received_from_Peer1.txt` is created under `files/Peer5` , which is exactly the same as the file `input.txt`.

![image-20250519222415397](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519222415397.png)

![image-20250519222529026](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519222529026.png)

#### 3. check command

If we input the command when no files are transmitting, we could see the following result.

![image-20250519222549784](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519222549784.png)

if we input the command when some files are transmitting, we could see results in the following

![image-20250519223055307](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519223055307.png)

#### 4. routes command

![image-20250519223246875](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519223246875.png)

![image-20250519223304044](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519223304044.png)

![image-20250519223326059](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519223326059.png)

![image-20250519223343029](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519223343029.png)

![image-20250519223358703](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519223358703.png)

link costs can randomly change like below:

![image-20250519223517655](C:\Users\86130\AppData\Roaming\Typora\typora-user-images\image-20250519223517655.png)

### Conclusion

The project demonstrates a fully working reliable UDP file transfer protocol with Distance Vector routing in a simulated peer-to-peer network.

The code can successfully send and receive files and distance vector routing tables were correctly populated.

