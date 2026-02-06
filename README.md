# RAM KVM AI 🤖

Autonomous computer control via Raspberry Pi + USB HID + HDMI Capture + AI Vision.

**Control any computer or smartphone like a human would — by looking at the screen and using keyboard/mouse.**

## How It Works

```
┌─────────────┐     HDMI      ┌─────────────┐
│   Target    │──────────────▶│  Capture    │
│  Computer   │               │   Card      │
│             │◀──────────────│             │
└─────────────┘   USB HID     └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │ Raspberry   │
                              │    Pi 5     │
                              │             │
                              │  ┌───────┐  │
                              │  │ Agent │  │──────▶ Vision API
                              │  └───────┘  │        (Claude/GPT-4V)
                              └─────────────┘
```

The agent operates like a human:
1. **Look** — Capture the screen via HDMI
2. **Think** — Send to vision model, analyze what to do
3. **Act** — Move mouse, click, type via USB HID
4. **Repeat** — Visual feedback loop until task is done

## Hardware Requirements

| Component | Description | Example |
|-----------|-------------|---------|
| Raspberry Pi 5 | Main controller | Pi 5 4GB/8GB |
| USB-C Data Cable | **Must support data** (not charge-only!) | Check it transfers files |
| HDMI Capture Card | USB 3.0 recommended | Generic 1080p capture |
| HDMI Cable | Connect target to capture card | Any HDMI cable |

### Important Notes

- The USB-C cable connects Pi to the target computer (Pi acts as keyboard/mouse)
- Most cheap USB-C cables are **charge-only** — test with file transfer first!
- Works with Mac, Windows, Linux, iPhone (with adapter), Android

## Software Setup

### 1. Configure Raspberry Pi

Edit `/boot/firmware/config.txt`, add under `[all]`:
```ini
dtoverlay=dwc2,dr_mode=peripheral
```

Edit `/boot/firmware/cmdline.txt`, add at the end:
```
modules-load=dwc2,libcomposite
```

Reboot the Pi.

### 2. Setup USB HID Gadget

```bash
sudo ./scripts/setup-hid-gadget.sh
```

This creates:
- `/dev/hidg0` — Keyboard
- `/dev/hidg1` — Mouse

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set API Key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

### Basic Task Execution

```bash
# Run a task
python src/agent.py "Send a message saying 'hello' to John on WhatsApp"

# Dry run (analyze only, no HID actions)
python src/agent.py --dry-run "Click the Settings icon"

# Verbose output
python src/agent.py -v "Open Chrome and go to google.com"
```

### Python API

```python
from src.agent import Agent, ClaudeVision
from src.hid import Keyboard, Mouse

# Setup
vision = ClaudeVision()
agent = Agent(vision=vision)

# Execute task with callback
def on_step(iteration, analysis, action):
    print(f"[{iteration}] {action}: {analysis.target_description}")

result = agent.execute_task(
    "Click the search bar and type 'hello world'",
    callback=on_step
)

print(f"Success: {result['success']}")
print(f"Iterations: {result['iterations']}")
```

### Manual Control

```python
from src.hid import Keyboard, Mouse

# Keyboard
kb = Keyboard()
kb.type_string("Hello World!")
kb.press_special('enter')
kb.hotkey('cmd', 'c')  # Cmd+C on Mac

# Mouse
mouse = Mouse()
mouse.move(50, 30)  # Relative movement
mouse.click()       # Left click
mouse.click('right')
```

### Screen Capture

```python
from src.capture import capture_frame, capture_frame_base64

# Save to file
path = capture_frame(output_path="screenshot.jpg")

# Get base64 for API
b64 = capture_frame_base64()
```

## Architecture

```
ram-kvm-ai/
├── src/
│   ├── agent.py      # Main agent with visual feedback loop
│   ├── capture.py    # HDMI capture module
│   └── hid.py        # USB HID keyboard/mouse control
├── scripts/
│   ├── setup-hid-gadget.sh    # Create USB HID devices
│   └── remove-hid-gadget.sh   # Remove USB HID devices
├── requirements.txt
└── README.md
```

## Visual Feedback Loop

Unlike coordinate-based automation, RAM KVM AI uses **visual feedback** like a human:

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│   │ Capture │───▶│ Analyze │───▶│ Execute │   │
│   │  Screen │    │  (AI)   │    │  Action │   │
│   └─────────┘    └─────────┘    └────┬────┘   │
│        ▲                             │         │
│        │                             │         │
│        └─────────────────────────────┘         │
│              (repeat until done)               │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ No coordinate calibration needed
- ✅ Works at any resolution/scale
- ✅ Self-correcting
- ✅ Handles UI changes gracefully

**Trade-offs:**
- ⏱️ Slower (~2-5s per action)
- 💰 Uses API calls (vision model)

## Supported Targets

| Target | USB HID | HDMI Capture | Notes |
|--------|---------|--------------|-------|
| Mac | ✅ | ✅ | Works great |
| Windows | ✅ | ✅ | Works great |
| Linux | ✅ | ✅ | Works great |
| iPhone | ✅ | ✅ | Needs Lightning/USB-C adapter for both |
| Android | ✅ | ✅ | Needs USB-C OTG + HDMI adapter |

## Troubleshooting

### "not attached" or HID blocked

- Check USB-C cable supports data (not charge-only)
- Ensure cable is in the **PWR** USB-C port on Pi
- Try a different cable

### No HDMI signal

- Check HDMI cable is connected
- Ensure target is outputting video (not just mirroring disabled)
- Try different resolution on target

### Vision API errors

- Verify API key is set: `echo $ANTHROPIC_API_KEY`
- Check API quota/billing

## License

**Dual Licensed:**

| Use Case | License | Cost |
|----------|---------|------|
| Personal, Educational, Open Source | AGPL-3.0 | Free |
| Commercial, Closed-source | [Commercial License](https://idiogo.gumroad.com/l/skynetpi) | $999 |

**The commercial license covers the entire SkynetPi project**, including:
- [skynetpi-bootstrap](https://github.com/idiogo/skynetpi-bootstrap) (setup + config)
- ram-kvm-ai (this repo)

🛒 **Purchase:** [idiogo.gumroad.com/l/skynetpi](https://idiogo.gumroad.com/l/skynetpi)
📧 **Questions:** skynetpi-commercial@idiogo.com.br

## Credits

Created by [Diogo Carneiro](https://github.com/diogocarneiro) with assistance from SkynetPi 🤖
