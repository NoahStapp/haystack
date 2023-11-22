import logging
from typing import List, Dict, Optional, Any

import requests

from haystack.preview import component
from haystack.preview.lazy_imports import LazyImport

logger = logging.getLogger(__name__)

with LazyImport("Run 'pip install jsonref'") as openapi_imports:
    import jsonref


@component
class OpenAPIServiceFunctionsBuilder:
    def __init__(self, service_spec_url: str):
        """
        :param service_spec_url: URL of the OpenAPI specification of the service.
        """
        openapi_imports.check()
        self.service_spec_url = service_spec_url
        self.openapi_functions: Optional[List[Dict[str, Any]]] = None
        self.service_openapi_spec: Optional[Any] = None  # OpenAPI JSON spec of the service

    def warm_up(self):
        response = requests.get(self.service_spec_url)
        if response.status_code == 200:
            service_openapi_spec = jsonref.loads(response.content)
            self.openapi_functions = self.openapi_to_functions(service_openapi_spec)
            self.service_openapi_spec = service_openapi_spec
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

    @component.output_types(functions=Dict[str, Any], service_openapi_spec=Dict[str, Any])
    def run(self, test: str) -> Dict[str, Any]:
        """
        Run the function specified in the message against the OpenAPI service.
        """
        if self.openapi_functions is None:
            raise Exception("OpenAPI service connector not warmed up. Call warm_up() first.")

        return {"functions": {"functions": self.openapi_functions}, "service_openapi_spec": self.service_openapi_spec}
