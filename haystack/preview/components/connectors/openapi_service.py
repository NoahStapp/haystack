import json
import logging
from typing import List, Dict, Optional, Any


from haystack.preview.dataclasses import ChatMessage, ChatRole
from haystack.preview import component
from haystack.preview.lazy_imports import LazyImport

logger = logging.getLogger(__name__)

with LazyImport("Run 'pip install openapi3'") as openapi_imports:
    from openapi3 import OpenAPI


@component
class OpenAPIServiceConnector:
    def __init__(self):
        openapi_imports.check()

    @component.output_types(service_response=Dict[str, Any])
    def run(self, messages: List[ChatMessage], service_openapi_spec: Any):
        message = messages[-1]
        if message.is_from(ChatRole.ASSISTANT) and self.is_valid_json(message.content):
            method_invocation_descriptor = json.loads(message.content)
            parameters = json.loads(method_invocation_descriptor["arguments"])
            name = method_invocation_descriptor["name"]

            openapi_service = OpenAPI(service_openapi_spec)

            method_name = f"call_{name}"
            method_to_call = getattr(openapi_service, method_name, None)

            # Check if the method exists and then call it
            if callable(method_to_call):
                service_response = method_to_call(parameters=parameters["parameters"])
                return {"service_response": [ChatMessage.from_user(str(service_response))]}
            else:
                raise ValueError(f"Method {method_name} not found in the OpenAPI specification.")
        else:
            raise ValueError(
                f"Message {message} does not contain correct function calling payload to invoke a method on the service."
            )

    def is_valid_json(self, content):
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False
