import tkinter as tk
from typing import Optional
from .utils import TooltipProvider
from .config import UIConstants


class TooltipWidget:
    """Individual tooltip widget implementation."""
    
    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = UIConstants.TOOLTIP_DELAY_MS):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: Optional[str] = None
        self._tip: Optional[tk.Toplevel] = None
        
        # Bind events
        widget.bind("<Enter>", self._schedule_show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule_show(self, _event=None):
        """Schedule tooltip to show after delay."""
        self._cancel_show()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_show(self):
        """Cancel scheduled tooltip show."""
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass  # Widget might be destroyed
        self._after_id = None

    def _show(self):
        """Show the tooltip."""
        if self._tip or not self.text:
            return
            
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            
            tip = tk.Toplevel(self.widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(
                tip,
                text=self.text,
                background=UIConstants.TOOLTIP_BACKGROUND,
                relief="solid",
                borderwidth=1,
                justify="left",
                padx=UIConstants.WIDGET_SPACING,
                pady=UIConstants.SMALL_SPACING,
                wraplength=UIConstants.TOOLTIP_WRAP_LENGTH,
            )
            label.pack()
            self._tip = tip
            
        except tk.TclError:
            # Widget might be destroyed, ignore
            pass

    def _hide(self, _event=None):
        """Hide the tooltip."""
        self._cancel_show()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass  # Already destroyed
        self._tip = None

    def destroy(self):
        """Cleanup tooltip resources."""
        self._hide()


class TkinterTooltipProvider:
    """Tkinter implementation of tooltip provider."""
    
    def __init__(self):
        self._tooltips = []
    
    def attach_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Attach tooltip to widget."""
        if text.strip():  # Only attach if there's actual text
            tooltip = TooltipWidget(widget, text)
            self._tooltips.append(tooltip)
    
    def cleanup(self):
        """Cleanup all tooltips."""
        for tooltip in self._tooltips:
            tooltip.destroy()
        self._tooltips.clear()


# Backward compatibility
class ParamHint(TooltipWidget):
    """Backward compatibility class."""
    pass


def attach(widget: tk.Widget, text: str) -> TooltipWidget:
    """Create and attach tooltip to widget. Backward compatibility function."""
    return TooltipWidget(widget, text)

