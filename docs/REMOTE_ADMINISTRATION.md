# Remote Administration

## System roles

### Development workstation

The Linux workstation is the development and testing system.

It is used for:

- VS Code development.
- Git operations.
- Docker-based website testing.
- Documentation.
- Troubleshooting.
- Preparing deployments.

### Broadcast host

The broadcast host runs the camera feed and Zoom meeting.

It is separate from the development workstation.

## SSH

Use SSH for command-line administration.

Typical tasks:

- Checking system status.
- Viewing logs.
- Checking connected USB devices.
- Checking camera receiver recognition.
- Updating approved software.
- Managing services.

Use individual authorized accounts.

Prefer SSH keys over password authentication where supported.

Do not store private keys or passwords in the project repository.

## XRDP or VNC

Use a remote desktop tool when a graphical interface is necessary.

Examples:

- Opening OBS Studio.
- Checking video capture devices.
- Configuring Zoom.
- Checking desktop notifications.
- Troubleshooting graphical applications.

Remote desktop access should be restricted to authorized users
and the approved local network.

## Operational separation

The development workstation should not be assumed to be the
broadcast host.

The broadcast host should not be used as the primary development
environment.

## Meeting-day considerations

Before the meeting:

1. Confirm the broadcast host is powered on.
2. Confirm the camera and wireless transmitter/receiver are connected.
3. Confirm the receiver is recognized by the host.
4. Confirm the intended camera framing presets work using the
   physical remote.
5. Confirm Zoom receives the correct camera feed.
6. If using OBS, confirm the OBS Virtual Camera is running.
7. Test audio and video before the meeting begins.

Avoid unnecessary system updates, reboots, or configuration changes
during a meeting.
