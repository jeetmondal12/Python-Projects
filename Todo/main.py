import json

tasks = []

def add_task():
    task = input("Enter a new task: ")
    tasks.append({"task": task, "done": False})
    print("Task added!")

def view_tasks():
    if not tasks:
        print("No tasks yet.")
    for i, t in enumerate(tasks):
        status = "✅" if t["done"] else "❌"
        print(f"{i+1}. {t['task']} [{status}]")

def mark_done():
    view_tasks()
    try:
        index = int(input("Enter task number to mark done: ")) - 1
        tasks[index]["done"] = True
        print("Task marked as done!")
    except:
        print("Invalid input.")

def delete_task():
    view_tasks()
    try:
        index = int(input("Enter task number to delete: ")) - 1
        tasks.pop(index)
        print("Task deleted!")
    except:
        print("Invalid input.")

def save_tasks():
    with open("tasks.json", "w") as f:
        json.dump(tasks, f)
    print("Tasks saved. Goodbye!")

def load_tasks():
    global tasks
    try:
        with open("tasks.json", "r") as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

def calculator_ui():
    load_tasks()
    while True:
        print("\n=========================")
        print("| 1 | Add Task          |")
        print("| 2 | View Tasks        |")
        print("| 3 | Mark Task Done    |")
        print("| 4 | Delete Task       |")
        print("| 5 | Save & Exit       |")
        print("=========================")
        choice = input("Choose an option (1-5): ")

        if choice == "1":
            add_task()
        elif choice == "2":
            view_tasks()
        elif choice == "3":
            mark_done()
        elif choice == "4":
            delete_task()
        elif choice == "5":
            save_tasks()
            break
        else:
            print("Invalid input. Try again.")

calculator_ui()
    
