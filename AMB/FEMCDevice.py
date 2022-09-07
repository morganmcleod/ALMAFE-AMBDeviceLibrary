'''
FEMCDevice represents a device connected via an FEMC module.
  It is a specialization of AMBDevice: An FEMCDevice object can be passed to any AMBDevice method.
  It has an FEMC Port number corresponding to the cartridge band or FE subsystem
  Its feMonitor and feControl methods take care of offseting the provided RCA for the cartridge band or subsystem
  Implements standard FEMC module initializatiom, monitor, and control.
'''
from AMB.AMBDevice import AMBDevice
from AMB.AMBConnectionItf import AMBConnectionItf
from typing import Optional
from datetime import datetime
import struct
from time import sleep

class FEMCDevice(AMBDevice):

    PORT_FEMC_MODULE    = 0
    PORT_BAND1          = 1
    PORT_BAND2          = 2
    PORT_BAND3          = 3
    PORT_BAND4          = 4
    PORT_BAND5          = 5
    PORT_BAND6          = 6
    PORT_BAND7          = 7
    PORT_BAND8          = 8
    PORT_BAND9          = 9
    PORT_BAND10         = 10
    PORT_POWERDIS       = 11
    PORT_IFSWITCH       = 12
    PORT_CRYOSTAT       = 13
    PORT_LPR            = 14
    PORT_FETIM          = 15
    
    MODE_OPERATIONAL       = 0
    MODE_TROUBLESHOOTING   = 1
    MODE_MAINTENANCE       = 2
    MODE_SIMULATE          = 3
    
    def __init__(self, 
                 conn:AMBConnectionItf, 
                 nodeAddr:int, 
                 femcPort:Optional[int] = PORT_FEMC_MODULE, 
                 logInfo = True):
        super(FEMCDevice, self).__init__(conn, nodeAddr)
        self.femcPort = femcPort
        self.logInfo = logInfo
        
    def initSession(self, mode:Optional[int] = MODE_TROUBLESHOOTING):
        data = self.__devMonitor(self.GET_SETUP_INFO)
        if data is None:
            self.__logMessage('GET_SETUP_INFO no data', True)
        elif data == b'\x00' or data == b'\x05':
            if self.setFeMode(mode):
                return True
        return False

    def setPort(self, femcPort:int):
        if femcPort >= self.PORT_FEMC_MODULE and femcPort <= self.PORT_FETIM:
            self.femcPort = femcPort
    
    def shutdown(self):
        super(FEMCDevice, self).shutdown()
        self.femcPort = None
       
    def getFemcVersion(self):
        data = self.__devMonitor(self.GET_VERSION_INFO)
        if data:
            return f"data[0].data[1].data[2]"
        else:
            return None

    def setFeMode(self, mode:int):
        if mode == self.MODE_OPERATIONAL:
            data = b'\x00'
        elif mode == self.MODE_TROUBLESHOOTING:
            data = b'\x01'
        elif mode == self.MODE_MAINTENANCE:
            data = b'\x02'
        elif mode == self.MODE_SIMULATE:
            data = b'\x03'
        else:
            self.__logMessage(f"setFeMode bad mode: {mode}", True)
            return False
        return self.__devCommand(self.SET_FE_MODE, data)

    def getFeMode(self):
        data = self.__devMonitor(self.GET_FE_MODE)
        if data:
            return data[0]
        else:
            return None 

    def getEsnList(self, reload = False):
        if reload:
            self.__devCommand(self.SET_READ_ESN, b'\x01')
            sleep(0.2)
        data = self.__devMonitor(self.GET_ESNS_FOUND)
        if not data:
            return None
        ret = []
        for _ in range(data[0]):
            data = self.__devMonitor(self.GET_ESNS)
            if data:
                ret.append(data)
        return ret

    def getEsnString(self):
        data = self.getEsnList()
        ret = ""
        if data:
            for esn in data:
                ret += f"{esn[0]:02X} {esn[1]:02X} {esn[2]:02X} {esn[3]:02X} {esn[4]:02X} {esn[5]:02X} {esn[6]:02X} {esn[7]:02X}\n"
        return ret
            
    def setBandPower(self, band:int, enable:bool = True):
        if band < self.PORT_BAND1 or band > self.PORT_BAND10:
            self.__logMessage(f"initBand bad band number: {band}", True)
            return False
        rca = self.SET_CART_POWER + ((band - 1) << 4)
        data = b'\x01' if enable else b'\x00'
        ret = self.__devCommand(rca, data)
        return ret
    
    def setAllBandsOff(self):
        for band in range(10):
            self.setBandPower(band + 1, False)

    def getNumBandsPowered(self):
        data = self.__devMonitor(self.GET_NUM_BANDS_POWERED)
        if data:
            return data[0]
        else:
            return None

    def monitor(self, rca:int):
        return self.__devMonitor(rca + ((self.femcPort - 1) << 12)) 
                
    def command(self, rca:int, data:bytes):
        return self.__devCommand(rca + ((self.femcPort - 1) << 12), data)
    
    @classmethod
    def unpackStatusByte(data, expectedLen):
        if not data:
            return None
        if len(data) == (expectedLen + 1):
            return data[expectedLen]
        else:
            return None
    
    @classmethod
    def unpackBool(cls, data, offset = 0):
        byte = cls.unpackU8(data, offset)
        return True if byte else False
    
    @classmethod
    def unpackU8(cls, data, offset = 0):
        if not data or len(data) < (offset + 1):
            return None
        else:
            return data[offset]
    
    @classmethod
    def unpackU16(cls, data, offset = 0):
        if not data or len(data) < (offset + 2): 
            return None
        else:
            return struct.unpack_from('!H', data, offset)[0]

    @classmethod
    def unpackU32(cls, data, offset = 0):
        if not data or len(data) < (offset + 4): 
            return None
        else:
            return struct.unpack_from('!L', data, offset)[0]

    @classmethod
    def unpackFloat(cls, data, offset = 0):
        if not data or len(data) < (offset + 4): 
            return None
        else:
            return struct.unpack_from('!f', data, offset)[0]

    @classmethod
    def packBool(cls, val, data = None, offset = 0):
        return cls.packU8(val, data, offset)
        
    @classmethod
    def packU8(cls, val, data = None, offset = 0):
        if data:
            data = bytearray(data)
        else:
            data = bytearray()
        while len(data) < (offset + 1):
            data.append(0)
        data[offset] = int(val) & 0xFF
        return bytes(data)
        
    @classmethod
    def packU16(cls, val, data = None, offset = 0):
        if data:
            data = bytearray(data)
        else:
            data = bytearray()
        while len(data) < (offset + 2):
            data.append(0)
        struct.pack_into('!H', data, offset, int(val))
        return bytes(data)

    @classmethod
    def packU32(cls, val, data = None, offset = 0):
        if data:
            data = bytearray(data)
        else:
            data = bytearray()
        while len(data) < (offset + 4):
            data.append(0)
        struct.pack_into('!L', data, offset, int(val))
        return bytes(data)

    @classmethod    
    def packFloat(cls, val, data = None, offset = 0):
        if data:
            data = bytearray(data)
        else:
            data = bytearray()
        while len(data) < (offset + 4):
            data.append(0)
        struct.pack_into('!f', data, offset, float(val))
        return bytes(data)

    def __devMonitor(self, rca:int):
        return super(FEMCDevice, self).monitor(rca)

    def __devCommand(self, rca:int, data:bytes):
        return super(FEMCDevice, self).command(rca, data)

    def __logMessage(self, msg, alwaysLog = False):
        if self.logInfo or alwaysLog:
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " FEMCDevice: " + msg)

    # RCAs used internally
    GET_AMBSI_VERSION_INFO  = 0x20000   # get the version info for the AMBSI firmware
    GET_SETUP_INFO          = 0x20001   # Initialize communications between the AMBSI and ARCOM
    GET_VERSION_INFO        = 0x20002   # Get the version info for the ARCOM Pegasus firmware
    GET_PPCOMM_TIME         = 0x20007   # For debugging:  get 8 bytes response as fast as possible
    GET_FPGA_VERSION_INFO   = 0x20008   # Get the version info for the FEMC FPGA
    GET_ESNS_FOUND          = 0x2000A   # Get the number of ESNs found in the FE
    GET_ESNS                = 0x2000B   # Get the next ESN from the FE queue
    GET_ERRORS_NUMBER       = 0x2000C   # Get the number of errors in the error queue
    GET_NEXT_ERROR          = 0x2000D   # Get the next error from the error queue
    GET_FE_MODE             = 0x2000E   # Get the FE operating mode (operational, troubleshooting, maintenance)

    # SPECIAL control points:      
    SET_FE_MODE             = 0x2100E   # Set the FE operating mode.
    SET_READ_ESN            = 0x2100F   # Tell the FEMC module to rescan the 1wire bus for ESNs.
    
    # power distribution module:
    SET_CART_POWER          = 0x1A00C
    GET_CART_POWER          = 0x0A00C
    GET_NUM_BANDS_POWERED   = 0x0A0A0