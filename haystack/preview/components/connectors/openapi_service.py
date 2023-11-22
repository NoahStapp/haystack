import json
import logging
from typing import List, Dict, Optional, Any

import requests


from haystack.preview.dataclasses import ChatMessage, ChatRole
from haystack.preview.lazy_imports import LazyImport

logger = logging.getLogger(__name__)

with LazyImport("Run 'pip install jsonref openapi3'") as openapi_imports:
    import jsonref
    from openapi3 import OpenAPI


class OpenAPIServiceConnector:
    def __init__(self, service_spec_url: str):
        """
        :param service_spec_url: URL of the OpenAPI specification of the service.
        """
        openapi_imports.check()
        self.service_spec_url = service_spec_url
        self.openapi_functions: Optional[List[Dict[str, Any]]] = None
        self.service_openapi: Optional[OpenAPI] = None

    def warm_up(self):
        response = requests.get(self.service_spec_url)
        if response.status_code == 200:
            service_openapi_spec = jsonref.loads(response.content)
            self.openapi_functions = self.openapi_to_functions(service_openapi_spec)
            self.service_openapi = OpenAPI(service_openapi_spec)
        else:
            raise Exception(f"Could not download OpenAPI specification from {self.service_spec_url}")

    def openapi_to_functions(self, service_openapi_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract functions from the OpenAPI specification of the service.
        """
        functions: List[Dict[str, Any]] = []
        for methods in service_openapi_spec["paths"].values():
            for spec_with_ref in methods.values():
                spec = jsonref.replace_refs(spec_with_ref)
                function_name = spec.get("operationId")
                desc = spec.get("description") or spec.get("summary", "")

                schema = {"type": "object", "properties": {}}

                req_body = spec.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
                if req_body:
                    schema["properties"]["requestBody"] = req_body

                params = spec.get("parameters", [])
                if params:
                    param_properties = {param["name"]: param["schema"] for param in params if "schema" in param}
                    schema["properties"]["parameters"] = {"type": "object", "properties": param_properties}

                functions.append({"name": function_name, "description": desc, "parameters": schema})
        return functions

    def run(self, message: ChatMessage):
        if message.is_from(ChatRole.ASSISTANT) and self.is_valid_json(message.content):
            method_invocation_descriptor = json.loads(message.content)
            parameters = method_invocation_descriptor["arguments"]
            name = method_invocation_descriptor["name"]

            method_name = f"call_{name}"
            method_to_call = getattr(self.service_openapi, method_name, None)

            # Check if the method exists and then call it
            if callable(method_to_call):
                return method_to_call(parameters=parameters)
            else:
                raise ValueError(f"Method {method_name} not found in the OpenAPI specification.")
        else:
            raise ValueError(f"Message {message} does not contain correct payload to invoke a method on the service.")

    def is_valid_json(self, content):
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False
