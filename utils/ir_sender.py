# Since both NEC and RC-5 protocols use the same method
# for generating waveform,
# it can be put in a separate class and called from both protocol's classes.
class WaveGenerator:
    def __init__(self):
        self.raw_codes = list()

    # Pull the specified output pin low
    def zero(self, duration):
        self.raw_codes.append(-duration)

    # Protocol-agnostic square wave generator
    def one(self, duration):
        self.raw_codes.append(duration)


# NEC protocol class
class NEC:
    def __init__(
        self,
        frequency=38000,
        duty_cycle=0.33,
        leading_pulse_duration=9000,
        leading_gap_duration=4500,
        one_pulse_duration=562,
        one_gap_duration=1686,
        zero_pulse_duration=562,
        zero_gap_duration=562,
        trailing_pulse_duration=562,
        trailing_gap_duration=0,
    ):
        self.wave_generator = WaveGenerator()
        self.frequency = frequency  # in Hz, 38000 per specification
        self.duty_cycle = duty_cycle  # duty cycle of high state pulse
        # Durations of high pulse and low "gap".
        # The NEC protocol defines pulse and gap lengths,
        # but we can never expect
        # that any given TV will follow the protocol specification.
        self.leading_pulse_duration = leading_pulse_duration
        # in microseconds, 9000 per specification
        self.leading_gap_duration = leading_gap_duration
        # in microseconds, 4500 per specification
        self.one_pulse_duration = one_pulse_duration
        # in microseconds, 562 per specification
        self.one_gap_duration = one_gap_duration
        # in microseconds, 1686 per specification
        self.zero_pulse_duration = zero_pulse_duration
        # in microseconds, 562 per specification
        self.zero_gap_duration = zero_gap_duration
        # in microseconds, 562 per specification
        self.trailing_pulse_duration = trailing_pulse_duration
        # trailing 562 microseconds pulse, some remotes send it, some don't
        self.trailing_gap_duration = trailing_gap_duration
        # trailing space

    # Send AGC burst before transmission
    def send_agc(self):
        self.wave_generator.one(self.leading_pulse_duration)
        self.wave_generator.zero(self.leading_gap_duration)

    # Trailing pulse is just a burst with the duration of standard pulse.
    def send_trailing_pulse(self):
        self.wave_generator.one(self.trailing_pulse_duration)
        if self.trailing_gap_duration > 0:
            self.wave_generator.zero(self.trailing_gap_duration)

    # This function is processing IR code.
    # Leaves room for possible manipulation
    # of the code before processing it.
    def process_code(self, ircode):
        if (
            (self.leading_pulse_duration > 0)
            or (self.leading_gap_duration > 0)
        ):
            self.send_agc()
        for i in ircode:
            if i == "0":
                self.zero()
            elif i == "1":
                self.one()
            else:
                return 1
        if self.trailing_pulse_duration > 0:
            self.send_trailing_pulse()
        return 0

    # Generate zero or one in NEC protocol
    # Zero is represented by a pulse and a gap of the same length
    def zero(self):
        self.wave_generator.one(self.zero_pulse_duration)
        self.wave_generator.zero(self.zero_gap_duration)

    # One is represented by a pulse and a gap three times longer than the pulse
    def one(self):
        self.wave_generator.one(self.one_pulse_duration)
        self.wave_generator.zero(self.one_gap_duration)


class IrSender:
    def __init__(self, protocol_config):
        self.protocol = NEC(**protocol_config)

    # send_code takes care of sending the processed IR code to pigpio.
    # IR code itself is processed and converted to
    # pigpio structs by protocol's classes.
    def send_code(self, ircode, nb=1):
        for _ in range(0, nb):
            code = self.protocol.process_code(ircode)
            if code != 0:
                return 1
        return self.protocol.wave_generator.raw_codes

    def send_data(self, data, max_mask, must_invert, nb=1):
        code = []
        # Send all Bits from Byte Data in Reverse Order
        for i in range(0, len(data)):
            idx = i if must_invert else (len(data) - i - 1)
            mask = 1
            while max_mask > mask > 0:
                if must_invert:
                    if data[idx] & mask:
                        code = code + ["1"]
                    else:
                        code = code + ["0"]
                else:
                    if data[idx] & mask:
                        code = ["1"] + code
                    else:
                        code = ["0"] + code
                mask = mask << 1
        return self.send_code("".join(code), nb)
