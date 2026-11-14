# Markdown Knowledge Density Optimizer (`compress_md.py`)

## Overview

This utility is a core component of the **Pilot for Trades** "Solo-Founder" workflow. Its purpose is to transform human-readable Markdown documentation into **High-Density Shorthand (HDS)** optimized for LLM context windows (Gemini, Claude, GPT).

By stripping "connective tissue" and linguistic "fluff," this script reduces token usage by **30-60%** without losing the underlying architectural logic or constraints required for the SDLC process.

---

## Features

* **Recursive Processing**: Automatically crawls the specified directory and all sub-folders.
* **Smart Filtering**: Identifies "Source" `.md` files and ignores existing `.min.md` files to prevent recursive compression.
* **Atomic Overwrites**: Automatically updates existing `.min.md` files, ensuring the AI always has the latest rules.
* **Path Agnostic**: Supports both absolute (`/Users/path/...`) and relative (`./.roo`) folder paths.

---

## The 4-Tier Compression Logic

The script applies an aggressive minimization regex that targets four specific categories of "token-wasters":

1. **Politeness & Intent**: Removes words like *please, ensure, and would like to*.
2. **Articles & Connectives**: Strips *the, a, an, and, which*—relying on Markdown's structural hierarchy for meaning.
3. **Prepositions**: Removes spatial/relational transitions that are inferred by proximity in prompts.
4. **Meta-References**: Removes self-referential language like *i, me, my, and your* to keep the agent focused strictly on the task.

---

## Usage

### Installation

Ensure you have Python 3.x installed. No external dependencies are required.

### Execution

Run the script from your terminal by passing the target folder as an argument:

```bash
# Relative path (standard for Roo Code projects)
python compress_md.py .roo

# Absolute path
python compress_md.py /path/to/project/Pilot for TradesAI/.roo

```

### Output

The script will generate a companion file for every source file found:

* `Source`: `.roo/rules-architect/design.md`
* `Compressed`: `.roo/rules-architect/design.min.md`

---

## Integration with Roo Code

To successfully execute the **solo-company process** and achieve exponential efficiency, follow this workflow:

1. **Write in Human**: Maintain your complex architectural thoughts in the standard `.md` files.
2. **Compress**: Run `compress_md.py` before starting a new major task or switching modes.
3. **Agent Loading**: Configure your **Orchestrator** or specialized modes to prioritize `.min.md` files for context to save on API costs and prevent context window saturation.

---

## Project Context: Pilot for Trades

This tool supports the rapid development of the **Pilot for Trades** platform—a voice-controlled, AI-powered quoting tool for electrical contractors. By keeping context slim, we ensure the AI can handle complex tasks like **NEC code compliance** and **QuickBooks bi-directional sync** without hitting token limits.
