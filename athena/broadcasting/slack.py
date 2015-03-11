from tabulate import tabulate
from athena.utils.config import Config


def send_msg(text, username=None, channel=None, icon=None):
    """
    Send a message to Slack
    """

    from slacker import Slacker

    config = Config.load_default()
    if not config.slack.token:
        raise ValueError("You must provide a Slack token in your configuration!")
    if not channel and not config.slack.default_channel:
        raise ValueError("You must provide a channel to send the Slack message to!")

    slack = Slacker(config.slack.token)

    ch = channel or config.slack.default_channel
    if not ch.startswith("#"):
        ch = "#" + ch
    u = username or config.slack.default_username
    i = icon or config.slack.default_icon
    icon_url = None
    icon_emoji = None
    if i and i.startswith(":") and i.endswith(":"):
        icon_emoji = i
    else:
        icon_url = i

    response = slack.chat.post_message(ch, text, username=u, icon_url=icon_url, icon_emoji=icon_emoji)
    return response


def send_table(title, headers, data, username, channel, icon):
    t = title or ""
    msg = '\n{} ```{}``` '.format(
        t, tabulate(data, headers=headers, tablefmt="plain", numalign='left'))
    send_msg(msg, username, channel, icon)
