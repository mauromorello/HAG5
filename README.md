# HAGhost5 - Home Assistant Integration for Flying Bear Ghost 5

HAGhost5 is a custom integration for [Home Assistant](https://www.home-assistant.io/) that brings the Flying Bear Ghost 5 3D printer into your smart home. This integration is designed for printers running the custom firmware developed by [Renzo Mischianti](https://www.mischianti.org/), enabling monitoring capabilities.

---

## Disclaimer

The project is currently in **beta** and is under active testing. Users are advised to use it at their own risk. The author does not take responsibility for any potential issues, including but not limited to malfunctioning of the printer, Home Assistant, or any related systems.

⚠️ **Warning:** Manual commands sent to the printer through this integration can damage your printer if used improperly. Proceed with caution and consult your printer's documentation.

---

## Features

### 1. **Printer Monitoring**
- Adds sensors to track important parameters during a 3D print, such as:
  - Print progress.
  - Temperature of the hotend and bed.
  - Printer status (idle, printing, error).
  - Remaining time for print completion.

### 2. **3D Print Visualization**
- Includes a **custom card** that uses [Three.js](https://threejs.org/) to provide a live visualization of the ongoing print.
- Visualize the G-code layer by layer in 3D as the print progresses.

### 3. **HAG5 Operations Card**
- A new **custom card** called `HAG5 Operations` provides a unified interface for interacting with the printer:
  - **Uploader Section:** Upload G-code files directly to the printer.
  - **File List Section:** View and manage files stored on the printer.
  - **Debug Section:** Send WebSocket commands manually and view logs.
  - **Command Section:** Send predefined commands to the printer.

---

## Installation

### Using HACS (Recommended)
1. Add this repository to your [HACS](https://hacs.xyz/) custom repositories.
2. Search for "HAGhost5" and install it.
3. Restart Home Assistant after installation.

### Manual Installation
1. Download the repository as a ZIP file and extract it.
2. Copy the `haghost5` folder into your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

---

## Configuration

### 1. **Add the Integration**
- Go to **Settings → Devices & Services → Add Integration**.
- Search for "HAGhost5" and follow the on-screen instructions.

### 2. **Enable the Custom Cards**
- Add the following resource paths in **Settings → Dashboards → Resources**:
  - `/local/community/haghost5/hag5-renderer-card/hag5-renderer-card.js`
  - `/local/community/haghost5/hag5-operations-card/hag5-operations-card.js`

### 3. **Configure the Operations Card**
- To enable the operations card, include it in your Lovelace dashboard configuration:
  ```yaml
  type: custom:hag5-operations-card
  uploader: true
  filelist: true
  debug: true
  command: true
  ```
- Set the parameters `uploader`, `filelist`, `debug`, and `command` to `true` or `false` depending on the sections you want to enable.

---

## Links and Resources

- Flying Bear Ghost 5 Firmware: [Renzo Mischianti](https://www.mischianti.org/)
- Home Assistant: [home-assistant.io](https://www.home-assistant.io/)
- Three.js: [threejs.org](https://threejs.org/)
- GitHub Repository: [HAGhost5](https://github.com/mauromorello/HAG5)

---

## Contribution

Contributions are welcome! Feel free to open issues or submit pull requests to improve this integration.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
