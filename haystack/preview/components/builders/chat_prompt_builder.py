import logging
from typing import Dict, Any, Optional, List

from jinja2 import Template

from haystack.preview import component
from haystack.preview import default_to_dict
from haystack.preview.dataclasses.chat_message import ChatMessage, ChatRole

logger = logging.getLogger(__name__)


@component
class ChatPromptBuilder:
    """
    ChatPromptBuilder builds chat prompts based on the provided list of ``ChatMessage`` instances and template
    variables. It integrates with Jinja2 templating for dynamic prompt generation.

    :param template_variables: A list of strings representing the variables that can be used in the Jinja2
    templates. These variables are essential for resolving dynamic content in the chat prompt.
    :type template_variables: List[str]
    """

    def __init__(self, template_variables: List[str]):
        """
        Initializes the class with the provided template variables. These variable names are used to resolve variables
        and their values during pipeline execution. The values resolved from the pipeline runtime are then injected
        into template placeholders of the ChatMessage. See run method for more details.

        :param template_variables: A list of template variable names to be used in chat prompt construction.
        :type template_variables: List[str]
        """
        if not template_variables:
            logger.warning(
                "template_variables were not provided, ChatPromptBuilder will not resolve any pipeline variables."
            )
        self.template_variables = template_variables

        input_slots = {var: Optional[Any] for var in template_variables}
        component.set_output_types(self, prompt=List[ChatMessage])

        run_input_slots = {"messages": List[ChatMessage], "template_variables": Optional[List[str]]}
        component.set_input_types(self, **run_input_slots, **input_slots)

    def to_dict(self) -> Dict[str, Any]:
        """
         Converts the `ChatPromptBuilder` instance to a dictionary format, primarily for serialization purposes.

        :return: A dictionary representation of the `ChatPromptBuilder` instance, including its template variables.
        :rtype: Dict[str, Any]
        """
        return default_to_dict(self, template_variables=self.template_variables)

    def run(self, messages: List[ChatMessage], template_variables: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Executes the chat prompt building process. This method injects the resolved pipeline variables into the
        template placeholders of the last user message. User has an option to provide additional template variables
        to the pipeline `run` method directly, which are merged with the pipeline variables resolved from the pipeline
        runtime.


        :param messages: A list of `ChatMessage` instances, representing the conversation history.
        :type messages: List[ChatMessage]
        :param template_variables: An optional dictionary of template variables. While template variables provided at
        initialization are required to resolve pipeline variables, these variables are additional variables users can
        directly provide to the pipeline `run` method and use in the template as well. Defaults to None.
        :type template_variables: Optional[Dict[str, Any]]
        :param kwargs: Additional keyword arguments, typically resolved from a pipeline, which are merged with the
        provided template variables.
        :return: A dictionary containing the key "prompt", which holds the updated list of `ChatMessage` instances,
        forming the complete chat prompt.
        :rtype: Dict[str, List[ChatMessage]]
        :raises ValueError: If no `ChatMessage` instances are provided to the method.
        """
        if messages:
            # apply the template to the last user message only
            last_message: ChatMessage = messages[-1]
            if last_message.is_from(ChatRole.USER):
                template = Template(last_message.content)
                if template_variables or kwargs:
                    # merge template_variables (user provided) and kwargs (resolved from pipeline)
                    template_variables_final = {**(kwargs or {}), **(template_variables or {})}
                    templated_user_message = ChatMessage.from_user(template.render(template_variables_final))
                    # return all previous messages + templated user message
                    new_messages = messages[:-1] + [templated_user_message]
                    return {"prompt": new_messages}
                return {"prompt": messages}
            else:
                return {"prompt": messages}
        else:
            raise ValueError("ChatPromptBuilder was not provided with ChatMessage(s)")
