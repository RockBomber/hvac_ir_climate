# HVAC-IR-Control - Python port for RPI3
# Eric Masse (Ericmas001) - 2017-06-30
# https://github.com/Ericmas001/HVAC-IR-Control
# Tested on Mitsubishi Model MSZ-FE12NA

# From original: https://github.com/r45635/HVAC-IR-Control
# (c)  Vincent Cruvellier - 10th, January 2016 - Fun with ESP8266

from . import ir_sender
from datetime import datetime


class PowerMode:
    """
    PowerMode
    """
    PowerOff = 0b00000000       # 0x00      0000 0000        0
    PowerOn = 0b00100000        # 0x20      0010 0000       32


class ClimateMode:
    """
    ClimateMode
    """
    Hot = 0b00001000            # 0x08      0000 1000        8
    Cold = 0b00011000           # 0x18      0001 1000       24
    Dry = 0b00010000            # 0x10      0001 0000       16
    Auto = 0b00100000           # 0x20      0010 0000       32

    __Hot2 = 0b00000000         # 0x00      0000 0000        0
    __Cold2 = 0b00000110        # 0x06      0000 0110        6
    __Dry2 = 0b00000010         # 0x02      0000 0010        2
    __Auto2 = 0b00000000        # 0x00      0000 0000        0

    @classmethod
    def climate2(cls, climate_mode):
        """
        climate2: Converts to the second climate value
        (For ClimateAndHorizontalVanne)
        """
        if climate_mode == cls.Hot:
            return cls.__Hot2
        if climate_mode == cls.Cold:
            return cls.__Cold2
        if climate_mode == cls.Dry:
            return cls.__Dry2
        if climate_mode == cls.Auto:
            return cls.__Auto2


class ISeeMode:
    """
    ISeeMode
    """
    ISeeOff = 0b00000000        # 0x00      0000 0000        0
    ISeeOn = 0b01000000         # 0x40      0100 0000       64


class PowerfulMode:
    """
    PowerfulMode
    """
    PowerfulOff = 0b00000000        # 0x00      0000 0000        0
    PowerfulOn = 0b00001000         # 0x08      0000 1000        8


class VanneHorizontalMode:
    """
    VanneHorizontalMode
    """
    NotSet = 0b00000000         # 0x00      0000 0000        0
    Left = 0b00010000           # 0x10      0001 0000       16
    MiddleLeft = 0b00100000     # 0x20      0010 0000       32
    Middle = 0b00110000         # 0x30      0011 0000       48
    MiddleRight = 0b01000000    # 0x40      0100 0000       64
    Right = 0b01010000          # 0x50      0101 0000       80
    Swing = 0b11000000          # 0xC0      1100 0000      192


class FanMode:
    """
    FanMode
    """
    Speed1 = 0b00000001         # 0x01      0000 0001        1
    Speed2 = 0b00000010         # 0x02      0000 0010        2
    Speed3 = 0b00000011         # 0x03      0000 0011        3
    Speed4 = 0b00000100         # 0x04      0000 0100        4
    Auto = 0b10000000           # 0x80      1000 0000      128


class VanneVerticalMode:
    """
    VanneVerticalMode
    """
    Auto = 0b01000000           # 0x40      0100 0000       64
    Top = 0b01001000            # 0x48      0100 1000       72
    MiddleTop = 0b01010000      # 0x50      0101 0000       80
    Middle = 0b01011000         # 0x58      0101 1000       88
    MiddleBottom = 0b01100000   # 0x60      0110 0000       96
    Bottom = 0b01101000         # 0x68      0110 1000      104
    Swing = 0b01111000          # 0x78      0111 1000      120


class TimeControlMode:
    """
    TimeControlMode
    """
    NoTimeControl = 0b00000000  # 0x00      0000 0000        0
    ControlStart = 0b00000101   # 0x05      0000 0101        5
    ControlEnd = 0b00000011     # 0x03      0000 0011        3
    ControlBoth = 0b00000111    # 0x07      0000 0111        7


class AreaMode:
    """
    AreaMode
    """
    NotSet = 0b00000000         # 0x00      0000 0000        0
    Left = 0b01000000           # 0x40      0100 0000       64
    Right = 0b11000000          # 0xC0      1100 0000      192
    Full = 0b10000000           # 0x80      1000 0000      128


class Delay:
    """
    Delay
    """
    HdrMark = 3400
    HdrSpace = 1750
    BitMark = 450
    OneSpace = 1300
    ZeroSpace = 420
    RptMark = 440
    RptSpace = 17100


class Index:
    """
    Index
    """
    Header0 = 0
    Header1 = 1
    Header2 = 2
    Header3 = 3
    Header4 = 4
    Power = 5
    ClimateAndISee = 6
    Temperature = 7
    ClimateAndHorizontalVanne = 8
    FanAndVerticalVanne = 9
    Clock = 10
    EndTime = 11
    StartTime = 12
    TimeControlAndArea = 13
    Unused14 = 14
    PowerfulMode = 15
    Unused16 = 16
    CRC = 17


class Constants:
    """
    Constants
    """
    Frequency = 38000  # 38khz
    MinTemp = 16
    MaxTemp = 31
    MaxMask = 0xFF
    NbBytes = 18
    NbPackets = 2
    # For Mitsubishi IR protocol we have to send two time the packet data


class Mitsubishi:
    """
    Mitsubishi
    """
    def power_off(self):
        """
        power_off
        """
        return self.__send_command(
            ClimateMode.Auto,
            21,
            FanMode.Auto,
            VanneVerticalMode.Auto,
            VanneHorizontalMode.Swing,
            ISeeMode.ISeeOff,
            AreaMode.NotSet,
            None,
            None,
            PowerfulMode.PowerfulOff,
            PowerMode.PowerOff,
        )

    def send_command(
        self,
        climate_mode=ClimateMode.Auto,
        temperature=21,
        fan_mode=FanMode.Auto,
        vanne_vertical_mode=VanneVerticalMode.Auto,
        vanne_horizontal_mode=VanneHorizontalMode.NotSet,
        isee_mode=ISeeMode.ISeeOff,
        area_mode=AreaMode.NotSet,
        start_time=None,
        end_time=None,
        powerful=PowerfulMode.PowerfulOff,
    ):
        """
        send_command
        """
        return self.__send_command(
            climate_mode,
            temperature,
            fan_mode,
            vanne_vertical_mode,
            vanne_horizontal_mode,
            isee_mode,
            area_mode,
            start_time,
            end_time,
            powerful,
            PowerMode.PowerOn,
        )

    def __send_command(
        self,
        climate_mode,
        temperature,
        fan_mode,
        vanne_vertical_mode,
        vanne_horizontal_mode,
        isee_mode,
        area_mode,
        start_time,
        end_time,
        powerful,
        power_mode,
    ):

        sender = ir_sender.IrSender(
            dict(
                leading_pulse_duration=Delay.HdrMark,
                leading_gap_duration=Delay.HdrSpace,
                one_pulse_duration=Delay.BitMark,
                one_gap_duration=Delay.OneSpace,
                zero_pulse_duration=Delay.BitMark,
                zero_gap_duration=Delay.ZeroSpace,
                trailing_pulse_duration=Delay.RptMark,
                trailing_gap_duration=Delay.RptSpace,
            ),
        )

        # data array is a valid frame, only byte to be chnaged will be updated.
        data = [0x23, 0xCB, 0x26, 0x01, 0x00, 0x20,
                0x08, 0x06, 0x30, 0x45, 0x67, 0x00,
                0x00, 0x00, 0x10, 0x00, 0x00, 0x1F]

        data[Index.Power] = power_mode
        data[Index.ClimateAndISee] = climate_mode | isee_mode
        data[Index.Temperature] = (
            max(
                Constants.MinTemp,
                min(Constants.MaxTemp, temperature),
            ) - 16
        )
        data[Index.ClimateAndHorizontalVanne] = (
            ClimateMode.climate2(climate_mode) | vanne_horizontal_mode
        )
        data[Index.FanAndVerticalVanne] = fan_mode | vanne_vertical_mode

        now = datetime.today()
        data[Index.Clock] = (now.hour*6) + (now.minute//10)

        if end_time is None:
            data[Index.EndTime] = 0
        else:
            data[Index.EndTime] = (end_time.hour*6) + (end_time.minute//10)

        if start_time is None:
            data[Index.StartTime] = 0
        else:
            data[Index.StartTime] = (start_time.hour*6) + (start_time.minute//10)

        if end_time is not None and start_time is not None:
            time_control = TimeControlMode.ControlBoth
        elif end_time is not None:
            time_control = TimeControlMode.ControlEnd
        elif start_time is not None:
            time_control = TimeControlMode.ControlStart
        else:
            time_control = TimeControlMode.NoTimeControl
        data[Index.TimeControlAndArea] = time_control | area_mode 

        data[Index.PowerfulMode] = powerful

        # CRC is a simple bits addition
        # sum every bytes but the last one
        data[Index.CRC] = sum(data[:-1]) % (Constants.MaxMask + 1)

        return sender.send_data(
            data, Constants.MaxMask, True, Constants.NbPackets
        )
