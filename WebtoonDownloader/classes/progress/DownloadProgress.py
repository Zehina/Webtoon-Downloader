from rich.progress import (
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    Progress, 
    TextColumn, 
    TimeRemainingColumn,
    ProgressColumn,
    SpinnerColumn
)
from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style
from rich.console import Console
from rich.logging import RichHandler

class CustomTransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text(f"?", style="progress.data.speed", justify='center')
        return Text(f"{task.speed:2.0f} {task.fields.get('type')}/s", style="progress.data.speed", justify='center')

class DownloadProgress(Progress):
    def __init__(self):
        super().__init__(    
            TextColumn("{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.2f}%",
            "•",
            SpinnerColumn(style="progress.data.speed"),
            CustomTransferSpeedColumn(),
            "•",
            TextColumn("[green]{task.completed:>02d}[/]/[bold green]{task.fields[rendered_total]}[/]", justify="left"),
            SpinnerColumn(),
            "•",
            TimeRemainingColumn(),
            transient=True,
            refresh_per_second=20
        )