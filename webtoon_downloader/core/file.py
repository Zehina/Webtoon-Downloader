import re


def slugify_name(file_name: str) -> str:
    """
    Slugifies a file name by removing special characters, replacing spaces with underscores.

    Args:
        name: The original file name

    Returns:
        The slugified file name.
    """
    # Replace leading/trailing whitespace and replace spaces with underscores
    # And remove special characters
    return re.sub(r"[^\w.-]", "", file_name.strip().replace(" ", "_"))
