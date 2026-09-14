"""Transport-neutral domain errors for Capability operations."""


class CapabilityDomainError(Exception):
    """Base class for Capability errors translated at the future API boundary."""


class CapabilityNotFoundError(CapabilityDomainError):
    """Raised when an owner-scoped Capability lookup has no result."""


class ParentCapabilityNotFoundError(CapabilityNotFoundError):
    """Raised when a proposed parent is absent from the owner's Capability map."""


class CapabilityValidationError(CapabilityDomainError):
    """Raised when a requested Capability mutation is invalid."""


class CapabilityConflictError(CapabilityDomainError):
    """Raised when a requested Capability mutation conflicts with hierarchy state."""


class CapabilityHierarchyConflictError(CapabilityConflictError):
    """Raised when hierarchy or archive invariants block a mutation."""


class CapabilityFlowNotAccessibleError(CapabilityDomainError):
    """Raised when a requested primary Flow is missing or not readable."""
