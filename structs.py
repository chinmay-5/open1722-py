import ctypes

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