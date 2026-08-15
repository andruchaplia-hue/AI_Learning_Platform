import logging

logger = logging.getLogger(__name__)

# Try importing kernel_function from semantic_kernel if available
try:
    from semantic_kernel.functions import kernel_function
except ImportError:
    # Decorator fallback if semantic_kernel is importing or mock environment
    def kernel_function(name=None, description=None):
        def decorator(func):
            func.__kernel_function_name__ = name or func.__name__
            func.__kernel_function_description__ = description or ""
            return func
        return decorator
