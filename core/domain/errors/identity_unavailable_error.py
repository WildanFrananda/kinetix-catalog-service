class IdentityUnavailableError(Exception):
    def __init__(self, merchant_principal_id: str, reason: str) -> None:
        super().__init__(
            f"identity did not answer about merchant {merchant_principal_id}: {reason}"
        )
        self.merchant_principal_id: str = merchant_principal_id
        self.reason: str = reason
