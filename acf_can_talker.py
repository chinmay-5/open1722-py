import ctypes
import traceback
import threading
import os
import socket

# config
LIB_PATH = '/home/Open1722/build/src/libopen1722.so'
ETH_P_TSN = 0x22F0
MAX_ETH_PDU_SIZE = 1500
STREAM_ID = 0xAABBCCDDEEFF0001

# enums
AVTP_CAN_CLASSIC = 0
AVTP_CAN_FD = 1

# structs
class SockAddr_ll(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_uint8 * 20) # 20 bytes
    ]
   
class SockAddr(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_uint8 * 16) # 16 bytes
    ]

class Can_Frame(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_uint8 * 16) # 16 bytes
    ]

class CanFD_Frame(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_uint8 * 72) # 72 bytes
    ]

class Frame_t(ctypes.Union):
    _fields_ = [
        ("cc", Can_Frame),
        ("fd", CanFD_Frame)
    ]

# TODO parse from args
priority = -1
ifname = 'lo'
macaddr = 'aa:bb:cc:dd:ee:ff'
can_variant = AVTP_CAN_CLASSIC
num_acf_msgs = 1
can_if_name = 'vcan0'
use_udp = 0
use_tscf = 0
talker_stream_id = STREAM_ID

# glob vars
# fd = 0
# res = 0
# can_socket = 0

# sk_ll_addr = SockAddr_ll()

pdu = (ctypes.c_uint8 * MAX_ETH_PDU_SIZE)()
pdu_length = 0
can_frames = (Frame_t * num_acf_msgs)()

# load the lib
lib = ctypes.CDLL(LIB_PATH)

# define function signatures
lib.create_talker_socket.argtypes = [ctypes.c_int]
lib.create_talker_socket.restype = ctypes.c_int

lib.setup_socket_address.argtypes = [ctypes.c_int, 
                                     ctypes.c_char_p, 
                                     ctypes.POINTER(ctypes.c_uint8),
                                     ctypes.c_int,
                                     ctypes.POINTER(SockAddr_ll)
                                    ]
lib.setup_socket_address.restype = ctypes.c_int

lib.setup_can_socket.argtypes = [ctypes.c_char_p,
                                 ctypes.c_int
                                ]
lib.setup_can_socket.restype = ctypes.c_int

lib.can_to_avtp.argtypes = [ctypes.POINTER(Frame_t),
                            ctypes.c_int,
                            ctypes.POINTER(ctypes.c_uint8),
                            ctypes.c_int,
                            ctypes.c_int,
                            ctypes.c_uint64,
                            ctypes.c_uint8,
                            ctypes.c_uint8,
                            ctypes.c_uint32
                            ]
lib.can_to_avtp.restype = ctypes.c_int


def parse_mac(mac_addr):
    try:
        assert type(mac_addr) == str
        s = mac_addr.split(':')
        assert len(s) == 6
        return (ctypes.c_uint8 * 6)(*[int(x, 16) for x in s])
    except Exception:
        print("Invalid MAC address, format should be aa:bb:cc:dd:ee:ff")
        exit(1)

def acf_talker_thread():
    print('Starting acf-can talker thread..')
    cf_seq_num = 0
    udp_seq_num = 0

    while True:
        for i in range(num_acf_msgs):
            if can_variant == AVTP_CAN_FD :
                # res = os.read(can_socket, 72)
                res = can_socket.recv(72)
            else:
                # res = os.read(can_socket, 16)
                res = can_socket.recv(16)
        
            if not res:
                print("Error reading CAN frames")
                continue
            else:
                can_frames[i].cc = Can_Frame.from_buffer_copy(res)

        # pack all the read frames into an avtp frame
        pdu_length = lib.can_to_avtp(can_frames,
                                     can_variant,
                                     pdu,
                                     use_udp,
                                     use_tscf,
                                     talker_stream_id,
                                     num_acf_msgs,
                                     cf_seq_num,
                                     udp_seq_num)
        
        # print(bytes(pdu[:pdu_length]))
        cf_seq_num += 1
        udp_seq_num += 1

        # send the packed frame on an ethernet iface
        eth_socket.sendto(bytes(pdu)[:pdu_length],
                          (ifname, ETH_P_TSN, 0, 0, bytes(parse_mac(macaddr))))

        # print(bytes(dest_addr.contents))
        # sock.sendto(bytes(pdu), (sk_ll_addr))

if __name__ == '__main__':
    try:
        print('Setting up sockets..')
        # setup the socket for sending avtp frames

        # fd = lib.create_talker_socket(priority)
        # assert fd >= 0

        # res = lib.setup_socket_address(fd, 
        #                             ifname, 
        #                             parse_mac(macaddr),
        #                             ETH_P_TSN,
        #                             ctypes.pointer(sk_ll_addr))
        # dest_addr = ctypes.cast(ctypes.pointer(sk_ll_addr),
        #                         ctypes.POINTER(SockAddr))
        # assert res >= 0

        eth_socket = socket.socket(socket.AF_PACKET, # family
                            socket.SOCK_DGRAM, # type
                            socket.htons(ETH_P_TSN)) # protocol
        eth_socket.bind((ifname, 0))

        # open can socket to listen generated can frames
        # can_socket = lib.setup_can_socket(can_if_name,
                                        #   can_variant)
        # assert can_socket >= 0
        
        can_socket = socket.socket(socket.AF_CAN,
                                   socket.SOCK_RAW,
                                   socket.CAN_RAW)
        can_socket.bind((can_if_name,))
        
        # start the acf-can talker thread
        talker_thread = threading.Thread(target= acf_talker_thread)
        talker_thread.start()
        talker_thread.join()

    except KeyboardInterrupt as e:
        print('Interrupted..')

    except Exception as e:
        print(f'Exception: {traceback.format_exception(e)}')
    
    finally:
        if eth_socket:
            eth_socket.close()
        if can_socket:
            can_socket.close()
        
        # if fd >=0:
            # print('Closing socket..')
            # os.close(fd)