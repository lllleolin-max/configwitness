# Contributing

Install a normal wheel, run `python -m unittest discover -s tests -v`,
`python tools/workflow.py`, and `python tools/contrast.py`. Tests use the standard
library. Core support starts at Python 3.11; CI covers Linux/Windows 3.11/3.14.

For a new predicate, update the strict schema, production evaluator, independent
checker and independently written exhaustive oracle. Include a counterexample,
missing/null/type boundaries and bounded-search behavior. Do not reuse the
production predicate in reference tests. Keep proposal input binding, exact
cost accounting and full original constraint checks intact.

Pull requests should explain a concrete user failure, affected subset, tests,
and limits. No dependency or generic new expression language is needed merely
to grow scope. Bug reports with small synthetic data are welcome. MIT licensing
permits reuse; contributed code should be compatible with it.
