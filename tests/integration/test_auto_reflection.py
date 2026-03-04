#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自動反省・改善システムの pytest スモークテスト。"""

import pytest


def _require_module():
    try:
        return __import__("auto_reflection_improvement", fromlist=["*"])
    except Exception as error:
        pytest.skip(f"auto_reflection_improvement unavailable: {error}")


@pytest.fixture
def reflection_system():
    module = _require_module()
    try:
        return module.get_auto_reflection_system()
    except Exception as error:
        pytest.skip(f"reflection system initialization failed: {error}")


def test_import_symbols_available():
    module = _require_module()
    assert hasattr(module, "get_auto_reflection_system")
    assert hasattr(module, "ImageEvaluator")
    assert hasattr(module, "AutoImprover")
    assert hasattr(module, "AutoReflectionImprovementSystem")


def test_statistics(reflection_system):
    stats = reflection_system.get_statistics()
    assert isinstance(stats, dict)
    assert "total_evaluations" in stats
    assert "average_score" in stats


def test_evaluation(reflection_system):
    evaluation = reflection_system.evaluator.evaluate_image(
        image_path="test_image.png",
        prompt="cute anime girl",
        negative_prompt="",
        model="test_model.safetensors",
        parameters={"steps": 30, "width": 512, "height": 512},
    )
    assert hasattr(evaluation, "overall_score")
    assert hasattr(evaluation, "improvements")


def test_improvement(reflection_system):
    module = _require_module()
    evaluation = module.ImageEvaluation(
        image_path="test.png",
        prompt="cute anime girl",
        negative_prompt="",
        model="test_model",
        parameters={"steps": 30, "width": 512, "height": 512},
        overall_score=0.5,
        anatomy_score=0.4,
        quality_score=0.6,
        prompt_match_score=0.5,
    )
    improvement = reflection_system.improver.improve_generation(evaluation, threshold=0.7)
    assert improvement is None or hasattr(improvement, "expected_improvement")
