__author__ = 'srkiyengar'

import socket
import logging
import struct
from datetime import datetime


LOG_LEVEL = logging.DEBUG

# Set up a logger with output level set to debug; Add the handler to the logger
my_logger = logging.getLogger("My_Logger")


class make_connection:

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
        else:
            self.sock = sock
        self.connection = 0

    def connect(self, host, port):
        try:
            self.sock.connect((host,port))
            self.link = 1
        except socket.timeout:
            my_logger.info("Socket time out error")
            self.link = 0

    def end_socket(self):
        #self.sock.shutdown(self.sock)
        self.sock.close()

    def send_data(self, msg):

        message_len = len(msg)
        total = 0
        while total < message_len:
            sent = self.sock.send(msg[total:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total = total + sent

    def receive_data(self,how_many):

        received_data = []
        bytes_recd = 0
        while bytes_recd < how_many:
            chunk = self.sock.recv((how_many - bytes_recd), 2048)
            if chunk == '':
                raise RuntimeError("socket connection broken")
            received_data.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(received_data)


class command_labview:

    def __init__(self, host, port=5000):

        self.my_connection = make_connection()
        self.my_connection.connect(host,port)
        self.connected = self.my_connection.link
        self.datafile = ""


    def exchange_time(self, time_str):

        l = len(time_str)
        format_str = "BB"+str(l)+"s"
        send_str = struct.pack(format_str,6,l,time_str)
        self.my_connection.send_data(send_str)
        response_header = self.my_connection.receive_data(2)
        c = ord(response_header[1])
        response_str = self.my_connection.receive_data(c)
        return response_str



    def send_unimplemented_command(self):
        some_string = "nothing"
        l = len(some_string)
        format_str = "BB"+str(l)+"s"
        end_str = struct.pack(format_str,4,l,some_string)
        self.my_connection.send_data(end_str)

    def start_collecting(self,filename):
        self.datafile = filename
        l = len(filename)
        format_str = "BB"+str(l)+"s"
        start_str = struct.pack(format_str,7,l,filename)
        self.my_connection.send_data(start_str)
        my_logger.info("Sent Command to NDI to Start Collecting for {}".format(filename))

    def stop_collecting(self):
        if self.datafile:
            l = len(self.datafile)
            format_str = "BB"+str(l)+"s"
            stop_str = struct.pack(format_str,5,l,self.datafile)
            self.my_connection.send_data(stop_str)
            my_logger.info("Sent Command to NDI to Stop Collecting for {}".format(self.datafile))

    def stop__labview_recording(self):
        filename = "dummy"
        l = len(filename)
        format_str = "BB"+str(l)+"s"
        end_str = struct.pack(format_str,6,l,filename)
        self.my_connection.send_data(end_str)
        self.my_connection.send_data(end_str)       #the labivew seems to requires two for while loop shutdonw - needs debugging

    def destroy(self):
        self.my_connection.end_socket()

class sync_time:
    def __init__(self, labview_connector, total_tries):
        self.time_diff = []
        self.labview_time = []
        self.grabber_after_time = []
        self.attempts = total_tries
        self.labview_connector = labview_connector
        self.clock_difference = 0
        self.transit_time = 0
        self.transit_error = 0

    def get_time_diff(self):
        for m in range(1,self.attempts,1):
            before_time = datetime.now()
            before_time_str = before_time.strftime("%Y-%m-%d-%H-%M-%S-%f")
            response_str = self.labview_connector.exchange_time(before_time_str)
            after_time = datetime.now()
            after_time_str = after_time.strftime("%Y-%m-%d-%H-%M-%S-%f")
            my_logger.info("Before Laptop Time: {}".format(before_time_str))
            my_logger.info("Desktop Response: {}".format(response_str))
            my_logger.info("After Laptop Time: {}".format(after_time_str))

            laptop_ts, labview_ts = response_str.split("S")
            labview1, labview2 = labview_ts.split(".")
            labview_ts = labview1 +"-" + labview2
            desktop_time = datetime.strptime(labview_ts,"%Y-%m-%d-%H-%M-%S-%f")
            self.labview_time.append(desktop_time)
            self.grabber_after_time.append(after_time)
            transit_time = after_time - before_time
            transit_time_ms = (1000000*transit_time.seconds)+(transit_time.microseconds)
            self.time_diff.append(transit_time_ms)

            if transit_time_ms < 2000:
                if desktop_time > after_time:
                    delta = desktop_time - after_time
                    difference = (1000000*delta.seconds)+(delta.microseconds)
                else:
                    delta = after_time - desktop_time
                    difference = -((1000000*delta.seconds)+(delta.microseconds))
                my_logger.info("--->Clock Difference (+ive means Desktop is ahead): {}".format(difference))
                self.clock_difference = difference
                self.transit_error = 0
            else:
                self.transit_error = 1

            my_logger.info("Attempt # {}".format(m))

            my_logger.info("--->Transit Time in ms: {}".format((transit_time_ms/1000)))
            self.transit_time = transit_time_ms




