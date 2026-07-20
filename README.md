# Hermes Council

Hermes Council is a pip-installable plugin foundation for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Installation

```bash
pip install .
```

The `hermes-agent-council` distribution is not published to PyPI yet.

The package exposes the `hermes-council` entry point in the `hermes_agent.plugins` group. Hermes discovers the entry point and calls its package-level `register(ctx)` function when the plugin is enabled.

Protocol behavior is landing in follow-up issues. This foundation does not yet provide council behavior, commands, tools, storage, or inference.

## License

MIT
