 # -*- coding: utf-8 -*-

# ce fichier contient les memes fonctions que ax12driver.c, mais ecrites en
# python cette fois-ci et encapsulées dans une classe AX12
# donc cf ax12driver.h pour avoir la doc
# en plus, une verification de la validite des arguments est faite
# ie, si on envoie un float la ou il faut un int, ca va lever une AssertionError
# verifie aussi la coherence en fonction des parametres physiques de la datasheet


from encapsulate_callback import encapsulate_callback
from I2C_bus import *



class Communication_Error(Exception):

    errors = ["No error", "Serial port not initialized", "Wrong checksum", "Target and answer ID mismatch", "Timeout", "Callback buffer is full"]

    def __init__(self, index):
        if index>=len(Communication_Error.errors) or index<0:
            self.msg = "No error matching return code"
        else:
            self.msg = Communication_Error.errors[index]

    def __str__(self):
        return self.msg



DEFAULT_MODE    =   0
WHEEL_MODE      =   1
def check_mode(m):
    assert (m in [DEFAULT_MODE, WHEEL_MODE])


class AX12:
    """
    AX12 emulates a physical AX12 servomotor
    """
    def __init__(self, id, baudrate=115200):
        """
        Construct a new 'AX12' object and instanciates I2C_bus if needed

        :param id: The id of the AX12, must be between 0 and 255
        :param baudrate: The baudrate to communicate with the AX12, defaults to 115200
        :return: returns nothing
        """
        check_uint8(id)
        self.id = id
        if I2C_bus.instance is None:
            I2C_bus(baudrate)
        elif I2C_bus.baudrate != baudrate:
            print "[.] Baudrate used to communicate with AX12 id "+str(id)+" ("+str(baudrate)+") does not match previously established baudrate ("+I2C_bus.baudrate+") (changing it)"
            I2C_bus(baudrate)


    @classmethod
    def scan_i2c(cls, print_on_fly=None, baudrate=None):
        """
        Lists AX12 connected to the raspberry

        :return: A list of the id of the connected raspberry
        """
        if I2C_bus.instance is None and baudrate is None:
            print "[-] Unable to scan I2C bus because not initialized"
            return None
        elif I2C_bus.instance is None:
            I2C_bus(baudrate)
        elif baudrate is not None and baudrate != I2C_bus.baudrate:
            print "[.] Baudrate used to scan i2c does not match previously established baudrate ("+I2C_bus.baudrate+") (changing it)"
            I2C_bus(baudrate)
        return I2C_bus.scan(print_on_fly)


    def ping(self):
        """
        Pings the AX12

        :return: 0 if the ping succeeded, a negative error value else
        """
        return I2C_bus.ping(self.id)


    def get_status(self):
        """
        Checks the status of the AX12

        :return: 0 if everything is fine, a negative value in case of an error
        """
        return int(lib_ax12.AX12getStatus(ctypes.c_uint8(self.id)))


    def get_position(self):
        """
        Gets the current position of the AX12

        :return: The position in degree from -150 to 150 increasing clockwise
        """
        return lib_ax12.AX12getPosition(ctypes.c_uint8(self.id))


    def get_speed(self):
        """
        Gets the current speed of the AX12, may be inaccurate

        :return: The speed in %, a positive value means a clockwise speed
        """
        return lib_ax12.AX12getSpeed(ctypes.c_uint8(self.id))


    def get_load(self):
        """
        Gets the current load of the AX12, may be inaccurate

        :return: The load in %, a positive value means a clockwise load
        """
        return lib_ax12.AX12getLoad(ctypes.c_uint8(self.id))


    def get_voltage(self):
        """
        Gets the current voltage of the AX12

        :return: The voltage in Volts
        """
        return lib_ax12.AX12getVoltage(ctypes.c_uint8(self.id))


    def get_temperature(self):
        """
        Gets the current temperature of the AX12

        :return: The temperature in Celcius degrees
        """
        return int(lib_ax12.AX12getTemperature(ctypes.c_uint8(self.id)))


    def is_moving(self):
        """
        Checks if the AX12 is moving

        :return: 1 if the AX12 is moving, 0 otherwise
        """
        return int(lib_ax12.AX12isMoving(ctypes.c_uint8(self.id)))


    def set_mode(self, mode):
        """
        Sets the mode of the AX12

        :param mode: 0 for default mode, 1 for wheel mode
        :return: 0 in case of success, raises an exception otherwise
        """
        check_mode(mode)

        ret = int(lib_ax12.AX12setMode(ctypes.c_uint8(self.id),
                                       ctypes.c_int(mode)))
        if ret<0:
            raise Communication_Error(-ret)
        return ret


    def set_speed(self, speed):
        """
        Sets the speed of the AX12

        :param speed: A percentage, positive for a clockwise speed
        :return: 0 in case of success, raises an exception otherwise
        """
        ret = int(lib_ax12.AX12setSpeed(ctypes.c_uint8(self.id),
                                        ctypes.c_double(speed)))
        if ret<0:
            raise Communication_Error(-ret)
        return ret


    def set_torque(self, torque):
        """
        Sets the torque limit of the AX12

        :param torque: A percentage, if 0 the AX12 won't be able to move
        :return: 0 in case of success, raises an exception otherwise
        """
        ret = int(lib_ax12.AX12setTorque(ctypes.c_uint8(self.id),
                                         ctypes.c_double(torque)))
        if ret<0:
            raise Communication_Error(-ret)
        return ret


    def set_LED(self, state):
        """
        Sets the LED state of the AX12

        :param state: 1 to put the LED on, 0 to put the LED off
        :return: 0 in case of success, raises an exception otherwise
        """
        assert(isinstance(state, int))

        ret = int(lib_ax12.AX12setLED(ctypes.c_uint8(self.id),
                                      ctypes.c_int(state)))
        if ret<0:
            raise Communication_Error(-ret)
        return ret


    def move(self, position, callback=lambda:None):
        """
        Orders the AX12 to move to a specified position

        :param position: A position in degree from -150 to 150 increasing clockwise
        :param callback: A function to be called at the end of the movement
        :return: 0 in case of success, raises an exception otherwise
        """
        assert(isinstance(position, float) or isinstance(position, int))
        assert(callable(callback))

        ret = int(lib_ax12.AX12move(ctypes.c_uint8(self.id),
                                    ctypes.c_double(position),
                                    encapsulate_callback(callback)))
        if ret<0:
            raise Communication_Error(-ret)
        return ret


    def cancel_callback(self):
        """
        Cancels the end move callback of the AX12

        :return: Returns nothing
        """
        lib_ax12.AX12CancelCallback(ctypes.c_uint8(self.id))


    def turn(self, speed):
        """
        Orders the AX12 to turn at a constant speed

        :param speed: a percentage, positive for a clockwise speed
        :return: 0 in case of success, raises an exception otherwise
        """
        assert(isinstance(speed, float) or isinstance(speed, int))

        ret = int(lib_ax12.AX12turn(ctypes.c_uint8(self.id),
                                    ctypes.c_double(speed)))
        if ret<0:
            raise Communication_Error(-ret)
        return ret
