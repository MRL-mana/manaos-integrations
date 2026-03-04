import statistics
import time
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import onnxruntime as ort

MODEL_URL = "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/onnx/model.onnx"
MODEL_PATH = Path(__file__).with_name("all_minilm_l6_v2.onnx")


def ensure_model() -> None:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 0:
        print(f"Model exists: {MODEL_PATH} ({MODEL_PATH.stat().st_size} bytes)")
        return
    print(f"Downloading model from: {MODEL_URL}")
    urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"Downloaded: {MODEL_PATH} ({MODEL_PATH.stat().st_size} bytes)")


def make_input(name, shape, dtype):
    fixed_shape = []
    for dim in shape:
        if isinstance(dim, int) and dim > 0:
            fixed_shape.append(dim)
        else:
            fixed_shape.append(1)

    if len(fixed_shape) == 1:
        fixed_shape[0] = max(8, fixed_shape[0])
    elif len(fixed_shape) >= 2:
        fixed_shape[0] = 1
        fixed_shape[1] = 128

    np_dtype = {
        "tensor(int64)": np.int64,
        "tensor(int32)": np.int32,
        "tensor(float)": np.float32,
        "tensor(float16)": np.float16,
    }.get(dtype, np.float32)

    if np.issubdtype(np_dtype, np.integer):
        lowered = name.lower()
        if "token_type" in lowered:
            return np.random.randint(0, 2, size=fixed_shape, dtype=np_dtype)
        if "attention_mask" in lowered:
            return np.ones(shape=fixed_shape, dtype=np_dtype)
        if "input_ids" in lowered:
            return np.random.randint(0, 30522, size=fixed_shape, dtype=np_dtype)
        return np.random.randint(0, 1000, size=fixed_shape, dtype=np_dtype)
    return np.random.random(size=fixed_shape).astype(np_dtype)


def bench(provider, runs=30):
    session = ort.InferenceSession(MODEL_PATH.as_posix(), providers=[provider])
    used = session.get_providers()

    inputs = {}
    for inp in session.get_inputs():
        inputs[inp.name] = make_input(inp.name, inp.shape, inp.type)

    for _ in range(5):
        _ = session.run(None, inputs)

    latencies = []
    for _ in range(runs):
        t0 = time.perf_counter()
        _ = session.run(None, inputs)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    avg = statistics.mean(latencies)
    p95 = float(np.percentile(latencies, 95))
    return avg, p95, used


def main():
    print(f"onnxruntime={ort.__version__}")
    print(f"available_providers={ort.get_available_providers()}")
    ensure_model()

    cpu_avg, cpu_p95, cpu_used = bench("CPUExecutionProvider", runs=30)
    print(f"CPU: avg={cpu_avg:.2f} ms p95={cpu_p95:.2f} ms used={cpu_used}")

    if "DmlExecutionProvider" in ort.get_available_providers():
        dml_avg, dml_p95, dml_used = bench("DmlExecutionProvider", runs=30)
        print(f"DML(default): avg={dml_avg:.2f} ms p95={dml_p95:.2f} ms used={dml_used}")

        print("DML device sweep:")
        for device_id in range(4):
            provider = ("DmlExecutionProvider", {"device_id": device_id})
            try:
                avg, p95, used = bench(provider, runs=20)
                print(
                    f"  device_id={device_id}: avg={avg:.2f} ms p95={p95:.2f} ms used={used}"
                )
            except Exception as ex:
                print(f"  device_id={device_id}: unavailable ({ex})")


if __name__ == "__main__":
    main()
