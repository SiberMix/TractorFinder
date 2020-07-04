import os
import socket
import threading
import struct	
import binascii

from src.logs.log_config import logger


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class TrackerServer:
	def __init__(self, protocol):
		p = os.path.join('tracker_receiver/src/', 'servers.json')
		with open(p, 'r') as s:
			protocol = load(s)

		self.ip, self.port = protocol[protocol.NAME.lower()].split(':')
		self.sock = socket.socket()
		self.sock.bind((self.ip, int(self.port)))
		self.sock.listen(1024)

		if self.ip=='': self.ip = 'ANY'
		logger.info(f'Сервер для {protocol.NAME} запущен - [{self.ip}:{self.port}]\n')
		
		listen_th = threading.Thread(target=self.connecter)
		listen_th.start()


	def connecter(self):
		while True:
			conn, addr = self.sock.accept()
			logger.debug(f'[{protocol.NAME}] попытка подсоединиться {addr}\n')
			protocol(conn, addr)


def extract(packet, length):
	length *= 2
	return packet[length:], packet[:length]

def extract_x(packet, letter, length):
	packet, extracted = extract(packet, length)
	return packet, struct.unpack(f"!{letter}", binascii.a2b_hex(extracted))[0]

def extract_byte(packet):
	return extract_x(packet, 'b', 1)

def extract_ubyte(packet):
	return extract_x(packet, 'B', 1)

def extract_short(packet):
	return extract_x(packet, 'h', 2)

def extract_ushort(packet):
	return extract_x(packet, 'H', 2)

def extract_int(packet):
	return extract_x(packet, 'i', 4)
 
def extract_uint(packet):
	return extract_x(packet, 'I', 4)

def extract_longlong(packet):
	return extract_x(packet, 'q', 8)

def extract_float(packet):
	packet, extracted = extract_x(packet, 'f', 4)
	return packet, round(extracted, 3)

def extract_double(packet):
	packet, extracted = extract_x(packet, 'd', 8)
	return packet, round(extracted, 3)

def unpack_from_bytes(fmt, packet):
	packet = binascii.a2b_hex(packet)
	return struct.unpack(fmt, packet)



def pack(packet):
	return binascii.a2b_hex(packet)

def add_x(packet, letter, value):
	new_part = binascii.hexlify(struct.pack(f'!{letter}', value)).decode('ascii')
	packet = packet+new_part
	return packet

def add_str(packet, string):
	if not isinstance(string, bytes): 
		string = string.encode('ascii')
		
	return add_x(packet, f'{len(string)}s', string)

def add_byte(packet, value):
	return add_x(packet, 'b', value)

def add_ubyte(packet, value):
	return add_x(packet, 'B', value)

def add_short(packet, value):
	return add_x(packet, 'h', value)

def add_ushort(packet, value):
	return add_x(packet, 'H', value)

def add_int(packet, value):
	return add_x(packet, 'i', value)

def add_uint(packet, value):
	return add_x(packet, 'I', value)

def add_longlong(packet, value):
	return add_x(packet, 'q', value)

def add_float(packet, value):
	return add_x(packet, 'f', value)

def add_double(packet, value):
	return add_x(packet, 'd', value)
