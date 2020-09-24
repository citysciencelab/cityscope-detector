import socket

class UDPsender:

    def __init__(self, addr="127.0.0.1", port=31337):
        self.dest_addr = addr
        self.dest_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def sendMsg(self, payload):
        try:
            self.sock.sendto(str(payload).encode("utf-8"), (self.dest_addr, self.dest_port))
        except Exception as e:
            print(e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sock.close()

class UDPreceiver:
    lastMsg = ""

    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", self.port))
        #self.sock.setblocking(0)
        self.sock.settimeout(1)

    def getMsg(self):
        try:
            data, addr = self.sock.recvfrom(32768)
            if data:
                self.lastMsg = data.decode("utf-8")
                #print(data)
        except socket.error as e:
            print(e)
        finally:
            return self.lastMsg
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sock.close()