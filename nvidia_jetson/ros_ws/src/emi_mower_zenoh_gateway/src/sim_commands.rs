//! Local simulation command state. Physical motor safety remains in the STM32.

use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Command {
    EmergencyStop { command_id: String },
    SetPower { command_id: String, enabled: bool },
    SetMode { command_id: String, mode: Mode },
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Manual,
    Auto,
}

#[derive(Debug, Serialize)]
pub struct CommandReply {
    pub command_id: String,
    pub status: &'static str,
    pub reason: Option<&'static str>,
}

#[derive(Default)]
pub struct SimCommandState {
    powered: bool,
    automatic: bool,
    stopped: bool,
}

impl SimCommandState {
    pub fn accepts_joystick(&self) -> bool {
        self.powered && !self.automatic && !self.stopped
    }

    /// Return a reply and whether the current motion should be stopped now.
    pub fn apply(&mut self, command: Command) -> (CommandReply, bool) {
        let command_id = match &command {
            Command::EmergencyStop { command_id }
            | Command::SetPower { command_id, .. }
            | Command::SetMode { command_id, .. } => command_id,
        };
        if command_id.is_empty() || command_id.len() > 128 {
            return (
                CommandReply {
                    command_id: command_id.clone(),
                    status: "rejected",
                    reason: Some("Invalid command ID"),
                },
                false,
            );
        }
        let (id, reason, stop_motion) = match command {
            Command::EmergencyStop { command_id } => {
                self.stopped = true;
                self.powered = false;
                (command_id, None, true)
            }
            Command::SetPower {
                command_id,
                enabled,
            } => {
                if enabled && self.stopped {
                    (command_id, Some("Emergency stop is latched"), false)
                } else {
                    self.powered = enabled;
                    (command_id, None, !enabled)
                }
            }
            Command::SetMode { command_id, mode } => {
                self.automatic = mode == Mode::Auto;
                (command_id, None, self.automatic)
            }
        };
        (
            CommandReply {
                command_id: id,
                status: if reason.is_some() {
                    "rejected"
                } else {
                    "accepted"
                },
                reason,
            },
            stop_motion && reason.is_none(),
        )
    }
}
