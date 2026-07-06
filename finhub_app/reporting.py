from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from finhub_app.domain import ReportContext
from finhub_app.guardrails import SYSTEM_GUARDRAILS, build_report_prompt


class ReportGenerator:
    def generate(self, context: ReportContext) -> str:
        raise NotImplementedError


class LangChainReportGenerator(ReportGenerator):
    def __init__(self, llm) -> None:
        self.llm = llm

    def generate(self, context: ReportContext) -> str:
        response = self.llm.invoke(
            [
                SystemMessage(content=SYSTEM_GUARDRAILS),
                HumanMessage(content=build_report_prompt(context)),
            ]
        )
        return _message_to_text(response)


class OpenAIReportGenerator(LangChainReportGenerator):
    def __init__(self, api_key: str, model: str) -> None:
        self.llm = ChatOpenAI(api_key=api_key, model=model, temperature=0.2)


class GeminiReportGenerator(LangChainReportGenerator):
    def __init__(self, api_key: str, model: str) -> None:
        self.llm = ChatGoogleGenerativeAI(
            api_key=api_key,
            model=model,
            temperature=0.2,
        )


def _message_to_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)

    content = response.content
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("text")
        ]
        return "\n".join(parts)

    return str(content)
