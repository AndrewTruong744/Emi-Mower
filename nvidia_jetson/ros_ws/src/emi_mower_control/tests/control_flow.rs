use emi_mower_control::{CommandWatchdog, ControlError, Stm32CommandFrame, VelocityCommand};
use std::time::{Duration, Instant};

#[test]
fn expired_ros_command_becomes_a_zero_command() {
    let start = Instant::now();
    let mut watchdog = CommandWatchdog::new(Duration::from_millis(200));
    let command = VelocityCommand {
        linear_mps: 0.8,
        angular_radps: -0.2,
    };
    watchdog.update(command, start);
    assert_eq!(
        watchdog.command_at(start + Duration::from_millis(199)),
        command
    );
    assert_eq!(
        watchdog.command_at(start + Duration::from_millis(201)),
        VelocityCommand::ZERO
    );
}

#[test]
fn can_frame_round_trips_and_rejects_corruption() {
    let frame = Stm32CommandFrame::from_velocity(
        42,
        true,
        VelocityCommand {
            linear_mps: 1.234,
            angular_radps: -0.567,
        },
    );
    let encoded = frame.encode();
    assert_eq!(Stm32CommandFrame::decode(&encoded).unwrap(), frame);

    let mut corrupted = encoded;
    corrupted[9] ^= 0x01;
    assert!(matches!(
        Stm32CommandFrame::decode(&corrupted),
        Err(ControlError::InvalidFrame)
    ));
}
