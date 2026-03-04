import time
import statistics
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper
import onnxruntime as ort


def build_model(path: Path) -> None:
    x = helper.make_tensor_value_info("X", TensorProto.FLOAT, [1, 1024])
    y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [1, 1024])

    add_const = helper.make_tensor(
        "add_const", TensorProto.FLOAT, [1, 1024], [0.5] * 1024
    )
    mul_const = helper.make_tensor(
        "mul_const", TensorProto.FLOAT, [1, 1024], [1.1] * 1024
    )

    nodes = [
        helper.make_node("Add", ["X", "add_const"], ["A"]),
        helper.make_node("Mul", ["A", "mul_const"], ["B"]),
        helper.make_node("Relu", ["B"], ["Y"]),
    ]

    graph = helper.make_graph(nodes, "TinyBench", [x], [y], [add_const, mul_const])
    model = helper.make_model(
        graph,
        producer_name="dml_quick_bench",
        ir_version=10,
        opset_imports=[helper.make_operatorsetid("", 13)],
    )
    onnx.save(model, path.as_posix())


def build_heavy_model(path: Path) -> None:
    x = helper.make_tensor_value_info("X", TensorProto.FLOAT, [1, 4096])
    y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [1, 4096])

    rng = np.random.default_rng(42)
    w1 = rng.standard_normal((4096, 4096), dtype=np.float32) * 0.02
    w2 = rng.standard_normal((4096, 4096), dtype=np.float32) * 0.02

    w1_init = helper.make_tensor(
        "W1", TensorProto.FLOAT, [4096, 4096], w1.reshape(-1).tolist()
    )
    w2_init = helper.make_tensor(
        "W2", TensorProto.FLOAT, [4096, 4096], w2.reshape(-1).tolist()
    )

    nodes = [
        helper.make_node("MatMul", ["X", "W1"], ["M1"]),
        helper.make_node("Relu", ["M1"], ["R1"]),
        helper.make_node("MatMul", ["R1", "W2"], ["M2"]),
        helper.make_node("Relu", ["M2"], ["Y"]),
    ]

    graph = helper.make_graph(nodes, "HeavyBench", [x], [y], [w1_init, w2_init])
    model = helper.make_model(
        graph,
        producer_name="dml_quick_bench",
        ir_version=10,
        opset_imports=[helper.make_operatorsetid("", 13)],
    )
    onnx.save(model, path.as_posix())


def bench(provider, model_path: Path, runs: int = 200) -> tuple[float, float, list[str]]:
    sess = ort.InferenceSession(model_path.as_posix(), providers=[provider])
    used_providers = sess.get_providers()
    input_name = sess.get_inputs()[0].name
    input_shape = sess.get_inputs()[0].shape
    width = input_shape[1] if isinstance(input_shape[1], int) and input_shape[1] > 0 else 1024
    data = np.random.rand(1, width).astype(np.float32)

    for _ in range(20):
        _ = sess.run(None, {input_name: data})

    latencies = []
    for _ in range(runs):
        start = time.perf_counter()
        _ = sess.run(None, {input_name: data})
        end = time.perf_counter()
        latencies.append((end - start) * 1000)

    avg = statistics.mean(latencies)
    p95 = np.percentile(latencies, 95)
    return avg, float(p95), used_providers


def main() -> None:
    providers = ort.get_available_providers()
    print(f"Available providers: {providers}")

    model_path = Path(__file__).with_name("tiny_bench.onnx")
    build_model(model_path)
    print(f"Model generated: {model_path}")

    heavy_model_path = Path(__file__).with_name("heavy_bench.onnx")
    build_heavy_model(heavy_model_path)
    print(f"Model generated: {heavy_model_path}")

    targets = ["CPUExecutionProvider"]
    if "DmlExecutionProvider" in providers:
        targets.append("DmlExecutionProvider")

    for provider in targets:
        avg, p95, used = bench(provider, model_path)
        print(f"[tiny]  {provider}: avg={avg:.4f} ms, p95={p95:.4f} ms, used={used}")

    for provider in targets:
        avg, p95, used = bench(provider, heavy_model_path, runs=50)
        print(f"[heavy] {provider}: avg={avg:.4f} ms, p95={p95:.4f} ms, used={used}")

    if "DmlExecutionProvider" in providers:
        print("\n[DirectML device_id sweep]")
        for device_id in range(4):
            provider = ("DmlExecutionProvider", {"device_id": device_id})
            try:
                avg, p95, used = bench(provider, heavy_model_path, runs=30)
                print(
                    f"[heavy] DML device_id={device_id}: avg={avg:.4f} ms, p95={p95:.4f} ms, used={used}"
                )
            except Exception as error:
                print(f"[heavy] DML device_id={device_id}: unavailable ({error})")


if __name__ == "__main__":
    main()
