"""HID dictionary relations v1: paid dictionary modes O, P, R(O), R(P) (exploratory).

``search`` is the single owner of the new algorithm. ``worker``/``runner``/``cli`` are
thin execution adapters, ``report``/``audit`` read saved artefacts, ``preserve``
records preservation and the implementation lock, ``ledger`` the controller clock.
Protocol: PROTOCOL_hierarchy_dictionary_v1.md and protocols/hierarchy_dictionary_v1/.
"""
