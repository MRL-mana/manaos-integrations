import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort


@dataclass
class Candidate:
    name: str
    provider: Any


def make_input(name: str, shape: list[Any], dtype: str):
    resolved = []
    for dim in shape:
        if isinstance(dim, int) and dim > 0:
            resolved.append(dim)
        else:
            resolved.append(1)

    if len(resolved) >= 2:
        resolved[0] = 1
        if resolved[1] < 8:
            resolved[1] = 8
        elif resolved[1] > 256:
            resolved[1] = 128

    np_dtype = {
        "tensor(int64)": np.int64,
        "tensor(int32)": np.int32,
        "tensor(float)": np.float32,
        "tensor(float16)": np.float16,
    }.get(dtype, np.float32)

    lowered = name.lower()
    if np.issubdtype(np_dtype, np.integer):
        if "token_type" in lowered:
            return np.random.randint(0, 2, size=resolved, dtype=np_dtype)
        if "attention_mask" in lowered:
            return np.ones(shape=resolved, dtype=np_dtype)
        if "input_ids" in lowered:
            return np.random.randint(0, 30522, size=resolved, dtype=np_dtype)
        return np.random.randint(0, 1000, size=resolved, dtype=np_dtype)

    return np.random.random(size=resolved).astype(np_dtype)


def build_inputs(session: ort.InferenceSession):
    feed = {}
    for inp in session.get_inputs():
        feed[inp.name] = make_input(inp.name, inp.shape, inp.type)
    return feed


def bench_candidate(model_path: Path, candidate: Candidate, runs: int):
    session = ort.InferenceSession(model_path.as_posix(), providers=[candidate.provider])
    used = session.get_providers()
    feed = build_inputs(session)

    for _ in range(3):
        session.run(None, feed)

    latencies = []
    for _ in range(runs):
        t0 = time.perf_counter()
        session.run(None, feed)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    return {
        "candidate": candidate.name,
        "requested_provider": str(candidate.provider),
        "used_providers": used,
        "avg_ms": statistics.mean(latencies),
        "p95_ms": float(np.percentile(latencies, 95)),
    }


def infer_loop(model_path: Path, best_provider: Any, iterations: int):
    session = ort.InferenceSession(model_path.as_posix(), providers=[best_provider])
    used = session.get_providers()
    feed = build_inputs(session)

    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        session.run(None, feed)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    return {
        "used_providers": used,
        "avg_ms": statistics.mean(latencies),
        "p95_ms": float(np.percentile(latencies, 95)),
        "iterations": iterations,
    }


def main():
    parser = argparse.ArgumentParser(description="Adaptive ONNX runtime selector (CPU vs DirectML)")
    parser.add_argument("--model", required=True, help="Path to ONNX model")
    parser.add_argument("--runs", type=int, default=8, help="Calibration runs per candidate")
    parser.add_argument("--iterations", type=int, default=30, help="Inference iterations after selection")
    parser.add_argument("--max-dml-device", type=int, default=2, help="Max DML device_id to probe")
    parser.add_argument("--out", default="adaptive_profile.json", help="Output JSON path")
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    available = ort.get_available_providers()
    print(f"onnxruntime={ort.__version__}")
    print(f"available_providers={available}")

    candidates = [Candidate("cpu", "CPUExecutionProvider")]
    if "DmlExecutionProvider" in available:
        candidates.append(Candidate("dml-default", "DmlExecutionProvider"))
        for device_id in range(args.max_dml_device + 1):
            candidates.append(
                Candidate(f"dml-device-{device_id}", ("DmlExecutionProvider", {"device_id": device_id}))
            )

    calibration = []
    for candidate in candidates:
        try:
            result = bench_candidate(model_path, candidate, args.runs)
            calibration.append(result)
            print(
                f"[calib] {result['candidate']}: avg={result['avg_ms']:.2f}ms p95={result['p95_ms']:.2f}ms used={result['used_providers']}"
            )
        except Exception as ex:
            print(f"[calib] {candidate.name}: failed ({ex})")

    if not calibration:
        raise RuntimeError("No valid provider candidate found")

    best = min(calibration, key=lambda x: x["avg_ms"])
    print(f"[select] best={best['candidate']} avg={best['avg_ms']:.2f}ms")

    chosen_provider = None
    for candidate in candidates:
        if candidate.name == best["candidate"]:
            chosen_provider = candidate.provider
            break

    infer_stats = infer_loop(model_path, chosen_provider, args.iterations)
    print(
        f"[infer] avg={infer_stats['avg_ms']:.2f}ms p95={infer_stats['p95_ms']:.2f}ms used={infer_stats['used_providers']}"
    )

    payload = {
        "model": model_path.as_posix(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "available_providers": available,
        "calibration": calibration,
        "selected": best,
        "infer": infer_stats,
    }

    out_path = Path(args.out).resolve()
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved profile: {out_path}")


if __name__ == "__main__":
    main()
