import os
import struct
import binascii
import socket
import threading
import datetime

from time import time, sleep
from json import load, loads, dumps
from enum import Enum

from src.utils import *
from src.db_worker import *
from src.db_connect import CONN
from src.logs.log_config import logger


class ION:

    BASE_PATH = 'tracker_receiver/src/protocols/ION/'
    NAME = 'ION'
    TRACKERS = set()

    def __init__(self, sock, addr, model):
        self.sock = sock
        self.addr = addr
        self.imei = ''


    def start(self):
        ION.TRACKERS.add(self)
        self.db = pymysql.connect(**CONN)

        self.assign = get_configuration(self.NAME, self.imei)
        self.ign_v = get_ignition_v(self.imei)

        self.stop = False
        self.data = {}
        self.command_response = {}

        try:
            self.handle_packet()
        except Exception as e:
            self.close()
            raise e


    def close(self):
        ION.TRACKERS.remove(self)
        self.sock.close()
        self.db.close()
        self.stop = True
        logger.info(f'ION {self.imei} отключен [{self.addr[0]}:{self.addr[1]}]')


    def handle_packet(self):
        if self.stop:
            self.stop = False

        while not self.stop:
            try:
                packet = binascii.hexlify(self.sock.recv(1024))
            except Exception as e:
                self.close()
                break

            packet, packet_type = extract_ubyte(packet)
            packet, packets = extract_ubyte(packet)
            packet, self.imei = ION.parse_imei(packet)

            logger.info(f'ION {self.imei} подключен [{self.addr[0]}:{self.addr[1]}]')

            all_data = {}
            for i in range(packets):
                try:
                    packet, data = ION.parse_data(packet)
                    logger.debug(f'[ION] {self.imei} данные #{i} {data}')
                    data = self.rename_data(data)
                    logger.debug(f'[ION] {self.imei} данные после переименования: {data}')
                    data = ION.prepare_geo(data)
                    logger.debug(f'[ION] {self.imei} данные после обработки: {data}')
                except Exception as e:
                    logger.error(f'[ION] {self.imei} ошибка парсинга\n{e}\nПакет{packet}')
                else:
                    all_data.append(data)

            count = insert_geo(all_data)
            logger.info(f'ION {self.imei} принято {count}/{packets} записей')
            if packet_type==0x82 or packet_type==0x83:
                self.sock.send(b'0')


    @staticmethod
    def parse_imei(packet):
        packet, imei = extract_str(packet, 7)
        part_1 = int(f'0x{imei[:3]}', 16)
        part_2 = int(f'0x{imei[3:]}', 16)
        imei = f'{part_1}{part_2}'
        return packet, imei


    @staticmethod
    def parse_data(packet):
        packet, lan = extract_int(packet)/100000
        packet, lon = extract_int(packet)/100000
        packet, speed = extract_ubyte(packet)*1.852
        packet, direction = extract_ubyte(packet)*2
        packet, sat_num = extract_ubyte(packet)
        packet, HDOP = extract_ubyte(packet)/10
        packet, status = extract_ubyte(packet)

        packet, AIN = extract_ushort(packet)
        packet, VOLTAGE = extract_ushort(packet)
        packet, TEMP = extract_ubyte(packet)

        packet, day = extract_ubyte(packet)
        packet, month = extract_ubyte(packet)
        packet, year = extract_ubyte(packet)
        packet, hour = extract_ubyte(packet)
        packet, minute = extract_ubyte(packet)
        packet, second = extract_ubyte(packet)

        packet, dt = datetime.datetime(
            day=day, month=month, year=year,
            hour=hour, minute=minute, second=second
            )

        exclude = ['packet','status','day','month','year','hour','minute','second']
        data = {key:value for key, value in locals().items() if key not in exclude or key!='exclude'}
        return packet, data


    @staticmethod
    def prepare_geo(data):
        ex_keys = ('lat', 'lon', 'speed', 'direction', 'dt')
        reserve = {k:v for k,v in data.items() if k not in ex_keys}
        reserve = str(reserve)[1:-1].replace("'", '"').replace(' ', '')

        geo = {
            'imei': data['imei'],
            'lat': float('{:.6f}'.format(data['lat'])),
            'lon': float('{:.6f}'.format(data['lon'])),
            'datetime': data['dt'],
            'type': 0,
            'speed': data['speed'],
            'direction': data['direction'],
            'bat': 0,
            'fuel': 0,
            'ignition': data.get('ignition', 0),
            'sensor': data.get('sensor', 0),
            'reserve': reserve,
            'ts': datetime.datetime.utcfromtimestamp(int(time()))
        }

        return geo


    def rename_data(self, data):
        new_data = {}
        for key, value in data.items():
            if key in self.assign.keys():
                ikey = self.assign[key]
                if '*' in ikey:
                    spl = ikey.split('*')
                    ikey, k = spl[0], spl[1]
                    new_val = round(value*float(k), 2)

                    if ikey=='temp' or ikey=='temp2':
                        new_val = round(new_val, 1)

                    new_data[ikey] = new_val
                    continue

                new_data[ikey] = value
                continue

            new_data[key] = value

        return new_data