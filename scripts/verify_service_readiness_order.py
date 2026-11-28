"""Verify API readiness error ordering without importing service dependencies."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
import symtable
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "service" / "app.py"


class ModelLoadError(Exception):
    def __init__(self, code: str, public_message: str) -> None:
        self.code = code
        self.public_message = public_message


class HealthReadyResponse:
    pass


class HealthUnavailableResponse:
    def __init__(self, **values: Any) -> None:
        self.values = values


class JSONResponse:
    def __init__(self, *, status_code: int, content: Any) -> None:
        self.status_code = status_code
        self.content = content


class HTTPException(Exception):
    def __init__(self, *, status_code: int, detail: Any) -> None:
        self.status_code = status_code
        self.detail = detail


class UploadFile:
    pass


def load_route_functions(source: str) -> dict[str, Any]:
    module = ast.parse(source, filename=str(SOURCE_PATH))
    selected = [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"health", "predict"}
    ]
    names = {node.name for node in selected}
    if names != {"health", "predict"}:
        raise AssertionError(f"Expected health and predict routes, found {sorted(names)}")

    for node in selected:
        node.decorator_list = []

    namespace: dict[str, Any] = {
        "ModelLoadError": ModelLoadError,
        "HealthReadyResponse": HealthReadyResponse,
        "HealthUnavailableResponse": HealthUnavailableResponse,
        "JSONResponse": JSONResponse,
        "HTTPException": HTTPException,
        "UploadFile": UploadFile,
        "File": lambda *_args, **_kwargs: None,
        "DEFAULT_CONFIDENCE": 0.25,
        "CLASS_NAMES": {0: "hard_hat_worn", 1: "depiction_region"},
        "jsonable_encoder": lambda value: value.values,
        "Any": Any,
    }
    isolated = ast.Module(body=selected, type_ignores=[])
    exec(compile(isolated, f"{SOURCE_PATH}#routes", "exec"), namespace)
    return namespace


def route_error_code(response: Any) -> str:
    if isinstance(response, JSONResponse):
        return response.content["error_code"]
    if isinstance(response, HTTPException):
        return response.detail["code"]
    raise AssertionError(f"Unexpected route response: {type(response).__name__}")


def invoke_route(namespace: dict[str, Any], route_name: str) -> Any:
    try:
        if route_name == "health":
            return namespace[route_name]()
        return asyncio.run(namespace[route_name](image=object(), confidence=0.25))
    except HTTPException as response:
        return response


def check_missing_model_precedes_gpu(namespace: dict[str, Any]) -> None:
    for route_name in ("health", "predict"):
        calls: list[str] = []

        def load_model() -> None:
            calls.append("model")
            raise ModelLoadError("model_path_not_configured", "MODEL_PATH missing")

        def require_gpu() -> None:
            calls.append("gpu")
            raise ModelLoadError("inference_gpu_unavailable", "GPU unavailable")

        namespace.update(load_model=load_model, require_inference_gpu=require_gpu)
        response = invoke_route(namespace, route_name)
        observed = route_error_code(response)
        if observed != "model_path_not_configured" or calls != ["model"]:
            raise AssertionError(f"{route_name}: expected model config first; got {observed} via {calls}")


def check_cached_model_still_checks_gpu(namespace: dict[str, Any]) -> None:
    for route_name in ("health", "predict"):
        calls: list[str] = []

        def load_model() -> object:
            calls.append("model")
            return object()

        def require_gpu() -> None:
            calls.append("gpu")
            raise ModelLoadError("inference_gpu_unavailable", "GPU unavailable")

        namespace.update(load_model=load_model, require_inference_gpu=require_gpu)
        response = invoke_route(namespace, route_name)
        observed = route_error_code(response)
        if observed != "inference_gpu_unavailable" or calls != ["model", "gpu"]:
            raise AssertionError(f"{route_name}: cached-model GPU check missing; got {observed} via {calls}")


def check_model_cache_is_global(source: str) -> None:
    table = symtable.symtable(source, str(SOURCE_PATH), "exec")
    loader = next((scope for scope in table.get_children() if scope.get_name() == "load_model"), None)
    if loader is None:
        raise AssertionError("load_model() was not found")
    cache_symbol = loader.lookup("_model")
    if not cache_symbol.is_global() or not cache_symbol.is_assigned():
        raise AssertionError("load_model() must declare and assign the module-level _model cache")


def main() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    compile(source, str(SOURCE_PATH), "exec")
    namespace = load_route_functions(source)
    check_missing_model_precedes_gpu(namespace)
    check_cached_model_still_checks_gpu(namespace)
    check_model_cache_is_global(source)
    print("PASS: health/predict prioritize model configuration errors")
    print("PASS: health/predict recheck GPU after cached-model return")
    print("PASS: load_model() assigns the module-level _model cache")
    print("PASS: service/app.py compiles")


if __name__ == "__main__":
    main()
