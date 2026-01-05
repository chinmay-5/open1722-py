import ctypes
import traceback
import threading
import socket

# config
LIB_PATH = '/home/Open1722/build/src/libopen1722.so'
ETH_P_TSN = 0x22F0
MAX_ETH_PDU_SIZE = 1500
MAX_CAN_FRAMES_IN_ACF = 15
STREAM_ID = 0xAABBCCDDEEFF0001

# enums
AVTP_CAN_CLASSIC = 0
AVTP_CAN_FD = 1

# structs
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
can_if_name = 'vcan1'
use_udp = 0
use_tscf = 0
listener_stream_id = STREAM_ID

pdu = (ctypes.c_uint8 * MAX_ETH_PDU_SIZE)()
can_frames = (Frame_t * MAX_CAN_FRAMES_IN_ACF)()

# load the lib
lib = ctypes.CDLL(LIB_PATH)

# define function signatures
lib.avtp_to_can.argtypes = [ctypes.POINTER(ctypes.c_uint8),
                           ctypes.POINTER(Frame_t),
                           ctypes.c_int,
                           ctypes.c_int,
                           ctypes.c_uint64,
                           ctypes.POINTER(ctypes.c_uint8),
                           ctypes.POINTER(ctypes.c_uint32),
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

def acf_listener_thread():
    print('Starting acf-can listener thread..')
    exp_cf_seqnum = ctypes.c_uint8(0)
    exp_udp_seqnum = ctypes.c_uint32(0)

    while True:
        res = eth_socket.recv(MAX_ETH_PDU_SIZE)
        if not res or len(res) > MAX_ETH_PDU_SIZE:
            print("Error reading AVTP frames")
            continue
        else:
            pdu = (ctypes.c_uint8 * len(res))(*res)

        # pack all the read frames into an avtp frame
        num_can_msgs = lib.avtp_to_can(pdu,
                                       can_frames,
                                       can_variant,
                                       use_udp,
                                       listener_stream_id,
                                       ctypes.byref(exp_cf_seqnum),
                                       ctypes.byref(exp_udp_seqnum))
        
        # print(bytes(can_frames))
        exp_cf_seqnum.value += 1
        exp_udp_seqnum.value += 1

        # send the packed frame to the vcan iface
        for i in range(num_can_msgs):
            if can_variant == AVTP_CAN_FD :
                res = can_socket.send(can_frames[i].fd)
            else:
                res = can_socket.send(can_frames[i].cc)

            if not res:
                print("Error sending CAN frames")
                continue

if __name__ == '__main__':
    try:
        print('Setting up sockets..')
        # setup the socket for receiving avtp frames
        eth_socket = socket.socket(socket.AF_PACKET, # family
                            socket.SOCK_DGRAM, # type
                            socket.htons(ETH_P_TSN)) # protocol
        eth_socket.bind((ifname, 0))

        # open can socket to send can frames
        can_socket = socket.socket(socket.AF_CAN,
                                   socket.SOCK_RAW,
                                   socket.CAN_RAW)
        can_socket.bind((can_if_name,))
        
        # start the acf-can talker thread
        talker_thread = threading.Thread(target= acf_listener_thread)
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