import re


ID_EXPR = r"\d{17,19}"
USER_MENTION_EXPR = fr"<@!?({ID_EXPR})>"
ROLE_MENTION_EXPR = fr"<@&({ID_EXPR})>"
CHANNEL_MENTION_EXPR = f"<#({ID_EXPR})>"
EMOJI_EXPR = (
    fr"<(?P<animated>a?):(?P<name>[_a-zA-Z0-9]{{2,32}}):(?P<id>{ID_EXPR})>"
)

ID_REGEX = re.compile(ID_EXPR)
USER_MENTION_REGEX = re.compile(USER_MENTION_EXPR)
ROLE_MENTION_REGEX = re.compile(ROLE_MENTION_EXPR)
CHANNEL_MENTION_REGEX = re.compile(CHANNEL_MENTION_EXPR)
EMOJI_REGEX = re.compile(EMOJI_EXPR)

USER_MENTION_OR_ID_REGEX = re.compile(fr"(?:{USER_MENTION_EXPR})|{ID_EXPR}")
ROLE_OR_ID_REGEX = re.compile(fr"(?:{ROLE_MENTION_EXPR})|{ID_EXPR}")
CHANNEL_OR_ID_REGEX = re.compile(fr"(?:{CHANNEL_MENTION_EXPR})|{ID_EXPR}")
