"""Drip sprite layout (from the original UI): size in px of each layer image and its placement on the 174x216 body."""
BODY = (174, 216)
SIZE = {'arm_left': (70, 163), 'arm_right': (69, 163), 'arm_up': (100, 175), 'arm_wave': (131, 126), 'body': (174, 216), 'brows_angry': (147, 46), 'brows_up': (155, 51), 'brows_worried': (192, 37), 'eyes_closed': (190, 39), 'eyes_open': (196, 87), 'hardhat': (125, 93), 'mouth_open': (56, 43), 'mouth_scream': (87, 61), 'mouth_sleep': (93, 21), 'mouth_smile': (58, 25), 'mouth_worried': (79, 31), 'pupil_l': (44, 44), 'pupil_r': (41, 44), 'stars': (96, 94), 'sweat_drop': (67, 91), 'tick': (89, 73), 'umbrella': (105, 94), 'zzz': (120, 94)}
POS = {'eyes_open': (50, 57, 54), 'eyes_closed': (50, 58, 52), 'brows_up': (50, 41, 50), 'brows_angry': (50, 43, 46), 'brows_worried': (50, 42, 56), 'mouth_smile': (50, 72, 15), 'mouth_open': (50, 73, 13), 'mouth_worried': (50, 74, 18), 'mouth_scream': (50, 74, 22), 'mouth_sleep': (50, 73, 16), 'hardhat': (50, 6, 52), 'umbrella': (1.5, 23, 54), 'sweat_drop': (82, 44, 12), 'zzz': (88, -4, 34), 'stars': (50, -6, 56), 'tick': (92, 18, 26), 'pupil_l': (35, 58, 9.5), 'pupil_r': (65, 58, 9.5), 'arm_left': (-1, 66, 21), 'arm_right': (101, 66, 21), 'arm_wave': (104, 50, 38), 'arm_up': (101, 52, 29), 'arm_up2': (-1, 52, 29)}

# expression -> (eyes, brows, mouth, left arm, right arm, extras, animation)
EX = {
    "idle": ("o", None, "mouth_smile", "arm_left", "arm_right", [], "float"),
    "wave": ("o", "brows_up", "mouth_open", "arm_left", "arm_wave", [], "float"),
    "happy": ("c", None, "mouth_open", "arm_up2", "arm_up", [], "bounce"),
    "curious": ("o", "brows_up", "mouth_smile", "arm_left", "arm_right", [], "tilt"),
    "worried": ("o", "brows_worried", "mouth_worried", "arm_left", "arm_right", ["sweat_drop"], "shiver"),
    "alarmed": ("o", "brows_up", "mouth_open", "arm_up2", "arm_up", ["hardhat"], "hop"),
    "panic": ("o", "brows_worried", "mouth_scream", "arm_up2", "arm_up", ["hardhat", "sweat_drop"], "shake"),
    "think": ("o", None, "mouth_sleep", "arm_left", "arm_right", [], "float"),
    "sleep": ("c", None, "mouth_sleep", "arm_left", "arm_right", ["zzz"], "sleep"),
    "dizzy": ("o", "brows_worried", "mouth_worried", "arm_left", "arm_right", ["stars"], "tilt"),
    "cheer": ("c", "brows_up", "mouth_open", "arm_up2", "arm_up", ["tick"], "bounce"),
}
MSG = {
    "curious": "Hmm, flow looks lower than usual.",
    "worried": "Blockage warning! Flow is dropping while the level rises.",
    "alarmed": "Overflow risk! Please check the drain.",
    "panic": "OVERFLOW! Water has reached the limit!",
    "sleep": "Zzz... waiting for the board.",
    "think": "Calibrating. Keep the flow steady.",
    "dizzy": "A sensor looks faulty. Check the wiring.",
}
