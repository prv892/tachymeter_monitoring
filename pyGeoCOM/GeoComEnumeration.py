from enum import Enum

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


class LeicaReturnCode(Enum):
    GRC_OK = 0  # Execution successful.
    NOTHING_TO_READ = 1
    GRC_IVPARAM = 2  # Invalid parameter (e.g. no valid position).
    GRC_IVRESULT = 3  # RL EDM type is set – no reflector./ Wrong values entered.
    GRC_FATAL = 4  # Fatal error
    GRC_NOT_IMPL = 5  # Not implemented yet.
    GRC_SETINCOMPLETE = 7  # Invalid number of parameters.
    GRC_ABORT = 8  # Function aborted.
    GRC_SHUT_DOWN = 12  # Error
    GRC_SYSBUSY = 13  # EDM already busy
    GRC_LOW_POWER = 16  # Power is low. Time remaining is about 30 Minutes.
    GRC_BATT_EMPTY = 18  # Battery is nearly empty. Time remaining is about 1 Minute.
    GRC_NA = 27  # GeoCOM Robotic license key not available
    GRC_ATA_NO_TARGET = 517  # No target detected
    GRC_ATA_STRANGE_LIGHT = 524  # No target detected
    GRC_EDM_INVALID_COMMAND = 770  # When an invalid intensity is entered
    GRC_EDM_DEV_NOT_INSTALLED = 778  # Laserpointer is not implemented
    TMC_NO_FULL_CORRECTION = 1283  # Error with angle measurement
    TMC_ACCURACY_GUARANTEE = 1284  # Info
    TMC_ANGLE_OK = 1285  # Warning
    TMC_ANGLE_NO_FULL_CORRECTION = 1288  # Warning
    TMC_ANGLE_ACCURACY_GUARANTEE = 1289  # Info
    TMC_ANGLE_ERROR = 1290  # Error
    TMC_DIST_PPM = 1291  # Error
    TMC_DIST_ERROR = 1292  # An error occurred during distance measurement.
    TMC_BUSY = 1293  # Error
    TMC_SIGNAL_ERROR = 1294  # Error
    GRC_MOT_UNREADY = 1792  # No movement in progress (e.g. stop without start).
    GRC_MOT_NOT_OCONST = 1794  # Drive is not in mode MOT_OCONST
    GRC_MOT_NOT_CONFIG = 1795  # System is not in state MOT_CONFIG or MOT_BUSY_OPEN_END
    GRC_COM_CANT_ENCODE = 3073  # Can't encode arguments in client.
    GRC_COM_CANT_DECODE = 3074  # Can't decode results in client.
    GRC_COM_CANT_SEND = 3075  # Failure in sending calls.
    GRC_COM_CANT_RECV = 3076  # Failure in receiving result
    GRC_COM_TIMEDOUT = 3077  # Communication timeout.
    GRC_COM_WRONG_FORMAT = 3078  # The request and receive formats are different
    GRC_COM_VER_MISMATCH = 3079  # RPC protocol mismatch error
    GRC_COM_CANT_DECODE_REQ = 3080  # Can't decode request in server
    GRC_COM_PROC_UNAVAIL = 3081  # The requested procedure is unavailable in the server.
    GRC_COM_CANT_ENCODE_REP = 3082  # Can't encode reply in server.
    GRC_COM_SYSTEM_ERR = 3083  # Communication hardware error
    GRC_COM_FAILED = 3085  # Mess into communication itself
    GRC_COM_NO_BINARY = 3086  # Unknown protocol
    GRC_COM_INTR = 3087  # Call interrupted
    GRC_COM_REQUIRES_8DBITS = 3090  # This error indicates desired protocol requires 8 data bits
    GRC_COM_TR_ID_MISMATCH = 3093  # Request and reply transaction ids do not match.
    GRC_COM_NOT_GEOCOM = 3094  # Parse failed; data package not recognised as GeoCOM communication package
    GRC_COM_UNKNOWN_PORT = 3095  # Tried to access an unknown hardware port.
    GRC_COM_OVERRUN = 3100  # Overruns during receive.
    GRC_COM_SRVR_RX_CHECKSUM_ERROR = 3101  # Checksum received at server is wrong
    GRC_COM_CLNT_RX_CHECKSUM_ERROR = 3102  # Checksum received at client is wrong
    GRC_COM_PORT_NOT_AVAILABLE = 3103  # COM port not available
    GRC_COM_PORT_NOT_OPEN = 3104  # COM port not opened / initialised
    GRC_COM_NO_PARTNER = 3105  # No communications partner on other end.
    GRC_COM_ERO_NOT_STARTED = 3106
    GRC_COM_CONS_REQ = 3107  # Attention to send consecutive requests.
    GRC_COM_SRVR_IS_SLEEPING = 3108  # TPS has gone to sleep. Wait and try again.
    GRC_COM_SRVR_IS_OFF = 3109  # TPS has shut down. Wait and try again
    GRC_AUT_TIMEOUT = 8704  # Timeout while positioning of one or both axes.
    GRC_AUT_Detent_ERROR = 8705  # Positioning not possible due to mounted EDM.
    GRC_AUT_ANGLE_ERROR = 8706  # Angle measurement error
    GRC_AUT_MOTOR_ERROR = 8707  # Instrument has no ‘motorization’.
    GRC_AUT_INCACC = 8708  # Position not exactly reached
    GRC_AUT_DEV_ERROR = 8709  # During the determination of the angle deviation error detected
    GRC_AUT_NO_TARGET = 8710  # No target found
    GRC_AUT_MULTIPLE_TARGETS = 8711  # Multiple targets found.
    GRC_AUT_BAD_ENVIRONMENT = 8712  # Bad environment conditions.
    GRC_AUT_DETECTOR_ERROR = 8713  # Error in target acquisition.
    GRC_AUT_NOT_ENABLED = 8714  # ATR mode not enabled
    GRC_AUT_CALACC = 8715  # ATR-calibration failed
    GRC_AUT_ACCURACY = 8716  # Inexact fine position
    GRC_AUT_DIST_STARTED = 8717  # Info
    GRC_AUT_SUPPLY_TOO_HIGH = 8718  # external Supply voltage is too high
    GRC_AUT_SUPPLY_TOO_LOW = 8719  # int. or ext. Supply volatage is too low
    GRC_AUT_NO_WORKING_AREA = 8720  # Working area not defined
    GRC_AUT_ARRAY_FULL = 8721  # power search data array is filled
    GRC_AUT_NO_DATA = 8722  # no data available
    GRC_AUT_SIDECOVER_ERR = 8723  # motion cannot executed because of sidecover
    GRC_AUT_OUT_OF_SYNC = 8724  # angle requested for time not in collection (probably telescope out of sync)
    GRC_AUT_NO_LOCK = 8725  # lock mode not allowed
    GRC_KDM_NOT_AVAILABLE = 12544  # KDM device is not available
    GRC_FTR_FILEACESS = 13056  # File access error
    GRC_FTR_WRONGFILEBLOCKNUMBER = 13057  # block number was not the expected one
    GRC_FTR_NOTENOUGHSPACE = 13058  # not enough space on device to proceed uploading
    GRC_FTR_INVALIDINPUT = 13059  # rename of file failed
    GRC_FTR_MISSINGSETUP = 13060  # invalid parameter as input


class OnOffType(Enum):
    OFF = 0
    ON = 1


class PositionMode(Enum):
    AUT_NORMAL = 0  # fast positioning mode
    AUT_PRECISE = 1  # exact positioning mode


class FineAdjustPositionMode(Enum):
    AUT_NORM_MODE = 0  # Angle tolerance
    AUT_POINT_MODE = 1  # Point tolerance#
    AUT_DEFINE_MODE = 2  # System independent positioning


class ATRMode(Enum):
    AUT_POSITION = 0  # Positioning to the hz- and v-angle
    AUT_TARGET = 1  # Positioning to a target in the environment of the hz- and v-angle.


class Directions(Enum):
    AUT_CLOCKWISE = 1  # direction clockwise.
    AUT_ANTICLOCKWISE = -1  # direction counter clockwise.


class BAPMeasurementModes(Enum):
    BAP_NO_MEAS = 0  # no measurements, take last one
    BAP_NO_DIST = 1  # no dist. measurement, angles only
    BAP_DEF_DIST = 2  # default distance measurements, pre-defined using
    BAP_CLEAR_DIST = 5  # clear distances
    BAP_STOP_TRK = 6  # stop tracking


class BAPDistanceMeasurementPrograms(Enum):
    BAP_SINGLE_REF_STANDARD = 0  # IR Standard
    BAP_SINGLE_REF_FAST = 1  # IR Fast
    BAP_SINGLE_REF_VISIBLE = 2  # LO Standard
    BAP_SINGLE_RLESS_VISIBLE = 3  # RL Standard
    BAP_CONT_REF_STANDARD = 4  # IR Tracking
    BAP_CONT_REF_FAST = 5  # not supported by TPS1200
    BAP_CONT_RLESS_VISIBLE = 6  # RL Fast Tracking
    BAP_AVG_REF_STANDARD = 7  # IR Average
    BAP_AVG_REF_VISIBLE = 8  # LO Average
    BAP_AVG_RLESS_VISIBLE = 9  # RL Average
    BAP_CONT_REF_SYNCRO = 10  # IR Synchro Tracking
    BAP_SINGLE_REF_PRECISE = 11  # IR Precise (TS30, TM30)


class BAPPrismenType(Enum):
    BAP_PRISM_ROUND = 0  # Leica Circular Prism
    BAP_PRISM_MINI = 1  # Leica Mini Prism
    BAP_PRISM_TAPE = 2  # Leica Reflector Tape
    BAP_PRISM_360 = 3  # Leica 360º Prism
    BAP_PRISM_USER1 = 4  # not supported by TPS1200
    BAP_PRISM_USER2 = 5  # not supported by TPS1200
    BAP_PRISM_USER3 = 6  # not supported by TPS1200
    BAP_PRISM_360_MINI = 7  # Leica Mini 360º Prism
    BAP_PRISM_MINI_ZERO = 8  # Leica Mini Zero Prism
    BAP_PRISM_USER = 9  # User Defined Prism
    BAP_PRISM_NDS_TAPE = 10  # Leica HDS Target
    BAP_PRISM_GRZ121_ROUND = 11  # GRZ121 360° prism for Machine Guidance
    BAP_PRISM_MA_MPR122 = 12  # MPR122 360° prism for Machine Guidance


class BAPReflectorTypeDefinition(Enum):
    BAP_REFL_UNDEF = 0  # reflector not defined
    BAP_REFL_PRISM = 1  # reflector prism
    BAP_REFL_TAPE = 2  # reflector tape


class TargetTypeDefinition(Enum):
    BAP_REFL_USE = 0  # with reflector
    BAP_REFL_LESS = 1  # without reflector


# class ATRLowVisDef(object):
#   BAP_ATRSET_NORMAL  # ATR is using no special flags or modes
#   BAP_ATRSET_LOWVIS_ON  # ATR low vis mode on
#   BAP_ATRSET_LOWVIS_AON  # ATR low vis mode always on
#   BAP_ATRSET_SRANGE_ON  # ATR high reflectivity mode on
#   BAP_ATRSET_SRANGE_AON  # ATR high reflectivity mode always on


class StopMode(Enum):
    COM_TPS_STOP_SHUT_DOWN = 0  # power down Instrument
    COM_TPS_STOP_SLEEP = 1  # Sleep Mode
    COM_TPS_STOP_GUI_ONLY = 4  # close onboard gui (Viva)


class StartMode(Enum):
    COM_TPS_STARTUP_LOCAL = 0  # not supported
    COM_TPS_STARTUP_REMOTE = 1  # RPC´s enabled online mode
    COM_TPS_STARTUP_GUI = 2  # start onboard gui (Viva)


class EDMMeasurementType(Enum):
    EDM_SIGNAL_MEASUREMENT = 1
    EDM_FREQ_MEASUREMENT = 2
    EDM_DIST_MEASUREMENT = 4
    EDM_ANY_MEASUREMENT = 8


class LockConditions(Enum):
    MOT_LOCKED_OUT = 0  # locked out
    MOT_LOCKED_IN = 1  # locked in
    MOT_PREDICTION = 2  # prediction mode


class MOTStopMode(Enum):
    MOT_NORMAL = 0  # Slow down with current acceleration
    MOT_SHUTDOWN = 1  # slow down by switch off power supply


class ControllerConfiguration(Enum):
    MOT_POSIT = 0  # configured for relative postioning
    MOT_OCONST = 1  # configured for constant speed
    MOT_MANUPOS = 2  # configured for manual positioning default setting
    MOT_LOCK = 3  # configured as "Lock-In"-controller
    MOT_BREAK = 4  # configured as "Brake"-controller do not use 5 and 6
    MOT_TERM = 7  # terminates the controller task


class ShutDownMechanismen(Enum):
    AUTO_POWER_DISABLED = 0  # instrument remains on
    AUTO_POWER_OFF = 2  # turns off mechanism


class TMCInclinationSensorMeasurementProgram(Enum):
    TMC_MEA_INC = 0  # Use sensor (apriori sigma)
    TMC_AUTO_INC = 1  # Automatic mode (sensor/plane)
    TMC_PLANE_INC = 2  # Use plane (apriori sigma)


class TMCMeasurementMode(Enum):
    TMC_STOP = 0  # Stop measurement program
    TMC_DEF_DIST = 1  # Default DIST-measurement program
    TMC_CLEAR = 3  # TMC_STOP and clear data
    TMC_SIGNAL = 4  # Signal measurement (test function)
    TMC_DO_MEASURE = 6  # Restart measurement task
    TMC_RTRK_DIST = 8  # Distance-TRK measurement program
    TMC_RED_TRK_DIST = 10  # Reflectorless tracking
    TMC_FREQUENCY = 11  # Frequency measurement (test)


class EDMMeasurementMode(Enum):
    EDM_MODE_NOT_USED = 0  # Init value
    EDM_SINGLE_TAPE = 1  # IR Standard Reflector Tape
    EDM_SINGLE_STANDARD = 2  # IR Standard
    EDM_SINGLE_FAST = 3  # IR Fast
    EDM_SINGLE_LRANGE = 4  # LO Standard
    EDM_SINGLE_SRANGE = 5  # RL Standard
    EDM_CONT_STANDARD = 6  # Standard repeated measurement
    EDM_CONT_DYNAMIC = 7  # IR Tacking
    EDM_CONT_REFLESS = 8  # RL Tracking
    EDM_CONT_FAST = 9  # Fast repeated measurement
    EDM_AVERAGE_IR = 10  # IR Average
    EDM_AVERAGE_SR = 11  # RL Average
    EDM_AVERAGE_LR = 12  # LO Average
