import time
import math
from typing import Union, List

import serial

from pyGeoCOM.GeoComEnumeration import *
from pyGeoCOM.surveytools import *


"""
entnommen aus pyGeoCOM,

MIT License

Copyright (c) 2025 Stefan Printz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""


RHO = 200 / math.pi

class AtmosphericData(object):
    def __init__(self, dry_temperature: float, pressure: float, humidity: float):
        self.pressure = pressure
        self.dry_temperature = dry_temperature
        self.humidity = humidity

    def __str__(self):
        return 'Temperatur: {0:.2f}, Luftdruck: {1:.2f}, Luftfeuchte: {2:.2f}'.format(self.dry_temperature, self.pressure, self.humidity)

    def wet_temperature(self):
        return 0.058 * self.humidity + 0.697 * self.dry_temperature + 0.003 * self.dry_temperature * self.humidity - 5.809


class TCException(Exception):
    def __init__(self, return_code: LeicaReturnCode):
        self.returnMessage = return_code.name


class AtmosphericCorrectionData(object):

    def __init__(self, lambda_value: float, pressure: float, dry_temperature: float, wet_temperature: float):
        self.lambda_value = lambda_value
        self.pressure = pressure
        self.dry_temperature = dry_temperature
        self.wet_temperature = wet_temperature

    def __str__(self):
        return str(self.lambda_value) + "," + str(self.pressure) + "," + str(self.dry_temperature) + "," + str(
            self.wet_temperature)


class TotalStation(object):

    def __init__(self, serialPortCOM, baudrate=9600, bytesize=8, parity=serial.PARITY_NONE, timeout=1, stopbits=1):
        self.last_return_code = LeicaReturnCode.GRC_OK
        self.waiting_instrument = 0
        self.serialPort = serial.Serial(port=serialPortCOM, baudrate=baudrate,
                                        bytesize=bytesize, parity=parity,
                                        timeout=timeout, stopbits=stopbits)

    def read_data_from_port(self) -> List[Union[LeicaReturnCode, str]]:
        time_wait = 0.5
        time_count = 0

        while True:
            time_count += time_wait
            if self.serialPort.inWaiting() > 0:
                out = self.serialPort.readline()
                print("read_data_from_port: " + str(out))
                out = out.decode("utf-8").rstrip()
                test = out[0:4]
                if out[0:4] == "%R1P":
                    out = out.split(":")
                    # out[0] protocol header
                    # out[1] following parameters
                    param = out[1].split(",")

                    # Set Enum vor Leica Return
                    param[0] = LeicaReturnCode(int(param[0]))
                    self.last_return_code = param[0]
                    self.waiting_instrument = 0
                    return param
            if time_count > 30:
                self.waiting_instrument = 0
                raise TCException(LeicaReturnCode.GRC_AUT_TIMEOUT)
            time.sleep(time_wait)

    def request(self, command: str) -> List[Union[LeicaReturnCode, str]]:
        """

        :param command:  ASCII-Request String from GeoCOM Reference Manuel (example: "%R1Q,2021:")
        :return: List with the Response. First element is {LeicaReturnCode} other as String

        """
        send_commad = (command + "\r\n").encode()

        if self.waiting_instrument == 1:
            print("Wait... ")
            time.sleep(10)

        print("Send: " + str(send_commad))
        self.waiting_instrument = 1

        self.serialPort.write(send_commad)
        time_wait = 0.5
        time_count = 0

        return self.read_data_from_port()

    def get_edm_mode(self) -> EDMMeasurementMode:
        response = self.request("%R1Q,2021:")
        return EDMMeasurementMode(int(response[1]))

    def set_edm_mode(self, edm: EDMMeasurementMode) -> LeicaReturnCode:
        """
        This function sets the current measurement mode. The measure function TMC_DoMeasure(TMC_DEF_DIST)
        uses this configuration.
        :param edm:
        :return:
        """
        response = self.request('%R1Q,2020:{0}'.format(edm.value))
        return response[0]

    def get_atm_correction(self) -> AtmosphericCorrectionData:
        """
        This function is used to get the parameters for the atmospheric correction
        :return:
        """
        response = self.request("%R1Q,2029:")
        return AtmosphericCorrectionData(float(response[1]), float(response[2]), float(response[3]), float(response[4]))

    def set_atm_correction(self, atm: AtmosphericCorrectionData) -> LeicaReturnCode:
        response = self.request("%R1Q,2028:" + str(atm))
        return response[0]

    def get_incline_switch(self):
        response = self.request("%R1Q,2007:")
        return OnOffType(int(response[1]))

    def set_incline_switch(self, state: OnOffType):
        response = self.request('%R1Q,2006:{0}'.format(state.value))
        return response[0]

    def edm_laserpointer(self, state: OnOffType):
        response = self.request('%R1Q,1004:{0}'.format(state.value))
        return response[0]

    def get_prism_constant(self) -> float:
        """
        This function is used to get the prism constant.
        :return:
        """
        response = self.request("%R1Q,2023:")
        return float(response[1])

    def wake_up(self):
        """
        Turn the instrument on.
        :return:
        """
        self.serialPort.write(b'%R1Q,18006:\r\n')
        time.sleep(30)
        self.serialPort.flushInput()

    def turn_off(self):
        """
        This function switches off the TPS1200 instrument
        :return:
        """
        response = self.request("%R1Q,112:0")
        return response[0]

    def get_instrument_name(self) -> str:
        """
        Gets the instrument name.
        :return:
        """
        response = self.request("%R1Q,5004:")
        return response[1]

    def get_software_version(self):
        response = self.request("%R1Q,5034:")
        return SWVersion(int(response[1]), int(response[2]), int(response[3]))

    def get_instrument_number(self) -> int:
        """
        Gets the factory defined serial number of the instrument.
        :return:
        """

        response = self.request("%R1Q,5003:")
        return int(response[1])



    def do_measure(self, command: TMCMeasurementMode, mode: TMCInclinationSensorMeasurementProgram) -> LeicaReturnCode:
        """
        This function carries out a distance measurement according to the TMC measurement mode like single distance,
        tracking,... . Please note that this command does not output any values (distances). In order to get the values you
        have to use other measurement functions such as TMC_GetCoordinate, TMC_GetSimpleMea or
        TMC_GetAngle.
        The result of the distance measurement is kept in the instrument and is valid to the next TMC_DoMeasure
        command where a new distance is requested or the distance is clear by the measurement program TMC_CLEAR.
        :return:
        """
        response = self.request("%R1Q,2008:{0},{1}".format(command.value, mode.value))
        return response[0]

    def get_simple_measurement(self, wait_time: int, mode: TMCInclinationSensorMeasurementProgram,
                               target_nr: int, atmospheric_data, measure_time) -> Measurement:
        """
        This function returns the angles and distance measurement data. This command does not issue a new distance
        measurement. A distance measurement has to be started in advance. If a distance measurement is valid the
        function ignores WaitTime and returns the results. If no valid distance measurement is available and the
        distance measurement unit is not activated (by TMC_DoMeasure before the TMC_GetSimpleMea call) the angle
        measurement result is returned after the waittime. Information about distance measurement is returned in the
        return code.
        :param target_nr:
        :param wait_time:
        :param mode:
        :return:
        """

        response = self.request("%R1Q,2108:{0},{1}".format(wait_time, mode.value))
        #print("get_simple_measurement out: " + str(response))

        if response[0] == LeicaReturnCode.GRC_OK:
            return Measurement(target_nr, Angle(float(response[1])), Angle(float(response[2])), float(response[3]), atmospheric_data, measure_time)
        else:
            return Measurement(target_nr, Angle(0), Angle(0), 0, atmospheric_data, measure_time)

    def search_target(self) -> LeicaReturnCode:
        """
        This function searches for a target in the configured or defined ATR SearchWindow. The functionality is only
        available for automated instruments.
        :return:
        """

        response = self.request("%R1Q,17020:0")
        return response[0]

    def get_internal_temperature(self) -> int:
        """
        Get the internal temperature of the instrument, measured on the Mainboard side. Values are reported in degrees
        Celsius.
        :return:
        """

        response = self.request("%R1Q,5011:")
        return int(response[1])

    def set_user_atr_state(self, state: OnOffType) -> LeicaReturnCode:
        response = self.request("%R1Q,18005:{0}".format(state.value))
        return response[0]

    def set_telescope_position(self, direction: Angle, zenith: Angle, pos_mode: PositionMode, atr_mode: ATRMode) -> LeicaReturnCode:
        response = self.request("%R1Q,9027:{0},{1},{2},{3},0".format(direction.value_rad, zenith.value_rad, pos_mode.value, atr_mode.value))
        return response[0]

    def set_telescope_to_second_face(self, pos_mode: PositionMode, atr_mode: ATRMode) -> LeicaReturnCode:
        """
        This procedure turns the telescope to the other face. If another function is active, for example locking onto a
        target, then this function is terminated and the procedure is executed.
        If the position mode is set to normal (PosMode = AUT_NORMAL) it is allowed that the current value of the
        compensator measurement is inexact. Positioning precise (PosMode = AUT_PRECISE) forces a new
        compensator measurement. If this measurement is not possible, the position does not take place.
        If ATR mode is activated and the ATR mode is set to AUT_TARGET, the instrument tries to position onto a target
        in the destination area.
        If LOCK mode is activated and the ATR mode is set to AUT_TARGET, the instrument tries to lock onto a target
        in the destination area.
        """
        response = self.request("%R1Q,9028:{0},{1},0".format(pos_mode.value, atr_mode.value))
        return response[0]

    def fine_adjust(self, hz_area: Angle, v_area: Angle):
        """
        This procedure precisely positions the telescope crosshairs onto the target prism and measures the ATR Hz and
        V deviations. If the target is not within the visible area of the ATR sensor (Field of View) a target search will
        be executed. The target search range is limited by the parameter dSrchV in V- direction and by parameter dSrchHz
        in Hz - direction. If no target found the instrument turns back to the initial start position.
        A current Fine Adjust LockIn towards a target is terminated by this procedure call. After positioning, the lock
        mode is active. The timeout of this operation is set to 5s, regardless of the general position timeout settings.
        The positioning tolerance is depends on the previously set up the fine adjust mode (see AUT_SetFineAdjustMoed
        and AUT_GetFineAdjustMode).
        Tolerance settings (with AUT_SetTol and AUT_ReadTol) have no influence to this operation. The tolerance
        settings as well as the ATR measure precision depends on the instrument’s class and the used EDM measure
        mode (The EDM measure modes are handled by the subsystem TMC).
        :param hz_area: Search range Hz-axis
        :param v_area: Search range V-axis
        :return:
        """
        response = self.request("%R1Q,9037:{0},{1},0".format(hz_area.value_rad, v_area.value_rad))
        return response[0]

    def get_fine_adjust_mode(self) -> FineAdjustPositionMode:
        """
        This function returns the current activated fine adjust positioning mode. This command is valid for all
        instruments, but has only effects for instruments equipped with ATR.
        :return:
        """
        response = self.request("%R1Q,9030:")
        return FineAdjustPositionMode(int(response[1]))

    def set_fine_adjust_mode(self, adj_mode: FineAdjustPositionMode) -> LeicaReturnCode:
        """
        This function sets the positioning tolerances (default values for both modes) relating the angle accuracy or the
        point accuracy for the fine adjust. This command is valid for all instruments, but has only effects for instruments
        equipped with ATR. If a target is very near or held by hand, it’s recommended to set the adjust-mode to
        AUT_POINT_MODE.
        :param: AdjMode: 0=Fine positioning with angle tolerance, 1=Fine positioning with point tolerance
        :return:
        """
        response = self.request("%R1Q,9031:{0}".format(adj_mode.value))
        return response[0]

    def get_angle_complete(self, mode: TMCInclinationSensorMeasurementProgram):
        """
        This function carries out an angle measurement and, in dependence of configuration, inclination measurement
        and returns the results. As shown the result is very comprehensive. For simple angle measurements use
        TMC_GetAngle5 or TMC_GetSimpleMea instead.
        Information about measurement is returned in the return code.
        :param mode:
        :return:
        """

        response = self.request("%R1Q,2003:{0}".format(mode.value))
        a = FullAngleMeasurement()

        a.hz = Angle(float(response[1]))
        a.v = Angle(float(response[2]))
        a.angle_accuracy = Angle(float(response[3]))
        a.angle_time = int(response[4])
        a.cross_incline = Angle(float(response[5]))
        a.length_incline = Angle(float(response[6]))
        a.accuracy_incline = Angle(float(response[7]))
        a.incline_time = int(response[8])
        a.face_def = int(response[9])

        return a

    def measure(self, target_nr: int, atmo, measure_time):
        #testweise ein fineadjust force, um ergebnis zu verbessern
        #h_suchbereich = Angle(0.005*math.pi/200)
        #v_suchbereich = Angle(0.005*math.pi/200)
        #self.fine_adjust(h_suchbereich,v_suchbereich)
        
        # start distance measurement
        print('start distance measurement')
        self.do_measure(TMCMeasurementMode.TMC_DEF_DIST, TMCInclinationSensorMeasurementProgram.TMC_AUTO_INC)

        for a in range(1, 8):
            time.sleep(3)
            m = self.get_simple_measurement(30, TMCInclinationSensorMeasurementProgram.TMC_AUTO_INC, target_nr, atmo, measure_time)
            if m.slope_distances > 0:
                return m

        print("no Distance arrived, searching...")
        ##hier hat paul rumgepfuscht
        ##ACHTUNG: winkel in gon eintragen, vorher distanz zu zielen berücksichtigen, es darf kein überlapp entstehen!!!
        #h_suchbereich = Angle(3.0*math.pi/200)
        #v_suchbereich = Angle(3.0*math.pi/200)
        #self.fine_adjust(h_suchbereich,v_suchbereich)
        
        print("Try new measurement")
        self.do_measure(TMCMeasurementMode.TMC_DEF_DIST, TMCInclinationSensorMeasurementProgram.TMC_AUTO_INC)
        time.sleep(20)
        return self.get_simple_measurement(30, TMCInclinationSensorMeasurementProgram.TMC_AUTO_INC, target_nr, atmo, measure_time)