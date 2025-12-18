#!/usr/bin/env python3
import argparse
import os
import sys
import csv
import time
import pickle

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation


def _import_ati_module():
    try:
        import ati_netft_pybind as ati  # type: ignore

        return ati
    except ImportError:
        pass

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "..", "hardware", "ati_netft", "python"),
        os.path.join(script_dir, "..", "build", "hardware", "ati_netft", "python"),
    ]
    for module_dir in candidates:
        module_dir = os.path.abspath(module_dir)
        if os.path.isdir(module_dir):
            sys.path.insert(0, module_dir)
            break
    import ati_netft_pybind as ati  # type: ignore

    return ati


def _build_config(ati, args):
    cfg = ati.ATINetftConfig()
    cfg.ip_address = args.ip
    cfg.counts_per_force = args.counts_per_force
    cfg.counts_per_torque = args.counts_per_torque
    cfg.sensor_name = "netft"
    cfg.fullpath = ""
    cfg.print_flag = False
    cfg.publish_rate = args.publish_rate
    cfg.noise_level = args.noise_level
    cfg.stall_threshold = args.stall_threshold
    cfg.Foffset = np.zeros(3)
    cfg.Toffset = np.zeros(3)
    cfg.Gravity = np.zeros(3)
    cfg.Pcom = np.zeros(3)
    cfg.WrenchSafety = np.ones(6) * args.safety_limit
    cfg.PoseSensorTool = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    return cfg


def _wait_for_data(sensor):
    while not sensor.is_data_ready():
        print("Waiting for data...")
        time.sleep(0.05)


def _decode_control(raw):
    try:
        return pickle.loads(raw)
    except Exception:
        try:
            return raw.decode("utf-8").strip()
        except Exception:
            return None


def _wait_for_start_signal(args):
    import zmq

    context = zmq.Context.instance()
    socket = context.socket(zmq.PULL)
    address = f"tcp://{args.sync_host}:{args.sync_port}"
    socket.bind(address)
    print(f"Waiting for start signal on {address}...")

    direction = "z"
    poller = None
    end_time = None
    if args.sync_timeout > 0:
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        end_time = time.time() + args.sync_timeout

    while True:
        if poller is not None:
            remaining = end_time - time.time()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for start signal.")
            socks = dict(poller.poll(remaining * 1000))
            if socket not in socks:
                continue
        raw = socket.recv()
        payload = _decode_control(raw)
        if isinstance(payload, dict):
            new_direction = payload.get("direction")
            if new_direction:
                direction = str(new_direction).lower()
            if payload.get("start"):
                break
        elif isinstance(payload, str):
            if payload.lower().startswith("start"):
                break

    print("Received start signal.")
    return socket, direction


def _poll_direction(socket, direction_state):
    import zmq

    while True:
        try:
            raw = socket.recv(zmq.NOBLOCK)
        except zmq.Again:
            break
        payload = _decode_control(raw)
        if isinstance(payload, dict):
            new_direction = payload.get("direction")
            if new_direction:
                direction_state["value"] = str(new_direction).lower()


def _run_plot(sensor, args):
    plot_hz = args.plot_hz
    window_sec = args.window_sec
    dt = 1.0 / plot_hz
    num_samples = max(2, int(window_sec * plot_hz))
    x = np.linspace(-window_sec, 0.0, num_samples)

    force = np.zeros((num_samples, 3))
    torque = np.zeros((num_samples, 3))

    fig, (ax_f, ax_t) = plt.subplots(2, 1, sharex=True)
    ax_f.set_ylabel("Force (N)")
    ax_t.set_ylabel("Torque (Nm)")
    ax_t.set_xlabel("Time (s)")
    ax_f.grid(True, alpha=0.3)
    ax_t.grid(True, alpha=0.3)

    labels_f = ["Fx", "Fy", "Fz"]
    labels_t = ["Tx", "Ty", "Tz"]
    force_lines = [ax_f.plot(x, force[:, i], label=labels_f[i])[0] for i in range(3)]
    torque_lines = [ax_t.plot(x, torque[:, i], label=labels_t[i])[0] for i in range(3)]
    ax_f.legend(loc="upper left")
    ax_t.legend(loc="upper left")
    status_text = ax_f.text(0.02, 0.95, "", transform=ax_f.transAxes)

    def update(_frame):
        nonlocal force, torque
        status, wrench = sensor.get_wrench_sensor()
        if status == 0:
            wrench = np.asarray(wrench).reshape(-1)
            force = np.roll(force, -1, axis=0)
            torque = np.roll(torque, -1, axis=0)
            force[-1] = wrench[:3]
            torque[-1] = wrench[3:6]
            for i in range(3):
                force_lines[i].set_ydata(force[:, i])
                torque_lines[i].set_ydata(torque[:, i])
            f_min, f_max = float(np.min(force)), float(np.max(force))
            t_min, t_max = float(np.min(torque)), float(np.max(torque))
            f_pad = max(0.5, 0.05 * (f_max - f_min)) if f_max != f_min else 0.5
            t_pad = max(0.05, 0.05 * (t_max - t_min)) if t_max != t_min else 0.05
            ax_f.set_ylim(f_min - f_pad, f_max + f_pad)
            ax_t.set_ylim(t_min - t_pad, t_max + t_pad)
            status_text.set_text("")
        else:
            status_text.set_text(f"status: {status}")
        return force_lines + torque_lines + [status_text]

    anim = animation.FuncAnimation(fig, update, interval=dt * 1000.0, blit=False)
    plt.show()
    return anim


def _run_log(sensor, args):
    control_socket, direction = _wait_for_start_signal(args)
    direction_state = {"value": direction}
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    log_base, log_ext = os.path.splitext(args.log_path)
    log_path = f"{log_base}_{timestamp_str}{log_ext or '.csv'}"
    log_file = open(log_path, "w", newline="")
    try:
        log_writer = csv.writer(log_file)
        log_writer.writerow(
            ["timestamp", "fx", "fy", "fz", "tx", "ty", "tz", "status", "direction"]
        )
        dt = 1.0 / max(args.publish_rate, 1.0)
        print(f"Logging to {log_path}. Press Ctrl+C to stop.")
        while True:
            _poll_direction(control_socket, direction_state)
            status, wrench = sensor.get_wrench_sensor()
            timestamp = time.time()
            if status == 0:
                wrench = np.asarray(wrench).reshape(-1)
                log_writer.writerow(
                    [
                        timestamp,
                        wrench[0],
                        wrench[1],
                        wrench[2],
                        wrench[3],
                        wrench[4],
                        wrench[5],
                        status,
                        direction_state["value"],
                    ]
                )
                log_file.flush()
            time.sleep(dt)
    except KeyboardInterrupt:
        print("Logging stopped.")
    finally:
        log_file.close()


def main():
    parser = argparse.ArgumentParser(description="Plot ATI NetFT wrench data.")
    parser.add_argument("--ip", default="192.168.10.21", help="Sensor IP address.")
    parser.add_argument("--counts-per-force", type=float, default=1000000.0)
    parser.add_argument("--counts-per-torque", type=float, default=1000000.0)
    parser.add_argument("--publish-rate", type=float, default=200.0)
    parser.add_argument("--plot-hz", type=float, default=50.0)
    parser.add_argument("--window-sec", type=float, default=5.0)
    parser.add_argument("--safety-limit", type=float, default=1e6)
    parser.add_argument("--noise-level", type=float, default=0.0)
    parser.add_argument("--stall-threshold", type=int, default=50)
    parser.add_argument("--sync-host", default="0.0.0.0")
    parser.add_argument("--sync-port", type=int, default=5556)
    parser.add_argument("--sync-timeout", type=float, default=0.0)
    parser.add_argument("--log-path", default="outputs/ati_netft_log.csv")
    parser.add_argument("--plot", action="store_true", default=False)
    args = parser.parse_args()

    ati = _import_ati_module()
    sensor = ati.ATINetft()
    config = _build_config(ati, args)

    if not sensor.init(config):
        raise RuntimeError("Failed to initialize ATI NetFT sensor.")

    _wait_for_data(sensor)
    if args.plot:
        _run_plot(sensor, args)
    else:
        _run_log(sensor, args)


if __name__ == "__main__":
    main()
