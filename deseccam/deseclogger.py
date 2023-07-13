import logging
import os


class CentralLogger:
    def __init__(self, queue):
        self.queue = queue
        if os.path.exists('/var/log/deseccam/deseccam.log'):
            os.remove('/var/log/deseccam/deseccam.log')
        logging.basicConfig(format='%(message)s', filename='/var/log/deseccam/deseccam.log', level=logging.DEBUG)

    def start_loop(self):
        while True:
            message = self.queue.get()
            logging.info(message)