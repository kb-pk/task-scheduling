import importlib
import pkgutil
from typing import Dict, List, Tuple, Type


def _import_all_method_modules() -> None:
    """Import all modules under `scheduler.methods` to trigger registrations.

    Method classes are decorated with `@register_method` in `scheduler.Parametrs`.
    Importing the modules ensures the registry gets populated.
    """
    try:
        import scheduler.methods as methods_pkg  # type: ignore
    except Exception:
        return

    for modinfo in pkgutil.iter_modules(getattr(methods_pkg, "__path__", [])):
        name = modinfo.name
        if name.startswith("_"):
            continue
        qualname = f"{methods_pkg.__name__}.{name}"
        try:
            importlib.import_module(qualname)
        except Exception:
            # Skip modules that fail to import
            continue


def discover_methods() -> List[Tuple[str, Type[object]]]:
    """
    Return a list of (display_name, method_class) discovered via the
    registry in `scheduler.Parametrs`.
    """
    # Import all method modules to populate the registry
    _import_all_method_modules()

    try:
        from scheduler.Parametrs import _METHOD_REGISTRY  # type: ignore
    except Exception:
        return []

    items: List[Tuple[str, Type[object]]] = list(_METHOD_REGISTRY.items())
    items.sort(key=lambda x: x[0].lower())
    return items


def method_name_map() -> Dict[str, Type[object]]:
    """Return mapping {display_name: method_class}."""
    return {display: cls for display, cls in discover_methods()}
