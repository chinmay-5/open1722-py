import traceback
import threading

from config import *
from open1722 import Open1722
from utils import parse_mac

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

def acf_talker_thread():
    print('Starting acf-can talker thread..')
    cf_seq_num = 0
    udp_seq_num = 0

    while True:
        can_frames = []

        for i in range(num_acf_msgs):
            if can_variant == AVTP_CAN_FD :
                res = can_socket.recv(72)
            else:
                res = can_socket.recv(16)
        
            if not res:
                print("Error reading CAN frames")
                continue
            else:
                can_frames.append(res)

        # pack all the read frames into an avtp frame
        pdu = open1722.can_to_avtp(can_frames,
                                   can_variant,
                                   use_udp,
                                   use_tscf,
                                   talker_stream_id,
                                   num_acf_msgs)
        cf_seq_num += 1
        udp_seq_num += 1

        # send the packed frame on an ethernet iface
        eth_socket.sendto(pdu, (ifname, ETH_P_TSN, 0, 0, bytes(parse_mac(macaddr))))

if __name__ == '__main__':
    try:
        open1722 = Open1722(num_acf_msgs)
        eth_socket = open1722.setup_eth_socket(ifname)
        can_socket = open1722.setup_can_socket(can_if_name)

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
