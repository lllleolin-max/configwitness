# Security and reporting

This tool does not authenticate input or read live cluster state. The source
fingerprint detects mismatched proposals, not a malicious replacement of both
input and proposal. Do not publish secrets in provider traces or generated JSON.
No code evaluation, shell execution or network access occurs in the SDK.

State bounds control enumeration, not every possible resource dimension. Apply
process CPU/memory limits to hostile input. The finite model is not a statement
of production availability, cloud IAM permissions or disaster recovery readiness.

Report defects with a minimal nonsecret input, expected versus actual status,
Python version and release/commit. Use a private maintainer channel for sensitive
material when one is established; do not place live credentials or internal fleet
names in public issues. At this initial release no private reporting address or
response-time commitment is established.
