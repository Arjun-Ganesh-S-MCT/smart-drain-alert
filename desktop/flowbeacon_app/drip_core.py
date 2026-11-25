"""Drip's offline assistant: port of src/drip-core.js (English only for now)."""
import random
import re

LINES = {
    "curious": "Flow is lower than normal at {d}. Keep watching.",
    "worried": "Blockage warning at {d}: flow is falling while the level rises. Inspect the drain.",
    "alarmed": "Overflow risk at {d}. Check the drain now.",
    "panic": "Overflow detected at {d}. Act now.",
    "sleep": "No data. Waiting for the board.",
    "think": "Calibrating. Keep the flow steady.",
    "dizzy": "A sensor reading looks wrong. Check the wiring.",
}
TIPS = [
    "Plastic and silt are the top causes of clogged drains.",
    "A drain can lose half its flow before anyone notices.",
    "Flow falling while the level rises is the classic blockage sign.",
    "The rain plate only knows wet or dry. It cannot measure how hard it rains.",
    "Turbidity is cloudiness. More particles in the water means a higher reading.",
    "Clearing drains before the monsoon prevents most street flooding.",
]
HELP = ("Ask me: status, why, when will it overflow, or what turbidity, flow, the water level, calibration or SMS mean. "
        "I can also set the baseline, start the demo, mute or acknowledge an alarm.")
GREET = ["Hi, I am Drip!", "Watching your drain.", "Tap me any time.", "Need a hand?"]


def line(state, drain=None):
    t = LINES.get(state)
    return t.replace("{d}", drain or "the drain") if t else ""


def reply(text, ctx):
    """ctx: worst, cause, evid, pred, nodes=[(name, text)] (only nodes with live data). Returns (text, action)."""
    t = str(text).lower().strip()
    if not t:
        return "Ask me something. Try: help", None
    def has(p): return re.search(p, t) is not None
    if has(r"\bbaseline\b"): return "Setting the baseline. Keep the flow normal for a few seconds.", "baseline"
    if has(r"\bdemo\b"): return "Starting or stopping the demo.", "demo"
    if has(r"\b(unmute|sound on)\b"): return "Sound is on.", "unmute"
    if has(r"\b(mute|silence)\b") and not has("alarm"): return "Sound is off.", "mute"
    if has(r"\b(acknowledge|ack|silence alarm|stop (the )?alarm)\b"): return "Alarm acknowledged.", "ack"
    if has(r"how are you|are you ok|systems"):
        return ("Something needs attention. Ask me for the status." if ctx.get("worst", 0) >= 2
                else "All systems are running. Nothing needs attention."), None
    if has(r"\b(status|drains?|how is|how are the|condition)\b") and not has(r"what is|what are"):
        live = ctx.get("nodes") or []
        if not live:
            return "No readings yet. Connect the board or try the demo.", None
        return ". ".join("%s: %s" % n for n in live) + ".", None
    if has(r"\b(why|cause|reason)\b"):
        c = ctx.get("cause")
        if c and c != "No fault indicated":
            return c + (". Evidence: " + ctx["evid"] if ctx.get("evid") else "") + ".", None
        return "Nothing is wrong right now.", None
    if has(r"(when|will).*(overflow|flood|full)|predict|\beta\b"):
        return ctx.get("pred") or "No overflow is predicted right now.", None
    if has(r"turbidity|cloudy"): return "Turbidity is how cloudy the water is. More silt or mud gives a higher reading, which can support a blockage estimate.", None
    if has(r"ultrasonic|distance|level|probe|sensor"): return "The water level sensor has five probes at different heights, each with a transistor. The level is how many probes are wet, from 0 to 5. More wet probes means higher water.", None
    if has(r"\bflow\b"): return "The flow sensor counts pulses. Flow falling while the water level rises is the classic blockage sign.", None
    if has(r"calibrat"): return "Calibration teaches the app what normal looks like. Use the wizard under Calibration, then tune the dials.", None
    if has(r"\b(sms|text message)\b"): return "SMS needs a GSM module on the board. Add your number and press Send test SMS.", None
    if has(r"wi-?fi|usb|cable|connect"): return "The Arduino Nano connects with a USB cable. Pick its port under Connection and press Connect.", None
    if has(r"\brain\b"): return "The rain plate only knows wet or dry. It cannot measure how hard it rains.", None
    if has(r"\btip\b|\bfact\b|did you know"): return random.choice(TIPS), None
    if has(r"who are you|your name|about you|what are you"): return "I am Drip, the FlowBeacon assistant. I watch your drains and tell you what changes.", None
    if has(r"thank|thanks|nandri"): return "You are welcome.", None
    if has(r"(^|\b)(hi|hello|hey|vanakkam)\b"): return "Hello. Ask me for the status any time.", None
    if has(r"help|what can you do|commands"): return HELP, None
    return "I did not understand that. Try: status, why, tip or help.", None
