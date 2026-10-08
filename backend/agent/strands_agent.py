from strands import Agent
from strands.models import BedrockModel
from agent.prompts import SYSTEM_PROMPT
from agent.strands_tools import ALL_TOOLS
from config import settings


def build_agent() -> Agent:
    model = BedrockModel(
        model_id=settings.BEDROCK_MODEL_ID,
        region_name=settings.BEDROCK_REGION,
        temperature=settings.BEDROCK_TEMPERATURE,
        max_tokens=settings.BEDROCK_MAX_TOKENS,
    )
    return Agent(model="openai.gpt-oss-120b-1:0", system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
