#![no_std]
#![no_main]

//! NUCLEO-F446RE CAN teleoperation firmware.
//!
//! CAN1 RX/TX: PB8/PB9 (AF9), connected to an external 3.3 V CAN transceiver.
//! Left H-bridge: PWM PA6/TIM3_CH1, direction PB0/PB1.
//! Right H-bridge: PWM PB6/TIM4_CH1, direction PB4/PB5.
//!
//! Direction polarity and the conservative defaults in `SkidSteerConfig` must
//! be verified on blocks before connecting traction motors.

use embassy_executor::Spawner;
use embassy_stm32::bind_interrupts;
use embassy_stm32::can::filter::Mask32;
use embassy_stm32::can::{
    Can, Fifo, Rx0InterruptHandler, Rx1InterruptHandler, SceInterruptHandler, StandardId,
    TxInterruptHandler,
};
use embassy_stm32::gpio::{Level, Output, OutputType, Speed};
use embassy_stm32::peripherals::CAN1;
use embassy_stm32::time::khz;
use embassy_stm32::timer::simple_pwm::{PwmPin, SimplePwm};
use embassy_time::{Duration, Instant, with_timeout};
use emi_mower_stm32::{
    CAN_COMMAND_ID, CanCommandFrame, CommandReceiver, SkidSteerConfig, SkidSteerMixer,
};
use panic_halt as _;

/// Makes direction changes safe by first forcing PWM off, then applying the
/// H-bridge direction, and finally restoring the requested duty.
macro_rules! apply_motor {
    ($pwm:expr, $forward:expr, $reverse:expr, $command:expr) => {{
        let command = $command;
        $pwm.set_duty_cycle_fully_off();
        if command > 0 {
            $forward.set_high();
            $reverse.set_low();
        } else if command < 0 {
            $forward.set_low();
            $reverse.set_high();
        } else {
            $forward.set_low();
            $reverse.set_low();
        }
        let duty = u32::from(command.unsigned_abs()) * $pwm.max_duty_cycle() / 1_000;
        $pwm.set_duty_cycle(duty);
    }};
}

const CAN_BITRATE: u32 = 500_000;
const CONTROL_PERIOD_MS: u64 = 10;

bind_interrupts!(struct Irqs {
    CAN1_TX => TxInterruptHandler<CAN1>;
    CAN1_RX0 => Rx0InterruptHandler<CAN1>;
    CAN1_RX1 => Rx1InterruptHandler<CAN1>;
    CAN1_SCE => SceInterruptHandler<CAN1>;
});

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    let p = embassy_stm32::init(Default::default());

    let mut can = Can::new(p.CAN1, p.PB8, p.PB9, Irqs);
    let command_id = StandardId::new(CAN_COMMAND_ID).unwrap();
    let mut command_filter = Mask32::frames_with_std_id(command_id, StandardId::MAX);
    command_filter.data_frames_only();
    can.modify_filters()
        .enable_bank(0, Fifo::Fifo0, command_filter);
    can.modify_config().set_bitrate(CAN_BITRATE);
    can.enable().await;

    let left_pwm_pin = PwmPin::new(p.PA6, OutputType::PushPull);
    let mut left_pwm = SimplePwm::new(
        p.TIM3,
        Some(left_pwm_pin),
        None,
        None,
        None,
        khz(20),
        Default::default(),
    );
    let mut left_pwm = left_pwm.ch1();
    left_pwm.enable();

    let right_pwm_pin = PwmPin::new(p.PB6, OutputType::PushPull);
    let mut right_pwm = SimplePwm::new(
        p.TIM4,
        Some(right_pwm_pin),
        None,
        None,
        None,
        khz(20),
        Default::default(),
    );
    let mut right_pwm = right_pwm.ch1();
    right_pwm.enable();

    let mut left_forward = Output::new(p.PB0, Level::Low, Speed::Low);
    let mut left_reverse = Output::new(p.PB1, Level::Low, Speed::Low);
    let mut right_forward = Output::new(p.PB4, Level::Low, Speed::Low);
    let mut right_reverse = Output::new(p.PB5, Level::Low, Speed::Low);

    let mixer = SkidSteerMixer::new(SkidSteerConfig::default());
    let mut receiver = CommandReceiver::with_default_timeout();

    loop {
        let now_ms = Instant::now().as_millis() as u32;
        if let Ok(Ok(envelope)) =
            with_timeout(Duration::from_millis(CONTROL_PERIOD_MS), can.read()).await
        {
            if let Ok(command) = CanCommandFrame::decode(envelope.frame.data()) {
                // Malformed/replayed frames never refresh the MCU watchdog.
                let _ = receiver.accept(command, now_ms);
            }
        }

        let motor_command = mixer.mix(receiver.command_at(Instant::now().as_millis() as u32));
        apply_motor!(left_pwm, left_forward, left_reverse, motor_command.left);
        apply_motor!(right_pwm, right_forward, right_reverse, motor_command.right);
    }
}
