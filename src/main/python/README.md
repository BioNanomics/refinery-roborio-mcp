# refinery-roborio-mcp (Python / RobotPy)

Pure Python implementation of the embedded MCP server for FRC robots running [RobotPy](https://robotpy.readthedocs.io/).

Identical functionality to the Java and C++ implementations — exposes robot status, match info, subsystem state, and NetworkTables browsing to AI assistants via HTTP JSON-RPC 2.0 on port 8765.

## Installation

```bash
pip install refinery-roborio-mcp
```

Or add to your `pyproject.toml` / `requirements.txt`:

```
refinery-roborio-mcp>=0.0.3
```

## Usage

In your `robot.py`:

```python
from refinery_roborio_mcp import RoboRioMcpServer

class MyRobot(wpilib.TimedRobot):
    def robotInit(self):
        # ... existing init code ...
        RoboRioMcpServer.start()        # default port 8765
        # RoboRioMcpServer.start(9000)  # or custom port
```

## Requirements

- Python >= 3.12
- RobotPy 2026.x (`robotpy-wpilib`, `pyntcore`, `robotpy-commands-v2`)
