from multiprocessing import Process, JoinableQueue
import signal
import desecruntime
import os
import time
import desecconfig
import deseclogger
import datetime

scheduler = None
config = None
loggq = None
loggp = None


def graceful_exit(msg):
    global scheduler
    global config
    print_and_log(msg)
    scheduler.shutdownall()
    ctime = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
    print_and_log(ctime+": Server stopped.")
    if loggq is not None:
        loggq.close()
    os.system('kill -9 {0}'.format(loggp.pid))
    os._exit(0)


def dummy_signal_handler(signal, _stack_frame):
    pass


def sigterm_handler(signal, _stack_frame):
    graceful_exit("Received SIGTERM signal, exiting. (Code: 01)")


def create_logger():
    signal.signal(signal.SIGINT, dummy_signal_handler)
    signal.signal(signal.SIGTERM, dummy_signal_handler)
    deseclogger.CentralLogger(loggq).start_loop()


def sighup_handler(signal, _stack_frame):
    global scheduler
    global config
    ctime = datetime.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')
    print_and_log(ctime+": Caught SIGHUP, reloading config and restarting all processes.")
    scheduler.shutdownall()
    time.sleep(3)
    do_start()


def print_and_log(msg):
        print msg
        loggq.put(msg)


def do_start():
    global scheduler
    global config
    global loggq
    global loggp

    config = desecconfig.DesecConfigParser().getsettings()
    if loggq is None:
        loggq = JoinableQueue()
        loggp = Process(target=create_logger)
        loggp.start()

    try:
        scheduler = desecruntime.Scheduler(config, loggq)
        scheduler.run()
    except KeyboardInterrupt:
        graceful_exit("Keyboard interrupt received, exiting. (Code: 02)")
    except SystemExit:
        graceful_exit("Received SIGTERM signal, exiting. (Code: 03)")
    except KeyError as e:
        print e.message
        graceful_exit("Key error occurred, exiting. (Code: 04)")
    except Exception, e:
        graceful_exit(e.message)


def main():
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGHUP, sighup_handler)
    do_start()


if __name__ == '__main__':
    main()