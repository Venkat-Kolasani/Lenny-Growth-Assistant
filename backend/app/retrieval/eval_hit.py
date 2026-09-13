def hit(expected_guest: str, guests: list[str]) -> bool:
    needle = expected_guest.lower()
    return any(needle in guest.lower() for guest in guests)
