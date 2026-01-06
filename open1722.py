import ctypes
import socket

from config import *
from structs import SockAddr_ll, Frame_t, Can_Frame

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

lib.avtp_to_can.argtypes = [ctypes.POINTER(ctypes.c_uint8),
                            ctypes.POINTER(Frame_t),
                            ctypes.c_int,
                            ctypes.c_int,
                            ctypes.c_uint64,
                            ctypes.POINTER(ctypes.c_uint8),
                            ctypes.POINTER(ctypes.c_uint32)
                            ]
lib.can_to_avtp.restype = ctypes.c_int

class Open1722:
    def __init__(self, num_acf_msgs = MAX_CAN_FRAMES_IN_ACF):
        self.pdu = (ctypes.c_uint8 * MAX_ETH_PDU_SIZE)()
        self.can_frames = (Frame_t * num_acf_msgs)()
        self.cf_seq_num = ctypes.c_uint8(0)
        self.udp_seq_num = ctypes.c_uint32(0)
        self.exp_cf_seqnum = ctypes.c_uint8(0)
        self.exp_udp_seqnum = ctypes.c_uint32(0)

    @staticmethod
    def setup_eth_socket(ifname: str):
        print(f'Setting up {ifname} socket..')
        # setup the socket for sending avtp frames
        # SOCK_RAW -> frame packed by user
        # SOCK_DGRAM -> frame packed by kernel
        eth_socket = socket.socket(socket.AF_PACKET, # family
                                   socket.SOCK_DGRAM, # type
                                   socket.htons(ETH_P_TSN)) # protocol
        eth_socket.bind((ifname, 0))

        return eth_socket

    @staticmethod
    def setup_can_socket(can_if_name: str):
        print(f'Setting up CAN socket..')
        # open can socket to listen generated can frames
        can_socket = socket.socket(socket.AF_CAN,
                                   socket.SOCK_RAW,
                                   socket.CAN_RAW)
        can_socket.bind((can_if_name,))

        return can_socket

    def can_to_avtp(self, can_frames: list, can_variant: int, use_udp: int, use_tscf: int, talker_stream_id: int, num_acf_msgs: int):
        for i in range(len(can_frames)):
            if can_variant == AVTP_CAN_FD:
                self.can_frames[i].fd = Can_Frame.from_buffer_copy(can_frames[i])
            else:
                self.can_frames[i].cc = Can_Frame.from_buffer_copy(can_frames[i])

        pdu_length = lib.can_to_avtp(self.can_frames,
                                     can_variant,
                                     self.pdu,
                                     use_udp,
                                     use_tscf,
                                     talker_stream_id,
                                     num_acf_msgs,
                                     self.cf_seq_num,
                                     self.udp_seq_num)
        
        self.cf_seq_num.value += 1
        self.udp_seq_num.value += 1
        
        return bytes(self.pdu)[:pdu_length]
    
    def avtp_to_can(self, pdu: bytes, can_variant: int, use_udp: int, listener_stream_id: int):
        self.pdu = (ctypes.c_uint8 * len(pdu))(*pdu)

        num_can_msgs = lib.avtp_to_can(self.pdu,
                                       self.can_frames,
                                       can_variant,
                                       use_udp,
                                       listener_stream_id,
                                       ctypes.byref(self.exp_cf_seqnum),
                                       ctypes.byref(self.exp_udp_seqnum))
        self.exp_cf_seqnum.value += 1
        self.exp_udp_seqnum.value += 1

        can_frames = []
        for i in range(num_can_msgs):
            if can_variant == AVTP_CAN_FD :
                can_frames.append(self.can_frames[i].fd)
            else:
                can_frames.append(self.can_frames[i].cc)

        return can_frames
