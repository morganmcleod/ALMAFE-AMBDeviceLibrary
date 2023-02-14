'''
AMBDevice represents the lowest-level CAN bus device.
  Uses the provided instance of AMBConnectionItf
  It has a node address and, for SocketServer devices, a copy of the ABM index and channel
  The Monitor.vi and Control.vi methods take care of combining the node address with the provided RCA.
  Implements standard AMBSI monitor points.
'''

from AMB.AMBConnectionItf import AMBConnectionItf, AMBConnectionError
from typing import Optional

class AMBDevice():
    
    GET_AMBSI_PROTOCOL_REV  = 0x30000
    GET_AMBSI_ERRORS        = 0x30001
    GET_AMBSI_NUM_TRANS     = 0x30002
    GET_AMBSI_TEMPERATURE   = 0x30003
    GET_AMBSI_SOFTWARE_REV  = 0X30004
    
    def __init__(self, 
                 conn:AMBConnectionItf,
                 nodeAddr:int):
        '''
        :param conn: AMBConnectionNican to use
        :param nodeAddr: of device on the bus
        '''
        self.conn = conn
        self.nodeAddr = nodeAddr

    def shutdown(self):
        self.conn = None
        self.nodeAddr = None
    
    def command(self, rca, data):
        return self.conn.command(self.nodeAddr, rca, data)
        
    def monitor(self, rca):
        return self.conn.monitor(self.nodeAddr, rca)
    
    def getAmbsiProtocolRev(self):
        try:
            # we don't want to call the overridden monitor() method:
            data = AMBDevice.monitor(self, self.GET_AMBSI_PROTOCOL_REV)
            return f"{data[0]}.{data[1]}.{data[2]}"
        except AMBConnectionError:
            return "0.0.0"
            
    def getAmbsiErrors(self):
        try:
            # we don't want to call the overridden monitor() method:
            data = AMBDevice.monitor(self, self.GET_AMBSI_ERRORS)
            numErr = int.from_bytes(data[0:1], 'big')
            lastErr = int(data[3])
            return numErr, lastErr
        except AMBConnectionError:
            return 0, 0

    def getAmbsiNumTrans(self):
        try:
            # we don't want to call the overridden monitor() method:
            data = AMBDevice.monitor(self, self.GET_AMBSI_NUM_TRANS)
            numTrans = int.from_bytes(data, 'big') 
            return numTrans
        except AMBConnectionError:
            return 0

    def getAmbsiTemperature(self):
        try:
            # we don't want to call the overridden monitor() method:
            data = AMBDevice.monitor(self, self.GET_AMBSI_TEMPERATURE)
            temp = float(data[0] >> 1)
            if data[1] != 0:
                temp *= -1
                temp += -1
            if data[0] & 0x01:
                temp += 0.5
            return temp
        except AMBConnectionError:
            return 0.0
        
    def getAmbsiSoftwareRev(self):
        try:
            # we don't want to call the overridden monitor() method:
            data = AMBDevice.monitor(self, self.GET_AMBSI_SOFTWARE_REV)
            return f"{data[0]}.{data[1]}.{data[2]}"
        except AMBConnectionError:
            return "0.0.0"

        
