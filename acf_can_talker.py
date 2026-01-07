import traceback
import threading
import argparse

from config import *
from open1722 import Open1722
from utils import parse_mac

def acf_talker_thread():
    print('Starting acf-can talker thread..')
    cf_seq_num = 0
    udp_seq_num = 0

    while True:
        can_frames = []

        for i in range(args.count):
            if args.fd:
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
                                   AVTP_CAN_FD if args.fd else AVTP_CAN_CLASSIC,
                                   args.udp,
                                   args.tscf,
                                   args.stream_id,
                                   args.count)
        cf_seq_num += 1
        udp_seq_num += 1

        # send the packed frame on an ethernet iface
        eth_socket.sendto(pdu, (args.ifname, ETH_P_TSN, 0, 0, bytes(args.dst_addr)))

def parse_args():
    parser = argparse.ArgumentParser(
        prog="acf_can_talker",
        description="Send CAN messages to a remote CAN bus over Ethernet using Open1722"
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

    # Destination MAC address (Ethernet)
    parser.add_argument(
        "-d", "--dst-addr",
        dest="dst_addr",
        default='aa:bb:cc:dd:ee:ff',
        type=parse_mac,
        help="Stream destination MAC address (If Ethernet)"
    )

    # Destination network address (UDP)
    parser.add_argument(
        "-n", "--dst-nw-addr",
        dest="dst_nw_addr",
        help="Stream destination network address and port (If UDP)"
    )

    # Count of CAN messages per Ethernet frame
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=1,
        help="Set count of CAN messages per Ethernet frame"
    )

    # Stream ID
    parser.add_argument(
        "--stream-id",
        type=lambda x: int(x, 0),
        default=STREAM_ID,
        help="Stream ID for talker stream"
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

        open1722 = Open1722(args.count)
        eth_socket = open1722.setup_eth_socket(args.ifname)
        can_socket = open1722.setup_can_socket(args.canif)

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
