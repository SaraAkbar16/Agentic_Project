import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.edit_agent.state_manager import StateManager
from agents.edit_agent.agent import EditAgent

def list_projects():
    base_dir = Path("data/outputs/video/phase3")
    if not base_dir.exists():
        return []
    return [d.name for d in base_dir.iterdir() if d.is_dir()]

def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("\n" + "="*50)
    print("PHASE 5: INTELLIGENT EDIT & UNDO SYSTEM")
    print("="*50)
    
    projects = list_projects()
    if not projects:
        print("No projects found in data/outputs/video/phase3. Please run Phase 3 first.")
        return
        
    print("\nAvailable Projects:")
    for i, p in enumerate(projects):
        print(f"{i+1}. {p}")
        
    p_choice = input(f"\nSelect project [1-{len(projects)}]: ").strip()
    try:
        project_id = projects[int(p_choice)-1]
    except:
        print("Invalid selection.")
        return

    # Initialize manager for the specific project
    project_path = Path("data/outputs/video/phase3") / project_id
    manager = StateManager(data_dir=str(project_path))
    agent = EditAgent(manager)
    
    print(f"\nEditing Project: {project_id}")
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Describe an edit (e.g., 'Make the scene darker')")
        print("2. Undo last change")
        print("3. View version history")
        print("4. Exit")
        
        choice = input("\nChoice [1-4]: ").strip()
        
        if choice == "1":
            query = input("Describe your edit: ").strip()
            if query:
                result = agent.process_query(query, str(project_path))
                print(f"\nResult: {result['message']}")
        
        elif choice == "2":
            history = manager.get_history()
            if len(history) < 2:
                print("No previous versions to undo to.")
            else:
                # Revert to the second to last version (before the latest edit)
                prev_version = history[-2]["version"]
                if manager.revert(prev_version):
                    print(f"Successfully reverted to {prev_version}")
                else:
                    print("Failed to revert.")
                    
        elif choice == "3":
            history = manager.get_history()
            print("\nVersion History:")
            for entry in history:
                print(f"[{entry['version']}] {entry['timestamp']} - {entry['change_summary']}")
                
        elif choice == "4":
            print("Exiting Editor.")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
