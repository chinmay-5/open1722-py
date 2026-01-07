import traceback
import threading
import argparse

from config import *
from open1722 import Open1722

def acf_listener_thread():
    print('Starting acf-can listener thread..')

    while True:
        pdu = eth_socket.recv(MAX_ETH_PDU_SIZE)
        if not pdu or len(pdu) > MAX_ETH_PDU_SIZE:
            print("Error reading AVTP frames")
            continue            

        # pack all the read frames into an avtp frame
        can_frames = open1722.avtp_to_can(pdu,
                                          AVTP_CAN_FD if args.fd else AVTP_CAN_CLASSIC,
                                          args.udp,
                                          args.stream_id)
        
        # print(bytes(can_frames))

        # send the packed frame to the vcan iface
        for frame in can_frames:
            res = can_socket.send(frame)

            if not res:
                print("Error sending CAN frames")
                continue

def parse_args():
    parser = argparse.ArgumentParser(
        prog="acf_can_listener",
        description="Receive CAN messages from a remote CAN bus over Ethernet using Open1722"
    )

    # CAN interface
    parser.add_argument(
        "--canif",
        required=True,
        help="CAN interface"
    )

    # CAN FD flag
    parser.add_argument(
        "--fd",
        action="store_true",
        default=False,
        help="Use CAN-FD"
    )

    # Network interface (Ethernet)
    parser.add_argument(
        "-i", "--ifname",
        required=True,
        help="Network interface"
    )
    
    # Stream ID
    parser.add_argument(
        "--stream-id",
        type=lambda x: int(x, 0),
        default=STREAM_ID,
        help="Stream ID for listener stream"
    )

    # TSCF/NTSCF
    parser.add_argument(
        "-t", "--tscf",
        action="store_true",
        default=False,
        help="Use TSCF (Default: NTSCF)"
    )

    # UDP/Ethernet
    parser.add_argument(
        "-u", "--udp",
        action="store_true",
        default=False,
        help="Use UDP (Default: Ethernet)"
    )

    return parser.parse_args()

if __name__ == '__main__':
    try:
        eth_socket = None
        can_socket = None

        args = parse_args()

        open1722 = Open1722()
        eth_socket = open1722.setup_eth_socket(args.ifname)
        can_socket = open1722.setup_can_socket(args.canif)
        
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
