# models

Shared Pydantic models: the domain objects and request/response schemas that services and routes
pass between each other.

## Belongs here

- Domain models that more than one component uses.
- Request and response bodies for the routes.
- Enums and value objects those models are built from.

## Does not belong here

- Configuration models — those live in [`config/`](../config/README.md).
- SQLAlchemy ORM tables. Keep the persistence schema separate from the models the API speaks, so a
  column rename is not automatically a breaking API change.
- Anything that performs I/O. Models are data plus validation, nothing else.

## Conventions

- One concept per file, named after the concept in `snake_case`.
- Grouped into a subdirectory per domain, named after that domain, rather than left flat. Nesting
  does not shorten the filename: `k8s_probes/k8s_probe_response.py`. Each domain package
  re-exports its models from `__init__.py`, so callers write
  `from app.models.feature_flags import FeatureFlag` rather than the leaf path.
- Field names are `snake_case`. The `ALL_CAPS` convention is specific to config models, where the
  names double as environment variable names.
- Put validation in the model rather than in the caller, and prefer Pydantic's built-in constraints
  over hand-written checks.
- The class Google docstring (including `Attributes:`) is for developers reading the
  code. The public contract in `/docs` is `model_config = ConfigDict(json_schema_extra=
  {"description": "..."})`, which overrides the docstring in the generated schema.
  Field copy for customers lives on `Field(description=...)`.
