"""Ask-user middleware: always-available tool for interactive Q&A during agent execution.

Bundles the ask_user tool and system-prompt injection together as a QuickToolsMiddleware,
so the tool and its LLM guidance are always added as a unit.
"""
import logging
from typing import Annotated, Any, Literal, cast

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command, interrupt
from typing_extensions import NotRequired, TypedDict

from lc_agent.middlewares.quick_tools import QuickToolsMiddleware

logger = logging.getLogger(__name__)

ASK_USER_SYSTEM_PROMPT = """\
<ask_user_rules>
## `ask_user`

You have access to the `ask_user` tool to ask the user questions when you need clarification or input.
Use this tool sparingly — only when you genuinely need information you cannot determine from context.

When using `ask_user`:
- Be concise and specific
- Group related questions into a **single** `ask_user` call; never make multiple sequential calls for information you need at once
- Never ask questions you can answer yourself from the available context
- Do NOT use for trivial yes/no decisions — just proceed with your best judgment

Do NOT use `ask_user` for:
- Simple confirmations you can handle autonomously
- Questions answerable from the conversation history or visible files
</ask_user_rules>"""


class QuestionInput(TypedDict):
    """LLM-facing question spec.

    Deliberately has NO ``type`` field: the type is inferred server-side from
    ``choices`` (present -> multiple_choice, absent -> text), so the model has
    no redundant field to forget or contradict.
    """

    question: Annotated[str, "The question text to display to the user."]
    choices: NotRequired[
        Annotated[
            list[str],
            "Include to make the question multiple-choice; omit for free-text input. "
            "An 'Other / custom' option is always appended automatically.",
        ]
    ]
    required: NotRequired[
        Annotated[bool, "Whether the user must answer. Defaults to true if omitted."]
    ]
    allow_multiple: NotRequired[
        Annotated[
            bool,
            "Only for questions with 'choices': allow selecting multiple options simultaneously. Defaults to false.",
        ]
    ]


class Question(TypedDict):
    """Normalized question used internally and in the interrupt payload sent to the frontend."""

    question: Annotated[str, "The question text to display to the user."]
    type: Annotated[
        Literal["text", "multiple_choice"],
        "Inferred server-side: 'multiple_choice' when 'choices' is present, else 'text'.",
    ]
    choices: NotRequired[
        Annotated[
            list[str],
            "Options for multiple_choice questions. An 'Other / custom' option is always appended automatically.",
        ]
    ]
    required: NotRequired[
        Annotated[bool, "Whether the user must answer. Defaults to true if omitted."]
    ]
    allow_multiple: NotRequired[
        Annotated[
            bool,
            "For multiple_choice: allow selecting multiple options simultaneously. Defaults to false.",
        ]
    ]


ASK_USER_TOOL_DESCRIPTION = """\
Ask the user one or more questions when you need clarification or input before proceeding.

Each question object has:
- "question" (required): the question text shown to the user
- "choices": list of option strings — include it to make the question multiple-choice,
  omit it to let the user type a free-text answer.
  An "Other / custom" option is always appended automatically.
- "allow_multiple": true to let the user select several options (only together with "choices")
- "required": false for optional questions (default: required)

Prefer multiple-choice (include "choices") when the answer set is finite and enumerable.
Mark a question optional ("required": false) only when you can proceed without the answer.

Example:
{"questions": [
  {"question": "Deploy to which environment?", "choices": ["testing", "staging", "production"]},
  {"question": "Any extra notes? (optional)", "required": false}
]}

Do not include "(required)" or "(optional)" annotations in the question text — the UI renders that
separately based on the "required" field.

Use this tool when:
- Critical information is missing and cannot be inferred from context
- The user must choose from a limited set of alternatives (provide "choices")
- Confirmation is needed before an irreversible action
- Multiple pieces of information are needed at once

Group related questions into a single call to minimise interruptions.
Do NOT use for decisions you can make yourself from the available context."""


def _normalize_questions(questions: list[QuestionInput]) -> list[Question]:
    """Infer `type` from `choices` and build normalized Question dicts.

    The LLM-facing schema has no `type` field: a question with a non-empty
    "choices" list is multiple_choice, anything else is text. Unknown extra
    keys (e.g. a stale "type" still emitted by the model) are dropped.
    """
    normalized: list[Question] = []
    for q in questions:
        if not isinstance(q, dict):
            # Keep as-is; _validate_questions raises the friendly error below.
            normalized.append(cast("Question", q))
            continue
        choices = q.get("choices")
        nq: dict[str, Any] = {
            "question": q.get("question"),
            "type": "multiple_choice" if choices else "text",
        }
        if choices:
            nq["choices"] = choices
        for key in ("required", "allow_multiple"):
            if key in q:
                nq[key] = q[key]
        normalized.append(cast("Question", nq))
    return normalized


def _validate_questions(questions: list[Question]) -> None:
    """Validate normalized question list structure before interrupting the agent."""
    if not questions:
        raise ValueError("ask_user requires at least one question")
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise ValueError(f"Question {i} must be a dict, got {type(q).__name__!r}")
        if not isinstance(q.get("question"), str) or not q["question"].strip():
            raise ValueError(f"Question {i} must have non-empty 'question' text")
        q_type = q.get("type", "text")
        if q_type not in ("text", "multiple_choice"):
            raise ValueError(
                f"Question {i} type must be 'text' or 'multiple_choice', got: {q_type!r}"
            )
        if q_type == "multiple_choice":
            choices = q.get("choices")
            if not isinstance(choices, list) or not choices:
                raise ValueError(
                    f"multiple_choice question {q.get('question')!r} requires a non-empty 'choices' list"
                )
            if not all(isinstance(c, str) and c.strip() for c in choices):
                raise ValueError(
                    f"multiple_choice question {q.get('question')!r}: all choices must be non-empty strings"
                )
        if q_type == "text" and q.get("choices"):
            raise ValueError(f"text question {q.get('question')!r} must not define 'choices'")
        if "required" in q and not isinstance(q["required"], bool):
            raise ValueError(
                f"Question {i} 'required' must be bool, got {type(q['required']).__name__!r}"
            )


def _parse_answers(
    response: object,
    questions: list[Question],
    tool_call_id: str,
) -> Command[Any]:
    """Parse an interrupt resume payload into a Command containing a ToolMessage.

    Supports status signals from the frontend adapter:
    - ``answered``: consume the provided ``answers`` list
    - ``cancelled``: synthesize ``(cancelled)`` answers
    - ``error``: synthesize ``(error: ...)`` answers

    Malformed payloads yield explicit error answers instead of silent fallbacks.
    """
    status: str = "answered"
    error_text: str | None = None
    answers: list[str]

    if not isinstance(response, dict):
        logger.error(
            "ask_user received malformed resume payload (expected dict, got %s); returning error answers",
            type(response).__name__,
        )
        answers = []
        status = "error"
        error_text = "invalid ask_user response payload"
    else:
        response_dict = cast("dict[str, Any]", response)
        response_status = response_dict.get("status")
        if isinstance(response_status, str):
            status = response_status

        if "answers" not in response_dict:
            if status == "answered":
                logger.error(
                    "ask_user resume payload missing 'answers' field; returning error answers"
                )
                answers = []
                status = "error"
                error_text = "missing ask_user answers payload"
            else:
                answers = []
        else:
            raw_answers = response_dict["answers"]
            if isinstance(raw_answers, list):
                answers = [str(a) for a in raw_answers]
            else:
                logger.error(
                    "ask_user received non-list 'answers' (%s); returning error answers",
                    type(raw_answers).__name__,
                )
                answers = []
                status = "error"
                error_text = "invalid ask_user answers payload"

        if status == "cancelled":
            answers = ["(cancelled)"] * len(questions)
        elif status == "error":
            err = response_dict.get("error")
            if isinstance(err, str) and err:
                error_text = err
        elif status == "answered":
            if len(answers) != len(questions):
                logger.warning(
                    "ask_user answer count mismatch: expected %d, got %d",
                    len(questions),
                    len(answers),
                )
        else:
            logger.error(
                "ask_user received unknown status %r; returning error answers", status
            )
            answers = []
            status = "error"
            error_text = "invalid ask_user response status"

    if status == "error":
        detail = error_text or "ask_user interaction failed"
        answers = [f"(error: {detail})" for _ in questions]

    parts = []
    for i, q in enumerate(questions):
        answer = answers[i] if i < len(answers) else "(no answer)"
        lines = [f"Q: {q['question']}"]
        # Include labeled options so the AI can cross-reference letter answers (e.g. "A") with choices
        if q.get("type") == "multiple_choice" and isinstance(q.get("choices"), list):
            option_lines = "\n".join(
                f"  {chr(65 + j)}. {c}" for j, c in enumerate(q.get("choices", []))
            )
            lines.append(f"Options:\n{option_lines}")
        lines.append(f"User answer: {answer}")
        parts.append("\n".join(lines))
    result_text = "\n\n".join(parts)
    return Command(update={"messages": [ToolMessage(result_text, tool_call_id=tool_call_id)]})


@tool("ask_user", description=ASK_USER_TOOL_DESCRIPTION)
def _ask_user(
    questions: list[QuestionInput],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command[Any]:
    """Ask the user one or more questions and return their answers."""
    normalized = _normalize_questions(questions)
    _validate_questions(normalized)
    payload = {
        "type": "ask_user",
        "questions": normalized,
        "tool_call_id": tool_call_id,
    }
    response = interrupt(payload)
    return _parse_answers(response, normalized, tool_call_id)


class AskUserMiddleware(QuickToolsMiddleware):
    """Middleware that provides the always-available ``ask_user`` tool.

    Bundles the tool definition and system-prompt injection as a QuickToolsMiddleware.

    Args:
        system_prompt: System-level instructions injected into every LLM request
            to guide ``ask_user`` usage.  Defaults to ``ASK_USER_SYSTEM_PROMPT``.
    """

    def __init__(self, *, system_prompt: str = ASK_USER_SYSTEM_PROMPT) -> None:
        super().__init__(
            middleware_name="AskUserMiddleware",
            tools=[_ask_user],
            system_prompt=system_prompt,
        )


'''
test
'''