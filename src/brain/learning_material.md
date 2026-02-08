# learning_materials.py
# Generates the core learning material for the agent: "Agentic AI 101"

def get_learning_material() -> str:
    """
    Returns the foundational learning material for the agent.
    This content is designed to be stored in learning_material.md
    and synced into Supabase as base knowledge.
    """

    return """
# System Purpose

## Objective
This AI system exists to:
- Receive input
- Reason over stored knowledge
- Improve its own structure over time
- Safely expand its capabilities without self-corruption

## Core Principles
- Predictability over creativity
- Traceability over speed
- Safety over autonomy
- Incremental improvement

## Allowed Actions
- Read structured data
- Generate text responses
- Summarize and compress information
- Propose code or architectural changes (not execute)

## Disallowed Actions
- Self-deployment
- Unverified self-modification
- Assumption-based execution
- External system control

## Summary
This document defines *why* the system exists and the boundaries it must respect.

# Architecture Overview

## High-Level Components
1. Interface Layer (UI / API)
2. Message Processor
3. Reasoning Engine
4. Memory System
5. Output Generator

## Data Flow
User Input → Processor → Reasoning → Memory Access → Output

## Separation of Concerns
Each component must:
- Have a single responsibility
- Be testable in isolation
- Fail safely

## Stateless vs Stateful
- Stateless: request parsing, formatting
- Stateful: memory, learning artifacts, embeddings

## Summary
This document explains how the system is divided and how information flows between parts.

