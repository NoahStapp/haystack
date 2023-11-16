from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from haystack.preview.dataclasses.document import Document

# TODO: Serialization, much like we do for Components. Extremely important
data = {"type": "ExtractedAnswer", "data": "whate", "document": {"id": ""}}

# TODO: Create backward compatibility metaclass like Document


@dataclass(frozen=True)
class Answer:
    data: Any
    query: str
    metadata: Dict[str, Any]  # rename to meta


# TODO: create property from answer to data


@dataclass(frozen=True)
class ExtractedAnswer(Answer):
    data: Optional[str]
    document: Optional[Document]
    context: str  # Need to add this, snippet of text found in the Document relevant to the answer.data
    probability: float  # rename to score
    # TODO: Rework start and end to included both the offset in Document and in the context
    start: Optional[int] = None
    end: Optional[int] = None


@dataclass(frozen=True)
class GeneratedAnswer(Answer):
    data: str
    documents: List[Document]
