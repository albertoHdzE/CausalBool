# U2/U3 ticket — isolated dependency extension

Status: approved for this packet's isolated development and execution when activated by the user. Active sibling integration is not authorized. The previous G deferral remains historical; this ticket supplies a route for a new run only.

## U2 owner and API

Owner: ../series-deconvolution/src/seqdecon/operators.py. Existing gaps remains unchanged. Add only:

    token_occurrence_frames(tokens: Sequence[int], value: int) -> list[int]

Input is a finite sequence of nonnegative built-in integers and a nonnegative built-in integer target. Reject booleans and noninteger or negative values with ValueError, validating the whole input before returning a result. Empty sequence and absent target yield []. Return every zero-based frame i where tokens[i] == value, in increasing order, including consecutive equal frames. This is occurrence extraction, not change detection.

Block slicing/tokenization stays in the thin study orchestrator using the accepted partition declaration. Do not put network semantics in seqdecon or copy its extractor into CausalBool production code. The audit may independently check membership as an explicitly named run-local audit exception.

Before copying, read sibling CLAUDE.md and TRANSFERENCE.md, and relevant owner tests. Snapshot the exact current package bytes and status read-only. Extend only an isolated copy of src/seqdecon/operators.py and a dedicated new test file. Deliver an unapplied patch and an archive of the importable package used. Do not patch the active sibling, install the package, modify its ledgers or run its OEIS/finance jobs.

Set the isolated OPERATOR_GROUP_VERSION and registry version to causal-grouping-gap-v1, and add a declaration for token_occurrence_frames with its domain and target-value parameter. Preserve existing operator declarations and bodies. Record both old and new operator_group_hash plus full source hashes. These identities are specific to this new ordering benchmark and do not revise any old finance null or result. Do not claim registry hashing alone covers implementation; full source hashes are mandatory.

## U3 import route

Run with the existing CausalBool venv interpreter. Explicit PYTHONPATH entries, in order:
1. absolute CausalBool/index-deconvolution/src;
2. absolute CausalBool/index-deconvolution/results/causal_abstraction_validation/abstraction-validation-v1-r1-source-r2;
3. absolute isolated-series-copy/src.

Set PYTHONDONTWRITEBYTECODE=1; disable pytest's cache; no global environment or .pth edits. Assert before production that deconvolution and all model owners resolve to the declared active sources, study to the adopted source-r2, and seqdecon and seqdecon.operators to the isolated package. Record resolved paths and hashes; reject shadow imports. Source owners are read-only.

The isolated dependency may be developed and exercised without another supervisor turn if all packet gates pass. Its upstream adoption remains a later decision. Missing imports are a blocker to report, not permission to create another owner or install dependencies.
