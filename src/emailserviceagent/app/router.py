from fastapi import APIRouter, HTTPException

from app.graph import build_graph
from app.schemas import EmailAgentRequest, EmailAgentResponse

router = APIRouter()
email_graph = build_graph()


@router.get("/health")
def health():
    return {"status": "ok", "service": "emailserviceagent"}


@router.post("/generate-email", response_model=EmailAgentResponse)
def generate_email(request: EmailAgentRequest):
    try:
        final_state = email_graph.invoke(
            {
                "request": request.model_dump(),
                "handoff_contract": request.handoff_contract,
                "email_type": "",
                "subject": "",
                "body": "",
                "llm_used": False,
                "microservice_status": "pending",
            }
        )

        return EmailAgentResponse(
            mode="agent",
            email_type=final_state["email_type"],
            subject=final_state["subject"],
            body=final_state["body"],
            microservice_status=final_state["microservice_status"],
            llm_used=final_state["llm_used"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))