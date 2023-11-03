from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil
import time
import socket
import threading

local_host = '0.0.0.0'
remote_host = '192.168.155.122'
mode_port = 12345
ctrl_port = 60003
status_port = [60002,60004]
gps_port = [60015,60016]
gps_server_port = [60010,60011]

############################################################################################

class Drone:
    def __init__(self, connection_string, baudrate=None):
        self.vehicle = connect(connection_string, baud=baudrate)

    def send_ned_velocity(self, velocity_x, velocity_y, velocity_z):
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0,  # time_boot_ms (not used)
            0, 0,  # target system, target component
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,  # frame
            0b0000111111000111,  # type_mask (only speeds enabled)
            0, 0, 0,  # x, y, z positions (not used)
            velocity_x, velocity_y, velocity_z,  # x, y, z velocity in m/s
            0, 0, 0,  # x, y, z acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)  # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)

        self.vehicle.send_mavlink(msg)

    def takeoff(self):
        global stop
        print("Taking off!")
        self.vehicle.simple_takeoff(1)
        start_time = time.time()
        TIMEOUT_SECONDS = 10
        while True:
            current_altitude = self.vehicle.location.global_relative_frame.alt
            if current_altitude is not None:
                print(" Altitude: ", current_altitude)
                if current_altitude >= 1 * 0.9:
                    print("Reached target altitude")
                    break
            else:
                print("Waiting for altitude information...")
            if time.time() - start_time > TIMEOUT_SECONDS:
                break
            time.sleep(1)

    def arm(self, mode='GUIDED'):
        print("Arming motors")
        self.vehicle.mode = VehicleMode(mode)
        self.vehicle.armed = True

        while not self.vehicle.armed:
            print("Waiting for Arming")
            self.vehicle.armed = True
            time.sleep(1)

        print("Vehicle Armed")

    def disarm(self):
        print("Disarming motors")
        self.vehicle.armed = False

        while self.vehicle.armed:
            print("Waiting for disarming...")
            self.vehicle.armed = False
            time.sleep(1)

        print("Vehicle Disarmed")

    def land(self):
        self.vehicle.mode = VehicleMode("LAND")
        print("Landing")

    def exit(self):
        self.vehicle.close()
        print("Completed")

############################################################################################

MCU = Drone('/dev/serial0',baudrate=115200)
print("MCU connected")


# MCU = Drone('tcp:127.0.0.1:5762')
# print("MCU connected")
# CD1 = Drone('tcp:127.0.0.1:5772')
# print("CD1 Connected")

Drone_ID = MCU

############################################################################################

def ServerSendStatus(drone, local_host, status_port):
    status_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    status_socket.bind((local_host, status_port))
    status_socket.listen(1)

    print('{} - ServerSendStatus is started!'.format(time.ctime()))

    while True:
        try:
            client_connection, client_address = status_socket.accept()

            status_data = status(drone)  # Call your status function here
            client_connection.send(status_data.encode())  # Send the string

        except KeyboardInterrupt:
            # Handle KeyboardInterrupt to gracefully exit the loop
            break
        except Exception as e:
            # Handle other exceptions, e.g., if the client disconnects unexpectedly
            print(f"Error: {e}")
            time.sleep(1)
        finally:
            if client_connection:
                client_connection.close()
            time.sleep(1)

    status_socket.close()

def status(drone):
    vehicle = drone.vehicle

    if vehicle is None:
        return "Not connected"

    b = str(vehicle.battery.voltage) if vehicle.battery is not None else '0'
    gs = str(vehicle.groundspeed) if hasattr(vehicle, 'groundspeed') else '0'
    md = str(vehicle.mode) if hasattr(vehicle, 'mode') else 'UNKNOWN'
    vx = str(vehicle.velocity[0]) if hasattr(vehicle, 'velocity') and len(vehicle.velocity) > 0 else '0'
    vy = str(vehicle.velocity[1]) if hasattr(vehicle, 'velocity') and len(vehicle.velocity) > 1 else '0'
    vz = str(vehicle.velocity[2]) if hasattr(vehicle, 'velocity') and len(vehicle.velocity) > 2 else '0'
    gps = str(vehicle.gps_0.fix_type) if hasattr(vehicle, 'gps_0') and hasattr(vehicle.gps_0, 'fix_type') else '0'
    lat = '{:.7f}'.format(vehicle.location.global_relative_frame.lat) if hasattr(vehicle, 'location') else '0'
    lon = '{:.7f}'.format(vehicle.location.global_relative_frame.lon) if hasattr(vehicle, 'location') else '0'
    alt = str(vehicle.location.global_relative_frame.alt) if hasattr(vehicle, 'location') else '0'
    armed = str(vehicle.armed) if hasattr(vehicle, 'armed') else 'False'

    status_str = ','.join([b, gs, md, vx, vy, vz, gps, lat, lon, alt, armed])

    return status_str

############################################################################################

def reconnectdrone(drone,connection,baud=None):
    drone.exit()
    time.sleep(1)
    drone = Drone(connection_string=connection,baudrate=baud)
    print("Drone Reconnected Successfully!")

############################################################################################

def ServerRecvCmd(local_host):
    global mode_port
    global Drone_ID
    cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cmd_socket.bind((local_host, mode_port))
    cmd_socket.listen(1)

    print('{} - SERVER_receive_and_execute_immediate_command() is started!'.format(time.ctime()))

    while True:
        try:
            client_connection, client_address = cmd_socket.accept()
            print('\n{} - Received immediate command from {}.'.format(time.ctime(), client_address))

            immediate_command_str = client_connection.recv(1024).decode()  # Receive and decode the command

            print('{} - Immediate command is: {}'.format(time.ctime(), immediate_command_str))
            
            if immediate_command_str == 'MCU':
                Drone_ID = MCU
                MCU.land()
                print("Reconnecting MCU Drone................................................................")
                time.sleep(1)
                threading.Thread(target=reconnectdrone, args=(MCU,'/dev/serial0',115200,)).start()
            if immediate_command_str == 'ARM':
                drone_arm(MCU)
            if immediate_command_str == 'land_all':
                drone_land(MCU)
            if immediate_command_str == 'TakeOff':
                Drone_ID.takeoff()
            if immediate_command_str == 'takeoff':
                drone_takeoff(MCU)
            if immediate_command_str == 'POSHOLD':
                drone_mode(MCU, 'POSHOLD')

            
        except KeyboardInterrupt:
            # Handle KeyboardInterrupt to gracefully exit the loop
            break
        except Exception as e:
            # Handle other exceptions, e.g., if the client disconnects unexpectedly
            print(f"Error: {e}")
            time.sleep(1)
        finally:
            if client_connection:
                client_connection.close()

############################################################################################

def ServerRecvControl(local_host):
    global ctrl_port
    global Drone_ID
    control_socket = socket.socket()
    control_socket.bind((local_host, ctrl_port))
    control_socket.listen(1)

    print('{} - SERVER_receive_control_commands() is started!'.format(time.ctime()))

    while True:
        try:
            client_connection, client_address = control_socket.accept()
            print('\n{} - Received control command from {}.'.format(time.ctime(), client_address))

            control_command_str = client_connection.recv(1024).decode()  # Receive and decode the command

            print('{} - Control command is: {}'.format(time.ctime(), control_command_str))
            
            try:
                x, y, z = map(float, control_command_str.split(','))  # Split and convert to floats
                ctrl(MCU, x, y, z)
            except ValueError:
                print("Invalid control command format. Expected 'x,y,z'")
        except KeyboardInterrupt:
            # Handle KeyboardInterrupt to gracefully exit the loop
            break
        except Exception as e:
            # Handle other exceptions, e.g., if the client disconnects unexpectedly
            print(f"Error: {e}")
            time.sleep(1)
        finally:
            if client_connection:
                client_connection.close()

############################################################################################

def drone_arm(drone):
    threading.Thread(target=drone.arm, args=('GUIDED',)).start()

def drone_takeoff(drone):
    threading.Thread(target=drone.takeoff).start()
    print(drone, "takeoff")

def drone_vel_ctrl(drone,x,y,z):
    drone.send_ned_velocity(x,y,z)
    time.sleep(0.5)
    drone.send_ned_velocity(0,0,0)

def ctrl(drone,x,y,z):
    threading.Thread(target=drone.send_ned_velocity, args=(x,y,z,)).start()

def set_mode(drone,mode):
    drone.vehicle.mode = VehicleMode(mode)

def drone_mode(drone,mode):
    threading.Thread(target=set_mode, args= (drone,mode,)).start()

def drone_land(drone):
    threading.Thread(target=drone.land).start()


############################################################################################

def start_server_service(local_host):
    threading.Thread(target=ServerRecvCmd, args=(local_host,)).start()
    threading.Thread(target=ServerRecvControl, args=(local_host,)).start()
    print("Thread serverRecvMode and ServerRecvControl are started!")

############################################################################################

def main():

    start_server_service(local_host)
    threading.Thread(target=ServerSendStatus, args=(MCU, local_host, status_port[0],)).start()
    print("MCU SendStatus Active")

############################################################################################

time.sleep(1)
main()
