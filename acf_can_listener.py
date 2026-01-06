import traceback
import threading

from config import *
from open1722 import Open1722

# TODO parse from args
priority = -1
ifname = 'lo'
macaddr = 'aa:bb:cc:dd:ee:ff'
can_variant = AVTP_CAN_CLASSIC
can_if_name = 'vcan1'
use_udp = 0
use_tscf = 0
listener_stream_id = STREAM_ID

def acf_listener_thread():
    print('Starting acf-can listener thread..')

    while True:
        pdu = eth_socket.recv(MAX_ETH_PDU_SIZE)
        if not pdu or len(pdu) > MAX_ETH_PDU_SIZE:
            print("Error reading AVTP frames")
            continue            

        # pack all the read frames into an avtp frame
        can_frames = open1722.avtp_to_can(pdu,
                                          can_variant,
                                          use_udp,
                                          listener_stream_id)
        
        # print(bytes(can_frames))

        # send the packed frame to the vcan iface
        for frame in can_frames:
            res = can_socket.send(frame)

            if not res:
                print("Error sending CAN frames")
                continue

if __name__ == '__main__':
    try:
        open1722 = Open1722()
        eth_socket = open1722.setup_eth_socket(ifname)
        can_socket = open1722.setup_can_socket(can_if_name)
        
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
