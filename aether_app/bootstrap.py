import main as legacy

from aether_app.markdown import (
    EnhancedCodeBlock,
    EnhancedMessageBubble,
)
from aether_app.settings import EnhancedSettingsWindow
from aether_app.window import EnhancedLocalAIWindow


def run():
    legacy.CodeBlock = EnhancedCodeBlock
    legacy.MessageBubble = EnhancedMessageBubble
    legacy.SettingsWindow = EnhancedSettingsWindow
    legacy.LocalAIWindow = EnhancedLocalAIWindow
    return legacy.main()
