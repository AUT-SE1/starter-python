"""Validate a live response against the shared OpenAPI document.

This understands the small slice of JSON Schema that openapi.yaml actually
uses: $ref, type, required, properties, enum and the numeric and string
bounds. It is deliberately dependency-free. If you would rather use a real
validator, openapi-core is the usual Python choice — swap it in and keep the
tests as they are.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_JSON_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "number": (int, float),
}


class OpenAPIDocument:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._root: dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))

    def schema(self, name: str) -> dict[str, Any]:
        schemas = self._root.get("components", {}).get("schemas", {})
        if name not in schemas:
            raise KeyError(f"schema {name!r} is not defined in {self._path}")
        return schemas[name]

    def validate(self, schema_name: str, value: Any) -> list[str]:
        """Return every problem found, so one failure names all of them."""
        problems: list[str] = []
        self._check(self.schema(schema_name), value, schema_name, problems)
        return problems

    # -- internals ---------------------------------------------------------

    def _resolve(self, schema: dict[str, Any]) -> dict[str, Any]:
        ref = schema.get("$ref")
        if not ref:
            return schema
        # Only local refs of the form #/components/schemas/Name are used here.
        return self.schema(ref.rsplit("/", 1)[-1])

    def _check(self, schema: dict[str, Any], value: Any, path: str, problems: list[str]) -> None:
        schema = self._resolve(schema)
        expected_type = schema.get("type")

        if expected_type and not _matches_type(expected_type, value):
            problems.append(f"{path}: expected type {expected_type}, got {_describe(value)}")
            return

        if "enum" in schema and value not in schema["enum"]:
            problems.append(f"{path}: value {value!r} is not one of {schema['enum']}")

        if expected_type == "object":
            for name in schema.get("required", []):
                if name not in value:
                    problems.append(f"{path}: required field {name!r} is missing")
            for name, property_schema in schema.get("properties", {}).items():
                if name in value:
                    self._check(property_schema, value[name], f"{path}.{name}", problems)

        elif expected_type == "string":
            minimum = schema.get("minLength")
            maximum = schema.get("maxLength")
            if minimum is not None and len(value) < minimum:
                problems.append(f"{path}: shorter than minLength {minimum}")
            if maximum is not None and len(value) > maximum:
                problems.append(f"{path}: longer than maxLength {maximum}")

        elif expected_type in ("integer", "number"):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and value < minimum:
                problems.append(f"{path}: {value} is below minimum {minimum}")
            if maximum is not None and value > maximum:
                problems.append(f"{path}: {value} is above maximum {maximum}")


def _matches_type(expected: str, value: Any) -> bool:
    if expected == "integer":
        # bool is a subclass of int in Python; a JSON integer is not a boolean.
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    python_type = _JSON_TYPES.get(expected)
    return True if python_type is None else isinstance(value, python_type)


def _describe(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__
