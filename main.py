import asyncio
import csv
import time
from collections import Counter
from database import Database
from validator import EmailValidator
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

console = Console()

class Dashboard:
    def __init__(self, total):
        self.stats = Counter({"Total": total, "Valid": 0, "Invalid": 0, "Risky": 0, "Error": 0, "Cached": 0})
        self.processed = 0
        self.start_time = time.time()

    def update(self, status, is_cached=False):
        self.processed += 1
        self.stats[status] += 1
        if is_cached:
            self.stats["Cached"] += 1

    def generate_layout(self, progress_table):
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(Panel("[bold cyan]🚀 Professional Email Verifier v1.0[/bold cyan]", border_style="blue"))
        
        # Statistics Table
        stats_table = Table(title="Live Statistics", expand=True)
        stats_table.add_column("Category", style="magenta")
        stats_table.add_column("Count", style="green")
        stats_table.add_column("Percentage", style="yellow")
        
        for cat, count in self.stats.items():
            if cat == "Total": continue
            pct = (count / self.processed * 100) if self.processed > 0 else 0
            stats_table.add_row(cat, str(count), f"{pct:.1f}%")
            
        # Overall progress panel
        elapsed = time.time() - self.start_time
        speed = self.processed / elapsed if elapsed > 0 else 0
        info_panel = Panel(
            f"Processed: {self.processed}/{self.stats['Total']}\n"
            f"Speed: {speed:.1f} emails/sec\n"
            f"Elapsed: {elapsed:.1f}s",
            title="Session Info",
            border_style="green"
        )
        
        layout["main"].split_row(
            Layout(stats_table, ratio=2),
            Layout(info_panel, ratio=1)
        )
        
        layout["footer"].update(progress_table)
        return layout

async def worker(queue, validator, db, dashboard, progress, task_id):
    while True:
        email = await queue.get()
        if email is None:
            queue.task_done()
            break
            
        cached = db.get_email_status(email)
        if cached:
            status, details = cached
            dashboard.update(status, is_cached=True)
        else:
            status, details = await validator.validate(email)
            db.save_email_status(email, status, details)
            dashboard.update(status)
            
        progress.update(task_id, advance=1)
        queue.task_done()
        result = (email, status, details)
        # We could yield this or save to a shared list
        _results.append(result)

_results = []

async def main(input_file, output_file, worker_count=50):
    db = Database()
    validator = EmailValidator(db)
    
    # Mock RAG setup
    db.add_domain_knowledge(["mailinator.com", "temp-mail.org"], "disposable")

    emails = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            emails = [row[0] for row in reader if row]
    except FileNotFoundError:
        # Create sample if missing
        emails = [f"user{i}@gmail.com" for i in range(100)] + ["test@mailinator.com", "bad@nonexistent.xxx"]
        with open(input_file, 'w', newline='') as f:
            writer = csv.writer(f)
            for e in emails: writer.writerow([e])

    total = len(emails)
    dashboard = Dashboard(total)
    queue = asyncio.Queue()
    
    for e in emails:
        await queue.put(e)
    
    # Add termination signals
    for _ in range(worker_count):
        await queue.put(None)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    )
    task_id = progress.add_task("Verifying...", total=total)
    
    with Live(dashboard.generate_layout(progress), refresh_per_second=4, screen=True) as live:
        workers = [
            asyncio.create_task(worker(queue, validator, db, dashboard, progress, task_id))
            for _ in range(worker_count)
        ]
        
        while not all(w.done() for w in workers):
            live.update(dashboard.generate_layout(progress))
            await asyncio.sleep(0.25)
            
        await asyncio.gather(*workers)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Email", "Status", "Details"])
        writer.writerows(_results)

if __name__ == "__main__":
    import sys
    inp = sys.argv[1] if len(sys.argv) > 1 else "sample.csv"
    asyncio.run(main(inp, "results.csv"))
