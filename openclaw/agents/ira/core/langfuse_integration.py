#!/usr/bin/env python3
"""
LANGFUSE INTEGRATION - LLM Observability Dashboard
===================================================

Integration with Langfuse for comprehensive LLM observability:
- Trace all LLM calls (OpenAI, Anthropic, etc.)
- Track token usage and costs
- Monitor latency and performance
- Debug conversation flows
- A/B testing and evaluation

Setup:
    1. Create account at https://langfuse.com
    2. Create a project and get API keys
    3. Set environment variables:
        LANGFUSE_PUBLIC_KEY=pk-...
        LANGFUSE_SECRET_KEY=sk-...
        LANGFUSE_HOST=https://cloud.langfuse.com  # or self-hosted

Usage:
    from core.langfuse_integration import (
        get_langfuse,
        trace_llm_call,
        create_trace,
        LangfuseCallback
    )
    
    # Automatic tracing with decorator
    @trace_llm_call("generate_answer")
    def generate_answer(query: str):
        return openai.chat.completions.create(...)
    
    # Manual tracing
    with create_trace("conversation") as trace:
        trace.span(name="retrieval")
        results = retriever.search(query)
        
        trace.generation(
            name="llm_call",
            model="gpt-4.1",
            input=prompt,
            output=response
        )
"""

import functools
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("ira.langfuse")

T = TypeVar("T")

LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

_LANGFUSE_AVAILABLE = False
_langfuse_client = None

try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
    _LANGFUSE_AVAILABLE = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)
except ImportError:
    logger.debug("Langfuse not installed: pip install langfuse")


@dataclass
class LLMCallMetrics:
    """Metrics for an LLM call."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass  
class TraceMetadata:
    """Metadata for a trace."""
    trace_id: str
    name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    channel: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


TOKEN_COSTS = {
    "gpt-4.1": {"input": 0.002, "output": 0.008},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for an LLM call."""
    costs = TOKEN_COSTS.get(model, TOKEN_COSTS.get("gpt-4.1-mini"))
    if not costs:
        return 0.0
    
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]
    return input_cost + output_cost


def get_langfuse() -> Optional["Langfuse"]:
    """Get or create Langfuse client."""
    global _langfuse_client
    
    if not _LANGFUSE_AVAILABLE:
        return None
    
    if _langfuse_client is None:
        try:
            _langfuse_client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
            )
            logger.info(f"Langfuse client initialized: {LANGFUSE_HOST}")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            return None
    
    return _langfuse_client


class LangfuseTracer:
    """
    Context manager for Langfuse tracing.
    
    Usage:
        with LangfuseTracer("conversation", user_id="user123") as tracer:
            tracer.span("retrieval", input={"query": query})
            results = search(query)
            tracer.end_span(output={"count": len(results)})
            
            tracer.generation(
                name="llm_call",
                model="gpt-4.1",
                input=prompt,
                output=response,
                usage={"input": 100, "output": 50}
            )
    """
    
    def __init__(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        channel: str = "",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ):
        self.name = name
        self.user_id = user_id
        self.session_id = session_id
        self.channel = channel
        self.tags = tags or []
        self.metadata = metadata or {}
        
        self._trace = None
        self._current_span = None
        self._spans_stack = []
        self._start_time = None
    
    def __enter__(self) -> "LangfuseTracer":
        self._start_time = time.time()
        
        langfuse = get_langfuse()
        if langfuse:
            try:
                self._trace = langfuse.trace(
                    name=self.name,
                    user_id=self.user_id,
                    session_id=self.session_id,
                    tags=self.tags + [self.channel] if self.channel else self.tags,
                    metadata={
                        "channel": self.channel,
                        **self.metadata,
                    },
                )
                logger.debug(f"Started Langfuse trace: {self.name}")
            except Exception as e:
                logger.warning(f"Failed to start Langfuse trace: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.time() - self._start_time) * 1000
        
        if self._trace:
            try:
                if exc_type:
                    self._trace.update(
                        status_message=str(exc_val),
                        level="ERROR",
                        metadata={**self.metadata, "error": str(exc_val)},
                    )
                else:
                    self._trace.update(
                        metadata={**self.metadata, "duration_ms": elapsed_ms},
                    )
            except Exception as e:
                logger.warning(f"Failed to end Langfuse trace: {e}")
        
        langfuse = get_langfuse()
        if langfuse:
            try:
                langfuse.flush()
            except Exception as e:
                logger.error(f"Error in __exit__: {e}", exc_info=True)
    
    def span(
        self,
        name: str,
        input: Any = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Any]:
        """Start a new span."""
        if not self._trace:
            return None
        
        try:
            parent = self._current_span if self._current_span else self._trace
            span = parent.span(
                name=name,
                input=input,
                metadata=metadata,
            )
            self._spans_stack.append(self._current_span)
            self._current_span = span
            return span
        except Exception as e:
            logger.warning(f"Failed to create span: {e}")
            return None
    
    def end_span(self, output: Any = None, status: str = "success"):
        """End the current span."""
        if self._current_span:
            try:
                self._current_span.end(output=output)
            except Exception as e:
                logger.warning(f"Failed to end span: {e}")
        
        if self._spans_stack:
            self._current_span = self._spans_stack.pop()
        else:
            self._current_span = None
    
    def generation(
        self,
        name: str,
        model: str,
        input: Any,
        output: Any,
        usage: Dict[str, int] = None,
        metadata: Dict[str, Any] = None,
    ):
        """Record an LLM generation."""
        if not self._trace:
            return
        
        try:
            parent = self._current_span if self._current_span else self._trace
            
            input_tokens = usage.get("input", 0) if usage else 0
            output_tokens = usage.get("output", 0) if usage else 0
            cost = calculate_cost(model, input_tokens, output_tokens)
            
            parent.generation(
                name=name,
                model=model,
                input=input,
                output=output,
                usage={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens,
                    "unit": "TOKENS",
                } if usage else None,
                metadata={
                    "cost_usd": cost,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record generation: {e}")
    
    def event(self, name: str, input: Any = None, output: Any = None, metadata: Dict = None):
        """Record an event."""
        if not self._trace:
            return
        
        try:
            self._trace.event(
                name=name,
                input=input,
                output=output,
                metadata=metadata,
            )
        except Exception as e:
            logger.warning(f"Failed to record event: {e}")
    
    def score(self, name: str, value: float, comment: str = None):
        """Record a score/metric."""
        if not self._trace:
            return
        
        try:
            self._trace.score(
                name=name,
                value=value,
                comment=comment,
            )
        except Exception as e:
            logger.warning(f"Failed to record score: {e}")


@contextmanager
def create_trace(
    name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    channel: str = "",
    **metadata
):
    """Create a Langfuse trace context."""
    tracer = LangfuseTracer(
        name=name,
        user_id=user_id,
        session_id=session_id,
        channel=channel,
        metadata=metadata,
    )
    with tracer:
        yield tracer


def trace_llm_call(
    name: str = None,
    capture_input: bool = True,
    capture_output: bool = True,
):
    """
    Decorator to trace LLM calls with Langfuse.
    
    Automatically captures:
    - Function inputs (if capture_input=True)
    - Function outputs (if capture_output=True)
    - Execution time
    - Errors
    
    Usage:
        @trace_llm_call("generate_answer")
        def generate_answer(query: str, context: dict):
            return openai.chat.completions.create(...)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        trace_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            
            with create_trace(trace_name) as tracer:
                if capture_input:
                    tracer.event("input", input={"args": str(args)[:500], "kwargs": str(kwargs)[:500]})
                
                try:
                    result = func(*args, **kwargs)
                    
                    if capture_output and result:
                        output_str = str(result)[:1000] if result else None
                        tracer.event("output", output=output_str)
                    
                    elapsed_ms = (time.time() - start_time) * 1000
                    tracer.score("latency_ms", elapsed_ms)
                    
                    return result
                    
                except Exception as e:
                    tracer.event("error", output=str(e))
                    raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            
            with create_trace(trace_name) as tracer:
                if capture_input:
                    tracer.event("input", input={"args": str(args)[:500], "kwargs": str(kwargs)[:500]})
                
                try:
                    result = await func(*args, **kwargs)
                    
                    if capture_output and result:
                        output_str = str(result)[:1000] if result else None
                        tracer.event("output", output=output_str)
                    
                    elapsed_ms = (time.time() - start_time) * 1000
                    tracer.score("latency_ms", elapsed_ms)
                    
                    return result
                    
                except Exception as e:
                    tracer.event("error", output=str(e))
                    raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


class OpenAICallbackHandler:
    """
    Callback handler for OpenAI calls to automatically log to Langfuse.
    
    Usage:
        handler = OpenAICallbackHandler(trace_name="chat")
        
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        handler.on_llm_end(response)
    """
    
    def __init__(
        self,
        trace_name: str = "openai_call",
        user_id: str = None,
        session_id: str = None,
    ):
        self.trace_name = trace_name
        self.user_id = user_id
        self.session_id = session_id
        self._tracer = None
        self._start_time = None
    
    def on_llm_start(self, model: str, messages: List[Dict]):
        """Called before LLM call."""
        self._start_time = time.time()
        self._tracer = LangfuseTracer(
            name=self.trace_name,
            user_id=self.user_id,
            session_id=self.session_id,
        )
        self._tracer.__enter__()
        self._model = model
        self._messages = messages
    
    def on_llm_end(self, response):
        """Called after LLM call with response."""
        if not self._tracer:
            return
        
        try:
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            
            output_text = response.choices[0].message.content if response.choices else ""
            
            self._tracer.generation(
                name="completion",
                model=self._model,
                input=self._messages,
                output=output_text,
                usage={"input": input_tokens, "output": output_tokens},
            )
        except Exception as e:
            logger.warning(f"Failed to log LLM response: {e}")
        finally:
            self._tracer.__exit__(None, None, None)
    
    def on_llm_error(self, error: Exception):
        """Called when LLM call fails."""
        if self._tracer:
            self._tracer.__exit__(type(error), error, None)


def flush():
    """Flush all pending Langfuse events."""
    langfuse = get_langfuse()
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse: {e}")


def shutdown():
    """Shutdown Langfuse client."""
    global _langfuse_client
    if _langfuse_client:
        try:
            _langfuse_client.shutdown()
        except Exception as e:
            logger.error(f"Error in shutdown: {e}", exc_info=True)
        _langfuse_client = None


__all__ = [
    "get_langfuse",
    "create_trace",
    "trace_llm_call",
    "LangfuseTracer",
    "OpenAICallbackHandler",
    "LLMCallMetrics",
    "calculate_cost",
    "flush",
    "shutdown",
]


if __name__ == "__main__":
    print("Testing Langfuse Integration\n" + "=" * 50)
    
    if _LANGFUSE_AVAILABLE:
        print("✅ Langfuse available")
        
        with create_trace("test_trace", user_id="test_user") as tracer:
            tracer.span("test_span", input={"query": "test"})
            time.sleep(0.1)
            tracer.end_span(output={"results": 5})
            
            tracer.generation(
                name="test_generation",
                model="gpt-4.1-mini",
                input="Hello",
                output="Hi there!",
                usage={"input": 10, "output": 5},
            )
            
            tracer.score("test_score", 0.95)
        
        print("✅ Test trace created")
        flush()
    else:
        print("⚠️ Langfuse not configured")
        print("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable")
    
    cost = calculate_cost("gpt-4.1-mini", input_tokens=1000, output_tokens=500)
    print(f"✅ Cost calculation: ${cost:.4f} for 1000 in / 500 out tokens")
    
    print("\n✅ Langfuse integration test complete")
