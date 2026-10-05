"""HID multilevel v1: reversible multi-width, multi-level word abstraction (exploratory).

``search`` is the single owner of the new algorithm. ``worker``/``runner``/``cli`` are
thin execution adapters, ``report``/``audit`` read saved artefacts, ``preserve``
records preservation and the implementation lock, ``ledger`` the controller clock.
Protocol: PROTOCOL_hierarchy_multilevel_v1.md and protocols/hierarchy_multilevel_v1/.
"""
