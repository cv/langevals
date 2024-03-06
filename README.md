# LangEvals

A Python package for aggregating various language model evaluation tools into a single platform. This package allows developers to evaluate the quality of language models using a variety of evaluators, which can be run locally or through an API.

If there is an evaluation missing that you want to use, LangEvals makes it easier to add new evaluators and bring them under a standard interface, by following the contributing guide below.

# Contributing

LangEvals is a monorepo and has many subpackages with different dependencies for each evaluator library or provider. We use poetry to install all dependencies and create a virtual env for each sub-package to make sure they are fully isolated. Given this complexity, to make it easier to contribute to LangEvals we recomend using VS Code for the development. Before opening up on VS Code though, you need to make sure to install all dependencies, generating thus the .venv for each package:

```
make install
```

This will also generate the `langevals.code-workspace` file, creating a different workspace per evaluator and telling VS Code which venv to use for each. Then, open this file on vscode and click the "Open Workspace" button

## Adding New Evaluators

To add a completely new evaluator for a library or API that is not already implemented, copy the `evaluators/example` folder, and follow the `example/word_count.py` boilerplate to implement your own evaluator, adding the dependencies on `pyproject.toml`, and testing it properly, following the `test_word_count.py` example.

If you want to add a new eval to an existing evaluator package (say, if OpenAI launches a new API for example), simply create a new Python file next to the existing ones.

To test it all together, run:

```
make lock
make install
make test
```