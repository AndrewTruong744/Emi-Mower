use emi_mower_stm32::{
    CanCommandFrame, CommandReceiver, FrameError, MotorCommand, SkidSteerConfig, SkidSteerMixer,
};

#[test]
fn can_frame_round_trips_and_rejects_corruption() {
    let command = CanCommandFrame::new(true, 42, 800, -300);
    let bytes = command.encode();
    assert_eq!(CanCommandFrame::decode(&bytes), Ok(command));

    let mut corrupted = bytes;
    corrupted[4] ^= 1;
    assert_eq!(
        CanCommandFrame::decode(&corrupted),
        Err(FrameError::BadChecksum)
    );
}

#[test]
fn watchdog_and_sequence_protection_always_fail_safe() {
    let mut receiver = CommandReceiver::new(200);
    let first = CanCommandFrame::new(true, 255, 500, 0);
    receiver.accept(first, 10).unwrap();
    assert_eq!(receiver.command_at(210), first);
    assert_eq!(receiver.command_at(211), CanCommandFrame::STOP);

    receiver
        .accept(CanCommandFrame::new(true, 0, 500, 0), 220)
        .unwrap();
    assert_eq!(
        receiver.accept(CanCommandFrame::new(true, 255, 500, 0), 221),
        Err(FrameError::StaleSequence)
    );
}

#[test]
fn skid_steer_mixer_handles_turning_and_saturation() {
    let mixer = SkidSteerMixer::new(SkidSteerConfig {
        track_width_mm: 500,
        max_wheel_speed_mm_s: 1_000,
        max_duty: 1_000,
    });
    assert_eq!(
        mixer.mix(CanCommandFrame::new(true, 1, 500, 1_000)),
        MotorCommand {
            left: 250,
            right: 750
        }
    );
    assert_eq!(
        mixer.mix(CanCommandFrame::new(true, 2, 4_000, 0)),
        MotorCommand {
            left: 1_000,
            right: 1_000
        }
    );
    assert_eq!(mixer.mix(CanCommandFrame::STOP), MotorCommand::STOP);
}
