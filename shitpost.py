import json
import time
import subprocess
bounce_decay = 0.7
gravity = 2
flick_friction = 0.3
floor_friction = 0.85
user_move_tolerance_x = 100
user_move_tolerance_y = 500  # keep this value lower than x value

# tolerance basically how many pixels should the mouse moves
# before it is defined as a throw
window_state = {}
while True:  # mccabe Cycolmatic complexity too high warning here
    sus = subprocess.run(["bspc", "query", "-N", "-n", ".floating"],
                         capture_output=True,
                         text=True).stdout.strip().splitlines()

    for wid in sus:
        data = subprocess.run(["bspc", "query", "-T", "-n", wid],
                              capture_output=True, text=True)
        try:
            node = json.loads(data.stdout)
        except json.JSONDecodeError:
            continue
        rect = node["client"]["floatingRectangle"]
        x = int(rect["x"])
        y = int(rect["y"])
        w = int(rect["width"])
        h = int(rect["height"])

        if wid not in window_state:
            window_state[wid] = {
                "velocity": 0, "direction": 1,
                "h_velocity": 0, "h_direction": 1,
                "last_x": x, "last_y": y,
            }

        last_x = window_state[wid]['last_x']
        last_y = window_state[wid]['last_y']

        real_dx = x - last_x
        real_dy = y - last_y

        script_h_step = int(
            window_state[wid]["h_velocity"] * window_state[wid]["h_direction"])
        script_step = int(
            window_state[wid]["velocity"] * window_state[wid]["direction"])

        user_intervened = abs(real_dx - script_h_step) > user_move_tolerance_x or abs(
            real_dy - script_step) > user_move_tolerance_y

        if user_intervened:
            window_state[wid]['h_velocity'] = abs(real_dx * flick_friction)
            window_state[wid]['h_direction'] = 1 if real_dx >= 0 else -1
            window_state[wid]['velocity'] = abs(real_dy * flick_friction)
            window_state[wid]['direction'] = 1 if real_dy >= 0 else -1

        window_state[wid]['last_x'] = x
        window_state[wid]['last_y'] = y

        is_on_floor = (y + h) >= 768

        if is_on_floor and window_state[wid]["direction"] == 1 and not user_intervened:
            overshoot = (y + h) - 768
            subprocess.run(["bspc", "node", wid, "-v", "0", str(-overshoot)])
            y -= overshoot

            incoming_velocity = window_state[wid]["velocity"]
            if incoming_velocity > gravity * 1.5:
                window_state[wid]["direction"] = -1
                window_state[wid]["velocity"] = int(
                    incoming_velocity * bounce_decay)
                window_state[wid]["h_velocity"] = int(
                    window_state[wid]['h_velocity'] * bounce_decay)
            else:
                window_state[wid]["velocity"] = 0
        if y < 0 and window_state[wid]["direction"] == -1 and not user_intervened:
            subprocess.run(["bspc", "node", wid, "-v", "0", str(-y)])
            y = 0
            window_state[wid]["direction"] = 1
            window_state[wid]["velocity"] = 1
        if (x + w) > 1366 and window_state[wid]["h_direction"] == 1 and not user_intervened:
            overshoot = (x + w) - 1366
            subprocess.run(["bspc", "node", wid, "-v", str(-overshoot), "0"])
            x -= overshoot
            window_state[wid]["h_direction"] = -1
            window_state[wid]["h_velocity"] = int(
                window_state[wid]["h_velocity"] * bounce_decay)

        if x < 0 and window_state[wid]["h_direction"] == -1 and not user_intervened:
            subprocess.run(["bspc", "node", wid, "-v", str(-x), "0"])
            x = 0
            window_state[wid]["h_direction"] = 1
            window_state[wid]["h_velocity"] = int(
                window_state[wid]["h_velocity"] * bounce_decay)

        is_at_rest = window_state[wid]["velocity"] == 0

        if is_on_floor and is_at_rest and window_state[wid]['h_velocity'] > 0:
            window_state[wid]['h_velocity'] = int(
                window_state[wid]['h_velocity'] * floor_friction)
        if not (is_on_floor and is_at_rest):
            if window_state[wid]["direction"] == 1:
                window_state[wid]["velocity"] += gravity
            else:
                window_state[wid]["velocity"] -= gravity

        if window_state[wid]["direction"] == -1 and window_state[wid]["velocity"] < 0:
            window_state[wid]["direction"] = 1
            window_state[wid]["velocity"] = 1

        if window_state[wid]["h_velocity"] < 1:
            window_state[wid]["h_velocity"] = 0
        velocity = window_state[wid]["velocity"]
        direction = window_state[wid]["direction"]
        h_velocity = window_state[wid]["h_velocity"]
        h_direction = window_state[wid]["h_direction"]

        step = int(velocity * direction)
        h_step = int(h_velocity * h_direction)

        subprocess.run(["bspc", "node", wid, "-v", str(h_step), str(step)])

    time.sleep(0.01)
