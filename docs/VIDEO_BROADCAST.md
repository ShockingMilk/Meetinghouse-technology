# Video Broadcast Setup

## Equipment

- PTZ camera.
- PTZ camera physical remote.
- J5 Connect TX.
- J5 Connect RX.
- Broadcast host computer.
- Zoom.
- Optional OBS Studio.

## Physical signal path

PTZ camera
    -> J5 Connect TX
    -> wireless connection
    -> J5 Connect RX
    -> USB
    -> broadcast host

Verify the exact camera output interface and J5 model before
marking the connection as compatible.

## Camera presets

Presets are saved on the PTZ camera.

They are recalled using the camera's physical remote.

| Preset | Purpose |
| ---: | --- |
| 0 | Default / start and finish |
| 1 | Speaker / podium |
| 2 | Chorister |
| 3 | Choir wide |
| 4 | Unassigned |
| 5 | Unassigned |
| 6 | Unassigned |
| 7 | Unassigned |
| 8 | Unassigned |
| 9 | Unassigned |

The intended shot is not proof that a preset has been configured.
Verify each preset physically and update its inventory status.

## Direct Zoom workflow

1. Connect the receiver to the broadcast host.
2. Confirm the operating system recognizes the receiver.
3. Open Zoom.
4. Select the appropriate camera input.
5. Test the image.
6. Test audio separately.

## OBS workflow

1. Connect the receiver to the broadcast host.
2. Open OBS Studio.
3. Add the receiver as a video capture source.
4. Confirm the picture and framing.
5. Start OBS Virtual Camera.
6. Open Zoom.
7. Select OBS Virtual Camera.
8. Test the image and audio.

## Troubleshooting

If there is no picture:

- Check camera power.
- Check the camera-to-transmitter connection.
- Check transmitter and receiver power.
- Check the wireless link.
- Check receiver USB connection.
- Check whether the operating system recognizes the device.
- Check the selected Zoom or OBS camera source.

If the image is delayed or unstable:

- Check wireless signal conditions.
- Check USB connection and port.
- Check capture resolution and frame rate.
- Compare direct Zoom operation with OBS operation.

Record confirmed working configurations in the inventory.
