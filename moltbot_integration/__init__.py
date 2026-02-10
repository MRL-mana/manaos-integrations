# Moltbot × まなOS 統合（分離型・1本ゲート）
# 司令塔=まなOS / 手足=Moltbot（限定権限）

from moltbot_integration.schema import (
    Plan,
    PlanStep,
    PlanScope,
    PlanMetadata,
    PlanConstraints,
    RiskLevel,
    ApprovalRequest,
    ExecuteResult,
    AuditRecord,
)
from moltbot_integration.approval import (
    REQUIRES_APPROVAL_ACTIONS,
    risk_requires_approval,
    action_requires_approval,
    plan_requires_approval,
)
from moltbot_integration.gateway import (
    MoltbotGatewayClient,
    sign_plan_body,
    PLAN_SIGNATURE_HEADER,
)

__all__ = [
    "Plan",
    "PlanStep",
    "PlanScope",
    "PlanMetadata",
    "PlanConstraints",
    "RiskLevel",
    "ApprovalRequest",
    "ExecuteResult",
    "AuditRecord",
    "REQUIRES_APPROVAL_ACTIONS",
    "risk_requires_approval",
    "action_requires_approval",
    "plan_requires_approval",
    "MoltbotGatewayClient",
    "sign_plan_body",
    "PLAN_SIGNATURE_HEADER",
]
