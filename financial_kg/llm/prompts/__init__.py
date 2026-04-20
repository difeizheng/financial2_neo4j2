"""LLM Prompt模板模块"""
from .structure_recognition import StructureRecognitionPrompt
from .semantic_annotation import SemanticAnnotationPrompt
from .formula_explanation import FormulaExplanationPrompt
from .anomaly_detection import AnomalyDetectionPrompt

__all__ = [
    "StructureRecognitionPrompt",
    "SemanticAnnotationPrompt",
    "FormulaExplanationPrompt",
    "AnomalyDetectionPrompt",
]