import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class LogicNode:
    topic: str
    claim: str
    support: List[str]
    intent: str            # technical | procedural | behavioral | style | pattern | meta_cognition
    certainty: str         # definitive | conditional | speculative
    target_table: str      # mapped to your 9 specific tables + building_knowledge
    source: str

@dataclass
class MentalModel:
    origin: str
    nodes: List[LogicNode]
    summary: str 

class TrueSummarizer:
    """
    A real summarizer:
    - Segments by # Titles and Headings
    - Maps intents to your specific 9 Supabase tables
    - Processes 10k+ words into structured LogicNodes
    - Progressive 20-step expansion for building_knowledge
    """

    # Mapping intents to your specific Supabase table names
    INTENT_TO_TABLE = {
        "technical": "rules",
        "procedural": "skills",
        "capability": "capability_registry",
        "behavioral": "traits",
        "persona": "personas",
        "pattern": "interaction_patterns",
        "style": "response_styles",
        "example": "conversation_examples",
        "meta_cognition": "building_knowledge",
        "default": "bot_memory"
    }

    LOGIC_KEYWORDS = {
        "definitive": ["must", "always", "never", "cannot", "guarantees", "required"],
        "conditional": ["if", "unless", "depends", "when", "provided"],
        "procedural": ["step", "first", "next", "then", "process", "workflow"],
        "warning": ["risk", "danger", "avoid", "failure", "critical"]
    }

    def __init__(self, provider_layer: Any, memory_layer: Any):
        self.provider = provider_layer
        self.memory = memory_layer

    async def summarize_and_store(self, instructions: Dict[str, Any]) -> MentalModel:
        raw_text, source = await self._gather(instructions)
        model = self._build_mental_model(raw_text, source)
        
        # This calls your Memory.py to file the nodes away
        await self.memory.store(model)

        # TRIGGER BUILDING KNOWLEDGE EXPANSION
        # Detect if the material is technical/architectural for the builder
        if any(k in raw_text.lower() for k in ["architecture", "module", "component", "refactor"]):
            comp = instructions.get("component_focus", "core_system")
            build_payloads = await self.populate_building_knowledge(raw_text, comp)
            # Hand off the 20-step list to memory for the building_knowledge table
            await self.memory.store_building_logic(build_payloads)

        return model

    async def _gather(self, instructions: Dict[str, Any]) -> (str, str):
        """Gathers based on your 4 layers and specific filenames."""
        if instructions.get("use_url"):
            return (await self.provider.secure_web_fetch(instructions["url_target"]), "url")
        
        if instructions.get("use_md"):
            return (await self.provider.read_local_mds(), "local_files")
            
        if instructions.get("use_logic_tables"):
            tables = ["rules", "skills", "capability_registry", "bot_memory"]
            return (str(await self.provider.secure_db_fetch(tables)), "logic_db")

        if instructions.get("use_op_logic"):
            tables = ["traits", "personas", "interaction_patterns", "response_styles", "conversation_examples"]
            return (str(await self.provider.secure_db_fetch(tables)), "op_db")
            
        raise ValueError("No valid gathering instruction provided")

    def _build_mental_model(self, text: str, source: str) -> MentalModel:
        sections = self._split_by_structure(text)
        nodes: List[LogicNode] = []

        for topic, content in sections.items():
            claim, support = self._extract_claim_and_support(content)
            if not claim:
                claim = f"{topic} defines a core functional parameter."

            intent = self._infer_intent(content, topic)
            
            node = LogicNode(
                topic=topic,
                claim=self._abstract(claim),
                support=[self._abstract(s) for s in support],
                intent=intent,
                certainty=self._infer_certainty(content),
                target_table=self.INTENT_TO_TABLE.get(intent, "bot_memory"),
                source=source
            )

            if self._passes_faithfulness_check(node, content):
                nodes.append(node)

        return MentalModel(
            origin=source,
            nodes=nodes,
            summary=self._synthesize_summary(nodes)
        )

    def _split_by_structure(self, text: str) -> Dict[str, str]:
        headings = re.findall(r'(?m)^#+\s+(.*)$', text)
        chunks = re.split(r'(?m)^#+\s+.*$', text)
        structure = {}
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            title = headings[i - 1].strip() if i > 0 else "System Overview"
            structure[title] = chunk.strip()
        return structure

    def _extract_claim_and_support(self, text: str) -> (Optional[str], List[str]):
        sentences = re.split(r'(?<=[.!?])\s+', text)
        claim = next((s for s in sentences if any(k in s.lower() for k in ["is", "means", "refers", "acts as"])), None)
        support = [s for s in sentences if any(k in s.lower() for k in ["because", "allows", "enables", "leads to", "requires"])]
        return claim, support

    def _abstract(self, sentence: str) -> str:
        sentence = re.sub(r'\b\d{4}\b', 'multiple years', sentence)
        sentence = re.sub(r'\b(for example|such as|e\.g\.)\b.*', '', sentence, flags=re.I)
        return sentence.strip()

    def _infer_intent(self, text: str, topic: str) -> str:
        t = (text + topic).lower()
        if any(k in t for k in ["architecture", "framework", "component", "refactor"]): return "meta_cognition"
        if any(k in t for k in ["must", "never", "rule", "constraint"]): return "technical"
        if any(k in t for k in ["step", "workflow", "process", "skill"]): return "procedural"
        if any(k in t for k in ["trait", "personality", "vibe"]): return "behavioral"
        if any(k in t for k in ["tone", "style", "voice"]): return "style"
        if any(k in t for k in ["pattern", "interaction", "habit"]): return "pattern"
        if any(k in t for k in ["example", "sample", "dialogue"]): return "example"
        return "default"

    def _infer_certainty(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in self.LOGIC_KEYWORDS["definitive"]): return "definitive"
        if any(k in t for k in self.LOGIC_KEYWORDS["conditional"]): return "conditional"
        return "speculative"

    def _passes_faithfulness_check(self, node: LogicNode, source_text: str) -> bool:
        if node.certainty == "definitive" and "may" in source_text.lower(): return False
        return True

    def _synthesize_summary(self, nodes: List[LogicNode]) -> str:
        if not nodes: return "No durable knowledge extracted."
        return f"Consolidated {len(nodes)} nodes across {len(set(n.target_table for n in nodes))} tables."

    # ---------- NEW: 20-STEP BUILDING EXPANSION ----------

    async def populate_building_knowledge(self, raw_mass: str, component_name: str) -> List[Dict[str, Any]]:
        """Scans raw text for 20 specialized steps. Accumulates for Builder.py."""
        steps_manifest = [
            "Component ID", "Architectural Intent", "Variable Mapping", "Data Type Enforcement",
            "Interface Schema", "Causal Linkage", "Dependency Mapping", "State Management",
            "Logic Branching", "Constraint Logging", "Error Modeling", "Edge Case Handling",
            "Security Audit", "Metadata Tagging", "Abstraction Level", "Performance Impact",
            "Conflict Detection", "Scalability Vector", "Refactor Prompting", "Integrity Check"
        ]

        payloads = []
        topic_context = self._extract_topic_context(raw_mass)

        for i, step_name in enumerate(steps_manifest, 1):
            extracted = self._find_step_intelligence(step_name, raw_mass)
            if extracted:
                payloads.append({
                    "step_number": i,
                    "step_name": step_name,
                    "component": component_name,
                    "topic": topic_context,
                    "raw_intelligence": extracted,
                    "source_origin": "learning_cycle",
                    "processed_flag": False
                })
        return payloads

    def _find_step_intelligence(self, step_name: str, mass: str) -> str:
        """Greedy search for any detail related to the 20 specialized steps."""
        keywords = {
            "Variable Mapping": ["var", "const", "env", "key", "input", "output", "argument"],
            "Logic Branching": ["if", "then", "else", "switch", "loop", "branch", "condition"],
            "Error Modeling": ["error", "exception", "catch", "fail", "crash", "try", "warning"],
            "Security Audit": ["proxy", "auth", "token", "secure", "encrypted", "credentials"],
            "Constraint Logging": ["forbidden", "limit", "cannot", "must not", "restrict", "only"]
        }
        
        target_keys = keywords.get(step_name, [step_name.lower()])
        sentences = re.split(r'(?<=[.!?])\s+', mass)
        found_logic = [s.strip() for s in sentences if any(k in s.lower() for k in target_keys)]
        
        return " | ".join(found_logic) if found_logic else ""

    def _extract_topic_context(self, mass: str) -> str:
        """Grabs first heading or first 50 chars for table context."""
        match = re.search(r'(?m)^#+\s+(.*)$', mass)
        return match.group(1).strip() if match else mass[:50].strip()
