# src/trusted_data_agent/agent/response_models.py
from pydantic import BaseModel, Field
from typing import List, Optional

class KeyMetric(BaseModel):
    """
    Represents a single, primary metric that can summarize the answer
    to a user's query, such as a total count or a status.
    """
    value: str = Field(..., description="The value of the metric, represented as a string.")
    label: str = Field(..., description="A short, descriptive label for the metric.")

class Observation(BaseModel):
    """
    Represents a single textual insight, finding, or piece of contextual
    information related to the final answer.
    """
    text: str = Field(..., description="The content of the observation as a natural language string.")

class CanonicalResponse(BaseModel):
    """
    The standardized, structured data model for a final summary from the LLM.
    This model serves as the contract between the data generation tier (Tier 1)
    and the presentation/rendering tier (Tier 2), ensuring a reliable and
    decoupled architecture.
    """
    direct_answer: str = Field(
        ...,
        description="A direct and concise sentence that factually answers the user's primary question."
    )
    key_metric: Optional[KeyMetric] = Field(
        None,
        description="The optional, single primary metric summarizing the response."
    )
    key_observations: List[Observation] = Field(
        default_factory=list,
        description="A list of supporting details, findings, and contextual insights."
    )
