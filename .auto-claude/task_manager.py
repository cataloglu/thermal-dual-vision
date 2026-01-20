#!/usr/bin/env python3
"""
Auto-Claude Task Manager
Görev yönetim sistemi - task.json dosyalarını yönetir
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
# Renkler
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
# Emojiler
EMOJI = {
    'pending': '⏳',
    'in_progress': '🚀',
    'completed': '✅',
    'blocked': '🚫',
    'failed': '❌',
    'info': 'ℹ️',
    'success': '🎉',
    'error': '⚠️',
    'folder': '📁',
    'file': '📄',
    'progress': '📊'
}
class TaskManager:
    def __init__(self, specs_dir: str = ".auto-claude/specs"):
        self.specs_dir = Path(specs_dir)
        if not self.specs_dir.exists():
            print(f"{EMOJI['error']} Specs klasörü bulunamadı: {self.specs_dir}")
            sys.exit(1)
    def load_task(self, task_id: str) -> Optional[Dict]:
        """Görev dosyasını yükle"""
        task_file = self.specs_dir / task_id / "task.json"
        if not task_file.exists():
            return None
        with open(task_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    def save_task(self, task_id: str, task_data: Dict):
        """Görev dosyasını kaydet"""
        task_file = self.specs_dir / task_id / "task.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
    def get_all_tasks(self) -> List[Dict]:
        """Tüm görevleri listele"""
        tasks = []
        for task_dir in sorted(self.specs_dir.iterdir()):
            if task_dir.is_dir():
                task = self.load_task(task_dir.name)
                if task:
                    task['id'] = task_dir.name
                    tasks.append(task)
        return tasks
    def list_tasks(self, status_filter: Optional[str] = None):
        """Görevleri listele"""
        tasks = self.get_all_tasks()
        if status_filter:
            tasks = [t for t in tasks if t.get('status') == status_filter]
        if not tasks:
            print(f"{EMOJI['info']} Görev bulunamadı!")
            return
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{EMOJI['folder']} GÖREV LİSTESİ{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        for task in tasks:
            status = task.get('status', 'pending')
            emoji = EMOJI.get(status, '❓')
            # Renk seçimi
            if status == 'completed':
                color = Colors.OKGREEN
            elif status == 'in_progress':
                color = Colors.OKCYAN
            elif status in ['failed', 'blocked']:
                color = Colors.FAIL
            else:
                color = Colors.WARNING
            print(f"{emoji} {color}{Colors.BOLD}{task['id']}{Colors.ENDC}")
            print(f"   {Colors.BOLD}Başlık:{Colors.ENDC} {task.get('title', 'N/A')}")
            print(f"   {Colors.BOLD}Durum:{Colors.ENDC} {color}{status}{Colors.ENDC}")
            if task.get('started_at'):
                print(f"   {Colors.BOLD}Başlangıç:{Colors.ENDC} {task['started_at']}")
            if task.get('completed_at'):
                print(f"   {Colors.BOLD}Tamamlanma:{Colors.ENDC} {task['completed_at']}")
            print()
    def show_progress(self):
        """İlerleme durumunu göster"""
        tasks = self.get_all_tasks()
        total = len(tasks)
        if total == 0:
            print(f"{EMOJI['info']} Görev bulunamadı!")
            return
        # Durum sayıları
        counts = {
            'completed': len([t for t in tasks if t.get('status') == 'completed']),
            'in_progress': len([t for t in tasks if t.get('status') == 'in_progress']),
            'pending': len([t for t in tasks if t.get('status') == 'pending']),
            'blocked': len([t for t in tasks if t.get('status') == 'blocked']),
            'failed': len([t for t in tasks if t.get('status') == 'failed']),
        }
        # Progress bar
        progress_pct = (counts['completed'] / total) * 100
        bar_length = 40
        filled = int(bar_length * counts['completed'] / total)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{EMOJI['progress']} PROJE İLERLEMESİ{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        print(f"{Colors.BOLD}Toplam Görev:{Colors.ENDC} {total}")
        print(f"\n{Colors.OKGREEN}{bar}{Colors.ENDC} {progress_pct:.1f}%\n")
        print(f"{EMOJI['completed']} {Colors.OKGREEN}Tamamlanan:{Colors.ENDC} {counts['completed']}")
        print(f"{EMOJI['in_progress']} {Colors.OKCYAN}Devam Eden:{Colors.ENDC} {counts['in_progress']}")
        print(f"{EMOJI['pending']} {Colors.WARNING}Bekleyen:{Colors.ENDC} {counts['pending']}")
        print(f"{EMOJI['blocked']} {Colors.FAIL}Engellenen:{Colors.ENDC} {counts['blocked']}")
        print(f"{EMOJI['failed']} {Colors.FAIL}Başarısız:{Colors.ENDC} {counts['failed']}")
        print()
    def start_task(self, task_id: str):
        """Görevi başlat"""
        task = self.load_task(task_id)
        if not task:
            print(f"{EMOJI['error']} Görev bulunamadı: {task_id}")
            return
        task['status'] = 'in_progress'
        task['started_at'] = datetime.now().isoformat()
        self.save_task(task_id, task)
        print(f"{EMOJI['success']} {Colors.OKGREEN}Görev başlatıldı:{Colors.ENDC} {task_id}")
        print(f"   {task.get('title', 'N/A')}")
    def complete_task(self, task_id: str):
        """Görevi tamamla"""
        task = self.load_task(task_id)
        if not task:
            print(f"{EMOJI['error']} Görev bulunamadı: {task_id}")
            return
        task['status'] = 'completed'
        task['completed_at'] = datetime.now().isoformat()
        self.save_task(task_id, task)
        print(f"{EMOJI['success']} {Colors.OKGREEN}Görev tamamlandı:{Colors.ENDC} {task_id}")
        print(f"   {task.get('title', 'N/A')}")
    def fail_task(self, task_id: str):
        """Görevi başarısız olarak işaretle"""
        task = self.load_task(task_id)
        if not task:
            print(f"{EMOJI['error']} Görev bulunamadı: {task_id}")
            return
        task['status'] = 'failed'
        self.save_task(task_id, task)
        print(f"{EMOJI['failed']} {Colors.FAIL}Görev başarısız:{Colors.ENDC} {task_id}")
    def block_task(self, task_id: str):
        """Görevi engelle"""
        task = self.load_task(task_id)
        if not task:
            print(f"{EMOJI['error']} Görev bulunamadı: {task_id}")
            return
        task['status'] = 'blocked'
        self.save_task(task_id, task)
        print(f"{EMOJI['blocked']} {Colors.WARNING}Görev engellendi:{Colors.ENDC} {task_id}")
    def next_task(self):
        """Sıradaki görevi öner"""
        tasks = self.get_all_tasks()
        pending = [t for t in tasks if t.get('status') == 'pending']
        if not pending:
            print(f"{EMOJI['info']} Bekleyen görev yok!")
            return
        next_task = pending[0]
        print(f"\n{Colors.BOLD}{EMOJI['info']} Sıradaki Görev:{Colors.ENDC}")
        print(f"   ID: {Colors.OKCYAN}{next_task['id']}{Colors.ENDC}")
        print(f"   Başlık: {next_task.get('title', 'N/A')}")
        print(f"\n{Colors.BOLD}Başlatmak için:{Colors.ENDC}")
        print(f"   python .auto-claude/task_manager.py start {next_task['id']}")
        print()
def main():
    if len(sys.argv) < 2:
        print(f"""
{Colors.BOLD}{Colors.HEADER}Auto-Claude Task Manager{Colors.ENDC}
{Colors.BOLD}Kullanım:{Colors.ENDC}
  python .auto-claude/task_manager.py <komut> [parametreler]
{Colors.BOLD}Komutlar:{Colors.ENDC}
  {Colors.OKCYAN}list [status]{Colors.ENDC}       - Görevleri listele (status: pending, in_progress, completed, blocked, failed)
  {Colors.OKCYAN}progress{Colors.ENDC}            - İlerleme durumunu göster
  {Colors.OKCYAN}start <task_id>{Colors.ENDC}     - Görev başlat
  {Colors.OKCYAN}complete <task_id>{Colors.ENDC}  - Görev tamamla
  {Colors.OKCYAN}fail <task_id>{Colors.ENDC}      - Görev başarısız
  {Colors.OKCYAN}block <task_id>{Colors.ENDC}     - Görev engelle
  {Colors.OKCYAN}next{Colors.ENDC}                - Sıradaki görevi öner
{Colors.BOLD}Örnekler:{Colors.ENDC}
  python .auto-claude/task_manager.py list
  python .auto-claude/task_manager.py list pending
  python .auto-claude/task_manager.py progress
  python .auto-claude/task_manager.py start 01-project-structure
  python .auto-claude/task_manager.py next
        """)
        sys.exit(0)
    manager = TaskManager()
    command = sys.argv[1]
    if command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        manager.list_tasks(status)
    elif command == "progress":
        manager.show_progress()
    elif command == "start":
        if len(sys.argv) < 3:
            print(f"{EMOJI['error']} Task ID gerekli!")
            sys.exit(1)
        manager.start_task(sys.argv[2])
    elif command == "complete":
        if len(sys.argv) < 3:
            print(f"{EMOJI['error']} Task ID gerekli!")
            sys.exit(1)
        manager.complete_task(sys.argv[2])
    elif command == "fail":
        if len(sys.argv) < 3:
            print(f"{EMOJI['error']} Task ID gerekli!")
            sys.exit(1)
        manager.fail_task(sys.argv[2])
    elif command == "block":
        if len(sys.argv) < 3:
            print(f"{EMOJI['error']} Task ID gerekli!")
            sys.exit(1)
        manager.block_task(sys.argv[2])
    elif command == "next":
        manager.next_task()
    else:
        print(f"{EMOJI['error']} Bilinmeyen komut: {command}")
        sys.exit(1)
if __name__ == "__main__":
    main()
