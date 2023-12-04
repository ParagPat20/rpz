from drone import Drone
from drone import *


cmd_port = 12345
ctrl_port = 54321
status_port = 60001
local_host = MCU_host

MCU = None

##################################################### Initialization #####################################################

MCU_initialized = False
d1 = None

msg_socket = socket.socket()
msg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
msg_socket.bind((local_host, cmd_port))
msg_socket.listen(5)
print('{} - SERVER_receive_and_execute_immediate_command() is started!'.format(time.ctime()))

def drone_list_update(cmd):
    try:
        global drone_list
        drone_list = cmd
        print(drone_list)
    except Exception as e:
        log(f"MCU_Host: Error in drone_list_update: {e}")


##########################################################################################################################

def initialize_MCU():
    try:
        global d1, MCU, MCU_initialized
        if not MCU and not MCU_initialized:
            MCU = Drone('/dev/serial0', 115200)
            d1 = MCU
            d1_str = 'MCU'
            print("MCU Connected")
            threading.Thread(target=MCU.send_status, args=(MCU_host,60001,)).start()
            MCU_initialized=True
        log("MCU getting ready for the params...")
        time.sleep(2) #getting ready for params
        MCU.get_vehicle_state()
    except Exception as e:
        log(f"MCU_Host: Error in initialize_MCU: {e}")

##########################################################################################################################
print("Sending IP to Computer, please start the computer")
try:
    log("Starting MCU_host at {}".format(socket.gethostbyname(socket.gethostname())))
except Exception as e:
    print(f"Error: {e}")
print("Cheers! Server is already going on!")
##########################################################################################################################

server_receive_and_execute_immediate_command(MCU_host)

##########################################################################################################################
