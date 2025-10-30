# AutifyME Extensions

Optional extensions for AutifyME that provide specialized capabilities with heavy dependencies.

---

## Philosophy

**Keep Core Lean, Extensions Optional**

Extensions are separated from the main AutifyME package to:
- ✅ Avoid bloating core package with unused dependencies
- ✅ Enable opt-in installation only when needed
- ✅ Maintain fast deployment and cold start times
- ✅ Allow independent versioning and updates
- ✅ Support future extensibility without breaking core

---

## Available Extensions

### 1. Google Computer Use

**Purpose:** Browser automation using Gemini 2.5 Computer Use model

**Heavy Dependencies:**
- Playwright (~200MB)
- Chromium browser (~400MB)

**When to Install:**
- Building web scraping workflows
- Automating form submissions
- UI testing automation
- Agentic browser control

**Installation:**
```bash
cd extensions/google_computer_use
uv pip install -e ".[playwright]"
playwright install chromium
```

**Documentation:** [extensions/google_computer_use/README.md](google_computer_use/README.md)

**Detailed Guide:** [docs/architecture/tech/GOOGLE_COMPUTER_USE_GUIDE.md](../docs/architecture/tech/GOOGLE_COMPUTER_USE_GUIDE.md)

---

## Future Extensions

**Planned (not yet implemented):**

- **Veo Video Generation** - Video creation workflows (when needed)
- **Live API Audio Streaming** - Real-time voice conversation (when needed)
- **Advanced Vision Processing** - Computer vision pipelines (heavy CV libraries)
- **PDF Processing** - Document parsing and extraction (heavy parsing libraries)

---

## Extension Development Guidelines

When creating new extensions:

**1. Justify Separation**
- Extension has dependencies >50MB total
- Extension is not universally needed (specialized use case)
- Extension can evolve independently

**2. Structure Requirements**
```
extensions/
  your_extension/
    __init__.py           # Clean API exports
    README.md             # Installation and usage
    pyproject.toml        # Dependencies and metadata
    [module files]
```

**3. Installation Pattern**
```bash
cd extensions/your_extension
uv pip install -e ".[optional-features]"
```

**4. Documentation**
- README in extension directory (quick start)
- Detailed guide in `docs/architecture/tech/` (comprehensive)
- Update this README with new extension

**5. Testing**
- Self-contained tests in extension directory
- CI/CD should test extensions separately (optional workflows)

---

## Why Not Submodules or Separate Repos?

**Considered Alternatives:**
- ❌ Git submodules - Complex for contributors
- ❌ Separate repositories - Harder to maintain coherence
- ❌ Monorepo with Bazel/Nx - Overkill for current scale
- ✅ **Extensions directory** - Simple, clear, maintainable

**Trade-offs:**
- All code in one repo (easier to maintain, test, review)
- Clear separation (via directory + optional install)
- Minimal complexity (just pip install when needed)

---

## Best Practices

**For Core Developers:**
- Always ask: "Does this belong in core or extension?"
- If dependency >50MB → extension
- If specialized use case → extension
- If universally needed → core

**For Extension Users:**
- Only install extensions you actively use
- Update extensions independently
- Report extension-specific issues with `[Extension]` tag

**For Contributors:**
- Follow extension development guidelines above
- Keep extensions loosely coupled from core
- Document installation and usage clearly
- Add tests specific to extension functionality

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Project architectural rules
- [Core Package](../agents/src/autifyme_agents/) - Main AutifyME agents
- [Architecture Docs](../docs/architecture/) - System design documents
