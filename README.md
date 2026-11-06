# Poetry Camera Project

This project aims to create a functional Poetry Camera with a Raspberry Pi, featuring:

1. **Network Setup**: Temporary hotspot creation to configure WiFi network.
2. **Poetry Camera**: Scripts and resources to capture images and generate poetry.
3. **Printer Integration**: Support for various printers to print status messages and generated poetry.

## Components
- **Network Setup**: Tools and scripts to manage WiFi configuration.
- **Poetry Camera**: Code and resources for the poetry generation feature.
- **Printer**: Management scripts for different printer types.
- **Capabilities**: `GET /api/capabilities` (propkit 1.25.0) lists what the camera can and cannot do; edit `web_interface/capabilities.py` when a feature is added, and `tests/test_capabilities.py` checks the list against the code.

## Setup
Instructions for setting up the entire project, including virtual environments and dependencies.

## License
MIT License
