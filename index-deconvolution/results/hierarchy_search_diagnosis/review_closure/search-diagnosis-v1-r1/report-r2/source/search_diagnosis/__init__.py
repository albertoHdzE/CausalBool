"""search-diagnosis-v1: post-hoc diagnostic adapters over the frozen HID-search-v2 owners.

PROTOCOL_hierarchy_search_diagnosis.md. Every module here imports the active
``hierarchy`` package unchanged and adds only diagnostic adapters: no encoder,
decoder, search, leaf builder, opcode or bootstrap is re-implemented.

Import as ``search_diagnosis`` with ``index-deconvolution/experiments`` on the path
(the name ``experiments`` resolves to the root ``src/experiments`` package).
"""
