"""
Context Debugging and Monitoring Utilities
Helps debug and optimize the smart context system
"""

import json
from typing import Dict, Any
from dataclasses import asdict
from logger import json_logger as logger


class ContextDebugger:
    """Utility class for debugging and monitoring context efficiency"""
    
    def __init__(self):
        self.context_stats = {
            "total_requests": 0,
            "by_intent": {},
            "by_scope": {},
            "avg_context_size": 0,
            "cache_hits": 0
        }
    
    def log_context_request(self, context_request, context_data: Dict[str, Any]):
        """Log context request for analysis"""
        self.context_stats["total_requests"] += 1
        
        # Track by intent
        intent_str = context_request.intent.value
        if intent_str not in self.context_stats["by_intent"]:
            self.context_stats["by_intent"][intent_str] = 0
        self.context_stats["by_intent"][intent_str] += 1
        
        # Track by scope
        scope_str = context_request.scope.value
        if scope_str not in self.context_stats["by_scope"]:
            self.context_stats["by_scope"][scope_str] = 0
        self.context_stats["by_scope"][scope_str] += 1
        
        # Calculate context size
        context_size = self._calculate_context_size(context_data)
        self.context_stats["avg_context_size"] = (
            (self.context_stats["avg_context_size"] * (self.context_stats["total_requests"] - 1) + context_size) 
            / self.context_stats["total_requests"]
        )
        
        logger.info(f"Context request logged - Intent: {intent_str}, Scope: {scope_str}, Size: {context_size} chars")
    
    def _calculate_context_size(self, context_data: Dict[str, Any]) -> int:
        """Calculate approximate context size in characters"""
        try:
            return len(json.dumps(context_data, default=str))
        except:
            return 0
    
    def get_context_efficiency_report(self) -> Dict[str, Any]:
        """Generate efficiency report"""
        return {
            "total_requests": self.context_stats["total_requests"],
            "most_common_intent": max(self.context_stats["by_intent"].items(), key=lambda x: x[1]) if self.context_stats["by_intent"] else None,
            "most_common_scope": max(self.context_stats["by_scope"].items(), key=lambda x: x[1]) if self.context_stats["by_scope"] else None,
            "avg_context_size_chars": round(self.context_stats["avg_context_size"], 2),
            "intent_distribution": self.context_stats["by_intent"],
            "scope_distribution": self.context_stats["by_scope"]
        }
    
    def log_context_comparison(self, old_context_size: int, new_context_size: int, intent: str):
        """Log comparison between old and new context systems"""
        reduction_percent = ((old_context_size - new_context_size) / old_context_size) * 100 if old_context_size > 0 else 0
        
        logger.info(
            f"Context optimization for {intent}: "
            f"Old: {old_context_size} chars, New: {new_context_size} chars, "
            f"Reduction: {reduction_percent:.1f}%"
        )


def debug_context_keys(context_data: Dict[str, Any]) -> Dict[str, Any]:
    """Debug helper to analyze context structure"""
    debug_info = {
        "total_keys": len(context_data),
        "key_types": {},
        "key_sizes": {},
        "nested_structures": {}
    }
    
    for key, value in context_data.items():
        # Track type
        debug_info["key_types"][key] = type(value).__name__
        
        # Track size
        if isinstance(value, (list, dict)):
            debug_info["key_sizes"][key] = len(value)
            if isinstance(value, list) and value:
                debug_info["nested_structures"][key] = type(value[0]).__name__
        else:
            debug_info["key_sizes"][key] = len(str(value)) if value else 0
    
    return debug_info


def validate_context_completeness(context_data: Dict[str, Any], required_keys: list) -> Dict[str, Any]:
    """Validate that context has required keys"""
    missing_keys = [key for key in required_keys if key not in context_data]
    empty_keys = [key for key in required_keys if key in context_data and not context_data[key]]
    
    return {
        "is_complete": len(missing_keys) == 0,
        "missing_keys": missing_keys,
        "empty_keys": empty_keys,
        "completeness_score": (len(required_keys) - len(missing_keys)) / len(required_keys) if required_keys else 1.0
    }


# Global debugger instance
context_debugger = ContextDebugger()
