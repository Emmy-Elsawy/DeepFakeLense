"""
RAG Store re-export for DeepFakeLens.
Aliases sys.modules['rag_store'] directly to agents.rag_store.rag_store.
"""

import sys
from agents.rag_store import rag_store as _real_rag_store

sys.modules["rag_store"] = _real_rag_store

from agents.rag_store.rag_store import *
