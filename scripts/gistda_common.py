"""Shared, area-neutral validation helpers for bounded GISTDA collection."""

ENDPOINT = 'https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/1day'


class CandidateError(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result
