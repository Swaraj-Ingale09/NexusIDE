import tkinter as tk
from tkinter import messagebox


def calculate_washing_time(load, dirt):
    if load <= 3 and dirt <= 3:
        return 20
    elif load <= 3 and dirt <= 7:
        return 35
    elif load <= 3 and dirt > 7:
        return 45
    elif load <= 7 and dirt <= 3:
        return 35
    elif load <= 7 and dirt <= 7:
        return 50
    elif load <= 7 and dirt > 7:
        return 65
    elif load > 7 and dirt <= 3:
        return 50
    elif load > 7 and dirt <= 7:
        return 70
    else:
        return 90


class AutoInputApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.show_load_dialog()

    def show_load_dialog(self):
        self.win1 = tk.Toplevel(self.root)
        self.win1.title("Input Required")
        self.win1.geometry("350x150")
        self.win1.attributes("-topmost", True)
        self.win1.lift()
        self.win1.focus_force()

        tk.Label(self.win1, text="Enter Load Size (kg):", font=("Arial", 12)).pack(pady=10)
        self.load_entry = tk.Entry(self.win1, font=("Arial", 12), width=20)
        self.load_entry.pack(pady=5)
        self.load_entry.focus()
        tk.Button(self.win1, text="Next", font=("Arial", 11), command=self.on_load_submit).pack(pady=10)
        self.win1.bind("<Return>", lambda e: self.on_load_submit())

    def on_load_submit(self):
        try:
            self.load = float(self.load_entry.get())
            self.win1.destroy()
            self.show_dirt_dialog()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number!")

    def show_dirt_dialog(self):
        self.win2 = tk.Toplevel(self.root)
        self.win2.title("Input Required")
        self.win2.geometry("350x150")
        self.win2.attributes("-topmost", True)
        self.win2.lift()
        self.win2.focus_force()

        tk.Label(self.win2, text="Enter Dirt Level (1-10):", font=("Arial", 12)).pack(pady=10)
        self.dirt_entry = tk.Entry(self.win2, font=("Arial", 12), width=20)
        self.dirt_entry.pack(pady=5)
        self.dirt_entry.focus()
        tk.Button(self.win2, text="Calculate", font=("Arial", 11), command=self.on_dirt_submit).pack(pady=10)
        self.win2.bind("<Return>", lambda e: self.on_dirt_submit())

    def on_dirt_submit(self):
        try:
            dirt = float(self.dirt_entry.get())
            if not (1 <= dirt <= 10):
                messagebox.showerror("Invalid Input", "Dirt Level must be between 1 and 10!")
                return
            self.win2.destroy()
            washing_time = calculate_washing_time(self.load, dirt)
            self.show_result(washing_time)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number!")

    def show_result(self, washing_time):
        win3 = tk.Toplevel(self.root)
        win3.title("Result")
        win3.geometry("400x150")
        win3.attributes("-topmost", True)
        win3.lift()
        win3.focus_force()

        tk.Label(win3, text="Recommended Washing Time", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(win3, text=f"{washing_time} minutes", font=("Arial", 20, "bold"), fg="green").pack(pady=5)
        tk.Button(win3, text="OK", font=("Arial", 11), command=lambda: (win3.destroy(), self.root.destroy())).pack(pady=10)
        win3.bind("<Return>", lambda e: (win3.destroy(), self.root.destroy()))


AutoInputApp().root.mainloop()
