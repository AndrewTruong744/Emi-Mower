use emi_mower_control::{
    joystick_key, joystick_to_velocity, parse_joystick_payload, CommandWatchdog, ControlError,
    Stm32CommandFrame, VelocityCommand,
};
use std::time::{Duration, Instant};

#[test]
fn app_payload_maps_to_the_ros_velocity_convention() {
    let joystick = parse_joystick_payload(br#"{"x":0.5,"y":-0.25}"#).unwrap();
    assert_eq!(joystick_key("mower-01").unwrap(), "mower/mower-01/joystick");
    assert_eq!(
        joystick_to_velocity(joystick, 2.0, 1.5),
        VelocityCommand {
            linear_mps: -0.5,
            angular_radps: 0.75,
        }
    );
}

#[test]
fn malformed_or_out_of_range_app_input_is_rejected() {
    assert!(matches!(
        parse_joystick_payload(br#"{"x":1.1,"y":0.0}"#),
        Err(ControlError::InvalidAxis { axis: "x", .. })
    ));
    assert!(matches!(
        parse_joystick_payload(br#"{"x":0.0,"y":0.0,"extra":true}"#),
        Err(ControlError::InvalidJson(_))
    ));
    assert!(matches!(
        joystick_key("mower/01"),
        Err(ControlError::InvalidMowerId)
    ));
}

#[test]
fn expired_ros_command_becomes_a_zero_command() {
    let start = Instant::now();
    let mut watchdog = CommandWatchdog::new(Duration::from_millis(200));
    let command = VelocityCommand {
        linear_mps: 0.8,
        angular_radps: -0.2,
    };
    watchdog.update(command, start);
    assert_eq!(watchdog.command_at(start + Duration::from_millis(199)), command);
    assert_eq!(watchdog.command_at(start + Duration::from_millis(201)), VelocityCommand::ZERO);
}

#[test]
fn uart_frame_round_trips_and_rejects_corruption() {
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
