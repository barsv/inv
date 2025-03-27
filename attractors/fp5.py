# Hyperparameter optimization using modal.
import modal
from modal import Image
import numpy as np
import pandas as pd
import os
from itertools import islice

app = modal.App("hyperopt")

image = (
    Image.debian_slim()
    .pip_install("numpy")
    .pip_install("pandas")
    .add_local_dir("./data", remote_path="/root/data")
)

# load data
file_path = "./data/BTCUSD_1T_close_only.npz"
data = np.load(file_path, allow_pickle=True)
df = pd.DataFrame(data['data'], columns=['timestamp', 'close'])
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['close'] = df['close'].astype(float)
df.set_index('timestamp', inplace=True)

# prepere train data
train_size = 400 * 1000
dfc = df[:train_size].copy()
dfc['close'] = np.log(dfc['close']) - np.log(dfc['close'].iloc[0])

def get_positions(_windows, _diffs, _diff_mins, _diff_maxs, _grid_sizes, _i):
    positions = []
    for wi, w in islice(enumerate(_windows), 1, None):
        diff = _diffs[wi].iloc[_i]
        diff_min = _diff_mins[wi]
        diff_max = _diff_maxs[wi]
        grid_size = _grid_sizes[wi]
        # Avoid division by zero and ensure diff_max > diff_min
        if diff_max == diff_min:
            pos_fixed = 0
        else:
            pos = (grid_size - 1) * (diff - diff_min) / (diff_max - diff_min)
            pos_fixed = max(0, min(round(pos), grid_size - 1))  # Ensure position is within bounds
        positions.append(pos_fixed)
    return positions

def get_diffs(_df, _windows):
    closes = _df['close']
    mas = {}
    diffs = {}
    for wi, w in enumerate(_windows):
        mas[wi] = closes.rolling(w).mean() if w > 0 else closes
        if wi > 0:
            diffs[wi] = mas[wi] - mas[wi - 1]
    return diffs

def get_min_max_diffs(_diffs, _windows):
    diff_mins = [0]
    diff_maxs = [0]
    for wi, w in islice(enumerate(_windows), 1, None):
        diff_mins.append(_diffs[wi].min())
        diff_maxs.append(_diffs[wi].max())
    return diff_mins, diff_maxs

def get_transitions_map(_df, _windows, _tau, _grid_sizes, _transitions_grid_size):
    """
    creates a map of price shifts
    """
    diffs = get_diffs(_df, _windows)
    diff_mins, diff_maxs = get_min_max_diffs(diffs, _windows)
    closes = _df['close']
    transition_values = closes.shift(-_tau) - closes
    transitions_min = transition_values.min()
    transitions_max = transition_values.max()
    transitions_map = {}
    max_window = max(_windows)
    for i in range(max_window, len(_df) - _tau):
        positions = get_positions(_windows, diffs, diff_mins, diff_maxs, _grid_sizes, i)
        # Calculate transition position
        transition_value = transition_values.iloc[i]
        if transitions_max == transitions_min:
            transitions_pos_fixed = 0
        else:
            transitions_pos = (_transitions_grid_size - 1) * (transition_value - transitions_min) / (transitions_max - transitions_min)
            transitions_pos_fixed = max(0, min(round(transitions_pos), _transitions_grid_size - 1))
        # Update transitions_map
        if tuple(positions) not in transitions_map:
            transitions_map[tuple(positions)] = {}
        if transitions_pos_fixed not in transitions_map[tuple(positions)]:
            transitions_map[tuple(positions)][transitions_pos_fixed] = 1
        else:
            transitions_map[tuple(positions)][transitions_pos_fixed] += 1
    return diff_mins, diff_maxs, transitions_map, transitions_min, transitions_max

def test(_transitions_map, _windows, _grid_sizes, _diff_mins, _diff_maxs, _transitions_max, _transitions_min, _transitions_grid_size, _tau):
    max_window = max(_windows)
    start = train_size
    end = len(df['close']) - 1 # start + 300 + max_window
    dfc = df[start:end].copy()
    dfc['close'] = np.log(dfc['close']) - np.log(dfc['close'].iloc[0])
    diffs = get_diffs(dfc, _windows)
    averages = []
    confidences = []
    found = 0
    correct = 0
    wrong = 0
    for i in range(max_window, len(dfc) - _tau):
        positions = get_positions(_windows, diffs, _diff_mins, _diff_maxs, _grid_sizes, i)
        if tuple(positions) in _transitions_map:
            probs = _transitions_map[tuple(positions)]
            average = 0
            hits = sum(probs.values())
            for k, v in probs.items():
                shift = (_transitions_max - _transitions_min) * k / (_transitions_grid_size - 1) + _transitions_min
                average += shift * v / hits
            averages.append(average)
            confidences.append(hits)
            found += 1
            if dfc['close'].iloc[i + _tau] - dfc['close'].iloc[i] > 0 and average > 0:
                correct += 1
            elif dfc['close'].iloc[i + _tau] - dfc['close'].iloc[i] < 0 and average < 0:
                correct += 1
            else:
                wrong += 1
        else:
            averages.append(0)
            confidences.append(0)
    total = len(dfc) - max_window
    return found, correct, wrong, total

@app.function(image=image, timeout=260, scaledown_window=9)
def evaluate_hyperparams(_tau):
    tau = _tau
    windows = [4, 12, 36, 108, 324, 972]
    grid_sizes = [43, 159, 159, 159, 129, 129]
    transitions_grid_size=2999
    diff_mins, diff_maxs, transitions_map, transitions_min, transitions_max = \
        get_transitions_map(dfc, windows, tau, grid_sizes, transitions_grid_size)
    found, correct, wrong, total = test(transitions_map, windows, grid_sizes, diff_mins, diff_maxs, \
        transitions_max, transitions_min, transitions_grid_size, tau)
    print(f'found: {found}, correct: {correct}, wrong: {wrong}, total: {total}, accuracy: {correct / found}')
    return {
        "params": tau,
        "result": {
                "found": found,
                "correct": correct,
                "wrong": wrong,
                "total": total,
                "accuracy": correct / found
            }
        }

@app.local_entrypoint()
def main():
    search_space = [
        1, 2, 4, 5, 8, 9, 10, 14, 15, 16, 19, 20, 21, 25, 26, 30, 31
    ]
    print(f"Dispatching {len(search_space)} jobs to Modal...")
    futures = [evaluate_hyperparams.spawn(params) for params in search_space]
    results = [f.get() for f in futures]
    print("Best result:", max(results, key=lambda r: r["result"]["accuracy"]))
    # save to file locally
    os.makedirs("results", exist_ok=True)
    with open("results/results.txt", "a") as f:
        for r in results:
            f.write(f"{r}\n")
