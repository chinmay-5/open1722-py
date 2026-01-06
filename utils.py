import ctypes

def parse_mac(mac_addr):
    try:
        assert type(mac_addr) == str
        s = mac_addr.split(':')
        assert len(s) == 6
        return (ctypes.c_uint8 * 6)(*[int(x, 16) for x in s])
    except Exception:
        print("Invalid MAC address, format should be aa:bb:cc:dd:ee:ff")
        exit(1)