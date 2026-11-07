import uuid

from fastapi import Depends, Request

from app.core.auth import AuthUser, current_user
from app.core.database import get_session
from app.services import catalog
from app.services.common import Ctx


def get_ctx(request: Request, user: AuthUser = Depends(current_user), session=Depends(get_session)) -> Ctx:
    """Kitchen comes ONLY from the verified JWT subject, never from request input (Rev 3 I.2)."""
    uid = uuid.UUID(user.user_id)
    kid = catalog.resolve_kitchen_id(session, uid)
    return Ctx(session=session, user_id=uid, kitchen_id=kid,
               request_id=request.headers.get("x-request-id") or uuid.uuid4().hex)
