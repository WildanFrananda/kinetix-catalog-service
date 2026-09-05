class ServiceIdentityError(RuntimeError):
    """Raised when this service's own mTLS material is missing or malformed.

    Separate from a TLS handshake failure on purpose: this one means the files on disk are
    wrong, and the message should send someone to the PKI rather than to the network.
    """
