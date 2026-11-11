from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.provider import AgentConfigurationError
from app.agent.service import AgentInvocationError, run_agent
from app.api.deps import Database, get_current_user
from app.core.exceptions import BusinessException
from app.core.responses import success
from app.schemas import AgentChatRequest, AgentChatVO, ApiResponse, CurrentUser

router = APIRouter(prefix="/agent", tags=["主 Agent"])


@router.post("/chat", response_model=ApiResponse[AgentChatVO])
def agent_chat(
    request: AgentChatRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(Database),
) -> dict:
    try:
        return success(run_agent(db, user, request))
    except AgentConfigurationError as exception:
        raise BusinessException(f"主 Agent 配置错误：{exception}") from exception
    except AgentInvocationError as exception:
        raise BusinessException(f"主 Agent 暂时不可用：{exception}") from exception

