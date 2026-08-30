"""Slice 1 has no documentary/DaVinci package.

Required later interface (not implemented):

    def build_documentary_package(investigation_id: str) -> dict:
        raise RuntimeError("documentary_package is UNAVAILABLE")

Must mark reconstructions: DOCUMENTED, ARCHIVAL, RECONSTRUCTION, SIMULATION, HYPOTHESIS.
Never present generated imagery as actual footage.
"""
