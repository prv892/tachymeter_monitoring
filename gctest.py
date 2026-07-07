import pytest
from unittest.mock import MagicMock, patch

from pyGeoCOM.surveytools import SWVersion, Angle, Measurement, FullAngleMeasurement

from geocom.TotalStation import TotalStation
from geocom.enums import LeicaReturnCode, PositionMode, ATRMode, TMCInclinationSensorMeasurementProgram, FaceDef, \
    TMCMeasurementMode
from geocom.enums.EDMMeasurementMode import EDMMeasurementMode

class TestTotalStation:

    @patch('serial.Serial')
    def test_get_edm_mode(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.inWaiting.side_effect = [1, 0]
        mock_serial.readline.return_value = b'%R1P,0,0:0,2\r\n'
        ts = TotalStation('COM1')
        edm_mode = ts.get_edm_mode()
        assert edm_mode == EDMMeasurementMode.EDM_SINGLE_STANDARD
        mock_serial.write.assert_called_once_with(b'%R1Q,2021:\r\n')

    @patch('serial.Serial')
    def test_set_edm_mode(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.inWaiting.side_effect = [1, 0]
        mock_serial.readline.return_value = b'%R1P,0,0:0\r\n'
        ts = TotalStation('COM1')
        lrc = ts.set_edm_mode(EDMMeasurementMode.EDM_CONT_DYNAMIC)
        assert lrc == LeicaReturnCode.GRC_OK
        mock_serial.write.assert_called_once_with(b'%R1Q,2020:7\r\n')

    @patch('serial.Serial')
    def test_set_telescope_position(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.inWaiting.side_effect = [1, 0]
        mock_serial.readline.return_value = b'%R1P,0,0:0\r\n'

        ts = TotalStation('COM1')
        direction = Angle(1.234)  # Beispielwert
        zenith = Angle(2.345)     # Beispielwert
        pos_mode = PositionMode.AUT_NORMAL   # Beispiel aus Enum
        atr_mode = ATRMode.AUT_POSITION      # Beispiel aus Enum

        ret = ts.set_telescope_position(direction, zenith, pos_mode, atr_mode)
        assert ret == LeicaReturnCode.GRC_OK

        expected_command = f'%R1Q,9027:{direction.value_rad},{zenith.value_rad},{pos_mode.value},{atr_mode.value},0\r\n'.encode()
        mock_serial.write.assert_called_once_with(expected_command)

    @patch('serial.Serial')
    def test_get_simple_measurement(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.inWaiting.side_effect = [1, 0]
        # Rückgabe mit Hz=0.9973, V=1.6134, Dist=1.3581
        mock_serial.readline.return_value = b'%R1P,0,0:0,0.9973,1.6134,1.3581\r\n'

        ts = TotalStation('COM1')
        atmo = None  # oder ein Mock-Objekt, je nach Konstruktor von Measurement
        measure_time = 1234
        wait_time = 1000
        mode = TMCInclinationSensorMeasurementProgram.TMC_AUTO_INC
        target_nr = 1

        m = ts.get_simple_measurement(wait_time, mode, target_nr, atmo, measure_time)

        assert isinstance(m, Measurement)
        assert abs(m.direction.value_rad - 0.9973) < 0.0001
        assert abs(m.zenith.value_rad - 1.6134) < 0.0001
        assert abs(m.slope_distances - 1.3581) < 0.0001
        mock_serial.write.assert_called_once_with(f'%R1Q,2108:{wait_time},{mode.value}\r\n'.encode())

    @patch('serial.Serial')
    def test_get_instrument_number(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.inWaiting.side_effect = [1, 0]
        mock_serial.readline.return_value = b'%R1P,0,0:0,42\r\n'

        ts = TotalStation('COM1')
        number = ts.get_instrument_number()
        assert number == 42
        mock_serial.write.assert_called_once_with(b'%R1Q,5003:\r\n')

    @patch('serial.Serial')
    def test_get_software_version(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.inWaiting.side_effect = [1, 0]
        mock_serial.readline.return_value = b'%R1P,0,0:0,1,2,3\r\n'

        ts = TotalStation('COM1')
        sw_version = ts.get_software_version()
        assert isinstance(sw_version, SWVersion)
        assert sw_version.release == 1
        assert sw_version.version == 2
        assert sw_version.sub_version == 3
        mock_serial.write.assert_called_once_with(b'%R1Q,5034:\r\n')

    @patch('serial.Serial')
    def test_get_instrument_name(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial
        mock_serial.inWaiting.side_effect = [1, 0]
        mock_serial.readline.return_value = b'%R1P,0,0:0,TestInstrument\r\n'

        ts = TotalStation('COM1')
        name = ts.get_instrument_name()
        assert name == 'TestInstrument'
        mock_serial.write.assert_called_once_with(b'%R1Q,5004:\r\n')

    @patch('serial.Serial')
    def test_get_angle_complete(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial

        # Beispielantwort passend zur erwarteten Struktur:
        # response = ["%R1P,...", "0", "0", "Hz", "V", "Accuracy", "Time", "CrossIncline", "LengthIncline", "AccuracyIncline", "InclineTime", "FaceDef"]
        # Werte als Strings, FaceDef am Ende als Index
        response_str = b'%R1P,0,0:0,1.23,2.34,0.01,100,0.11,0.22,0.03,50,0\r\n'
        mock_serial.inWaiting.side_effect = [1, 0]
        mock_serial.readline.return_value = response_str

        ts = TotalStation('COM1')
        mode = TMCInclinationSensorMeasurementProgram.TMC_AUTO_INC

        angle = ts.get_angle_complete(mode)

        assert isinstance(angle, FullAngleMeasurement)
        assert abs(angle.hz.value_rad - 1.23) < 1e-4
        assert abs(angle.v.value_rad - 2.34) < 1e-4
        assert abs(angle.angle_accuracy.value_rad - 0.01) < 1e-4
        assert angle.angle_time == 100
        assert abs(angle.cross_incline.value_rad - 0.11) < 1e-4
        assert abs(angle.length_incline.value_rad - 0.22) < 1e-4
        assert abs(angle.accuracy_incline.value_rad - 0.03) < 1e-4
        assert angle.incline_time == 50
        assert angle.face_def == FaceDef.TMC_FACE_NORMAL

        mock_serial.write.assert_called_once_with(f'%R1Q,2003:{mode.value}\r\n'.encode())

    @patch('serial.Serial')
    def test_measure(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial

        ts = TotalStation('COM1')

        # Wir mocken die intern genutzten Methoden do_measure und get_simple_measurement
        ts.do_measure = MagicMock(return_value=LeicaReturnCode.GRC_OK)

        # Simuliere get_simple_measurement, gibt Measurement mit Distanz > 0 zurück (erster Aufruf)
        good_measurement = MagicMock()
        good_measurement.slope_distances = 10
        ts.get_simple_measurement = MagicMock(return_value=good_measurement)

        target_nr = 1
        atmo = MagicMock()  # Mock Atmosphärendaten
        measure_time = 1234

        result = ts.measure(target_nr, atmo, measure_time)

        # Prüfe, ob do_measure aufgerufen wurde
        ts.do_measure.assert_called_with(TMCMeasurementMode.TMC_DEF_DIST,
                                         TMCInclinationSensorMeasurementProgram.TMC_AUTO_INC)

        # Prüfe, ob get_simple_measurement mindestens einmal aufgerufen wurde
        ts.get_simple_measurement.assert_called()

        # Ergebnis sollte unser gutes Measurement sein
        assert result == good_measurement


test = TestTotalStation()

test.test_get_instrument_number()
test.test_set_telescope_position()
print("hi")