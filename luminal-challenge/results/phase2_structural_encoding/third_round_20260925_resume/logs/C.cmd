PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_export --run results/phase2_structural_encoding/third_round_20260925_resume --stage C_acceptance
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_export --run results/phase2_structural_encoding/third_round_20260925_resume --stage C_export
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_stage_c --run results/phase2_structural_encoding/third_round_20260925_resume --stage C_fixed_work
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_stage_c --run results/phase2_structural_encoding/third_round_20260925_resume --stage C_wall
PYTHONPATH=.reference:. ../venv/bin/python -s -m research.third_round_resume_stage_c --run results/phase2_structural_encoding/third_round_20260925_resume --stage C_public
