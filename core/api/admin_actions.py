from core.infrastructure.observability.admin_action_audit import declare_admin_actions

CATEGORY_CREATE = "catalog.category_create"
CATEGORY_UPDATE = "catalog.category_update"
CATEGORY_DELETE = "catalog.category_delete"

ADMIN_ACTIONS = (
    CATEGORY_CREATE,
    CATEGORY_UPDATE,
    CATEGORY_DELETE,
)

declare_admin_actions(ADMIN_ACTIONS)
