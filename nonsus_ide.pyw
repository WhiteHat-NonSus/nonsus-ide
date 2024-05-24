import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
from tkinter import ttk
import re

class NonsusIDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nonsus IDE 2024")
        self.geometry("1024x768")
        self.state('zoomed')  # Maximize the window

        self.current_directory = os.getcwd()
        self.current_file = None
        self.terminal_open = False  # Track terminal state

        self.configure(bg='white')  # Set window background color
        self.create_menu()
        self.create_panes()

        # Apply custom styles
        self.style = ttk.Style(self)
        self.style.theme_use("default")

        self.style.configure("FileExplorer.TFrame", background="white", borderwidth=0)
        self.style.configure("Flat.TButton", background="#f0f0f0", relief="flat")
        self.style.map("Flat.TButton", background=[("active", "#d9d9d9")])
        self.style.configure("TScrollbar", background="#f0f0f0", troughcolor="#d9d9d9", relief="flat")
        self.style.map("TScrollbar", background=[("active", "#d9d9d9")])

    def create_menu(self):
        menu_bar = tk.Menu(self)
        
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="打开文件夹", command=self.open_folder)
        file_menu.add_command(label="打开文件", command=self.open_file)
        file_menu.add_command(label="保存", command=self.save_file)
        file_menu.add_command(label="另存为", command=self.save_file_as)
        menu_bar.add_cascade(label="文件", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="撤回", command=lambda: self.focused_editor_event("<<Undo>>"))
        edit_menu.add_command(label="恢复", command=lambda: self.focused_editor_event("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="剪切", command=lambda: self.focused_editor_event("<<Cut>>"))
        edit_menu.add_command(label="复制", command=lambda: self.focused_editor_event("<<Copy>>"))
        edit_menu.add_command(label="粘贴", command=lambda: self.focused_editor_event("<<Paste>>"))
        menu_bar.add_cascade(label="编辑", menu=edit_menu)
        
        tool_menu = tk.Menu(menu_bar, tearoff=0)
        tool_menu.add_command(label="终端", command=self.toggle_terminal)
        menu_bar.add_cascade(label="工具", menu=tool_menu)
        
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)

        self.config(menu=menu_bar)

    def create_panes(self):
        self.panes = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.panes.pack(fill=tk.BOTH, expand=1)

        self.file_explorer_frame = ttk.Frame(self.panes, style="FileExplorer.TFrame")
        self.file_explorer_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        self.file_explorer = tk.Text(self.file_explorer_frame, bg='white', highlightthickness=0)
        self.file_explorer.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.file_explorer.bind("<Double-1>", self.on_file_explorer_double_click)
        self.file_explorer.bind("<Button-3>", self.show_file_explorer_menu)
        
        self.file_explorer_scrollbar = ttk.Scrollbar(self.file_explorer_frame, orient=tk.VERTICAL, style="TScrollbar")
        self.file_explorer_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_explorer.config(yscrollcommand=self.file_explorer_scrollbar.set)
        self.file_explorer_scrollbar.config(command=self.file_explorer.yview)
        
        self.editor_notebook = ttk.Notebook(self.panes)
        self.panes.add(self.file_explorer_frame)
        self.panes.add(self.editor_notebook)

        self.refresh_file_explorer()

    def open_file_as_tab(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        editor = ScrolledText(self.editor_notebook, font='TkDefaultFont')
        editor.insert(tk.END, content)
        editor.pack(fill=tk.BOTH, expand=1)
        self.editor_notebook.add(editor, text=os.path.basename(filepath))
        self.editor_notebook.select(editor)
        self.add_close_button(editor)
        self.apply_syntax_highlighting(editor)
        editor.bind("<<Modified>>", self.on_code_change)
        editor.bind("<Button-3>", self.show_code_editor_menu)

    def on_file_explorer_double_click(self, event):
        index = self.file_explorer.index("@%s,%s" % (event.x, event.y))
        line = self.file_explorer.get(f"{index} linestart", f"{index} lineend")
        selected_item = line.strip()
        if selected_item == "..":
            self.current_directory = os.path.dirname(self.current_directory)
            self.refresh_file_explorer()
        else:
            full_path = os.path.join(self.current_directory, selected_item)
            if os.path.isfile(full_path):
                self.open_file_as_tab(full_path)
            elif os.path.isdir(full_path):
                self.current_directory = full_path
                self.refresh_file_explorer()

    def close_current_tab(self):
        current_tab = self.editor_notebook.select()
        if current_tab:
            self.editor_notebook.forget(current_tab)

    def add_close_button(self, tab):
        close_button = tk.Button(tab, text="✕", command=lambda: self.close_current_tab())
        close_button.place(relx=0.95, rely=0.02, anchor=tk.NE)

    def create_close_button(self, event):
        tab_id = self.editor_notebook.index("@%d,%d" % (event.x, event.y))
        tab = self.editor_notebook.nametowidget(tab_id)
        self.add_close_button(tab)

    def bind_close_button(self):
        self.editor_notebook.bind("<Button-3>", self.create_close_button)

    def open_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        self.editor.delete(1.0, tk.END)
        self.editor.insert(tk.END, content)
        self.current_file = filepath

    def save_file(self):
        if self.current_file:
            content = self.editor.get(1.0, tk.END)
            with open(self.current_file, 'w', encoding='utf-8') as file:
                file.write(content)
        else:
            self.save_file_as()

    def save_file_as(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".py")
        if filepath:
            content = self.editor.get(1.0, tk.END)
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)
            self.current_file = filepath

    def open_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.current_directory = folder_path
            self.refresh_file_explorer()

    def toggle_terminal(self):
        if self.terminal_open:
            self.close_terminal()
        else:
            self.open_terminal()

    def open_terminal(self):
        self.terminal_frame = tk.Frame(self, height=150, bd=1, relief=tk.SUNKEN)
        self.terminal_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.terminal = ScrolledText(self.terminal_frame, height=8, bg="black", fg="white", font='TkDefaultFont')
        self.terminal.pack(fill=tk.BOTH, expand=1)
        self.terminal.bind("<Return>", self.execute_command)
        self.terminal.insert(tk.END, f"Terminal opened in {self.current_directory}\n")
        self.terminal_open = True

    def close_terminal(self):
        self.terminal_frame.pack_forget()
        del self.terminal
        self.terminal_open = False

    def execute_command(self, event):
        command = self.terminal.get("1.0", tk.END).strip()
        self.terminal.delete("1.0", tk.END)
        if command:
            def run_command():
                process = subprocess.Popen(command, shell=True, cwd=self.current_directory,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                stdout, stderr = process.communicate()
                self.terminal.insert(tk.END, stdout)
                self.terminal.insert(tk.END, stderr)
                self.terminal.see(tk.END)  # Scroll to the end of the text box
            threading.Thread(target=run_command).start()
        return "break"

    def show_file_explorer_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="新建文件", command=self.new_file)
        menu.add_command(label="新建文件夹", command=self.new_folder)
        menu.add_command(label="删除", command=self.delete_item)
        menu.add_command(label="重命名", command=self.rename_item)
        menu.post(event.x_root, event.y_root)

    def new_file(self):
        filename = simpledialog.askstring("新建文件", "请输入文件名：")
        if filename:
            open(os.path.join(self.current_directory, filename), 'w').close()
            self.refresh_file_explorer()

    def new_folder(self):
        foldername = simpledialog.askstring("新建文件夹", "请输入文件夹名：")
        if foldername:
            os.makedirs(os.path.join(self.current_directory, foldername), exist_ok=True)
            self.refresh_file_explorer()

    def delete_item(self):
        index = self.file_explorer.index(tk.ACTIVE)
        line = self.file_explorer.get(f"{index}.0", f"{index}.end")
        selected_item = line.strip()
        full_path = os.path.join(self.current_directory, selected_item)
        if os.path.isdir(full_path):
            os.rmdir(full_path)
        else:
            os.remove(full_path)
        self.refresh_file_explorer()

    def rename_item(self):
        index = self.file_explorer.index(tk.ACTIVE)
        line = self.file_explorer.get(f"{index}.0", f"{index}.end")
        selected_item = line.strip()
        full_path = os.path.join(self.current_directory, selected_item)
        new_name = simpledialog.askstring("重命名", "请输入新名称：")
        if new_name:
            os.rename(full_path, os.path.join(self.current_directory, new_name))
        self.refresh_file_explorer()

    def refresh_file_explorer(self):
        self.file_explorer.config(state=tk.NORMAL)
        self.file_explorer.delete(1.0, tk.END)
        if self.current_directory != os.path.abspath(os.sep):
            self.file_explorer.insert(tk.END, "..\n")
        for item in os.listdir(self.current_directory):
            item_path = os.path.join(self.current_directory, item)
            if os.path.isdir(item_path):
                self.file_explorer.insert(tk.END, item + "\n", "folder")
            elif os.access(item_path, os.X_OK):
                self.file_explorer.insert(tk.END, item + "\n", "executable")
            else:
                self.file_explorer.insert(tk.END, item + "\n")
        self.file_explorer.tag_configure("folder", foreground="purple")
        self.file_explorer.tag_configure("executable", foreground="green")
        self.file_explorer.config(state=tk.DISABLED)

    def show_about(self):
        messagebox.showinfo("关于", "Nonsus IDE 2024\n\n作者: Nonsus\n\n版权所有 © 2024 Nonsus")

    def apply_syntax_highlighting(self, editor):
        code = editor.get(1.0, tk.END)
        editor.tag_remove("keyword", "1.0", tk.END)
        editor.tag_remove("string", "1.0", tk.END)
        editor.tag_remove("comment", "1.0", tk.END)

        keyword_pattern = re.compile(r'\b(class|def|return|if|else|elif|for|while|try|except|import|from|as|with|lambda|yield|pass|continue|break|assert|nonlocal|global|True|False|None|and|or|not|is|in)\b')
        string_pattern = re.compile(r'(".*?"|\'.*?\')')
        comment_pattern = re.compile(r'(#.*?$)', re.MULTILINE)

        start = "1.0"
        while True:
            match = keyword_pattern.search(code)
            if not match:
                break
            start_index = f"{start}+{match.start()}c"
            end_index = f"{start}+{match.end()}c"
            editor.tag_add("keyword", start_index, end_index)
            code = code[match.end():]

        start = "1.0"
        while True:
            match = string_pattern.search(code)
            if not match:
                break
            start_index = f"{start}+{match.start()}c"
            end_index = f"{start}+{match.end()}c"
            editor.tag_add("string", start_index, end_index)
            code = code[match.end():]

        start = "1.0"
        while True:
            match = comment_pattern.search(code)
            if not match:
                break
            start_index = f"{start}+{match.start()}c"
            end_index = f"{start}+{match.end()}c"
            editor.tag_add("comment", start_index, end_index)
            code = code[match.end():]

        editor.tag_configure("keyword", foreground="blue")
        editor.tag_configure("string", foreground="orange")
        editor.tag_configure("comment", foreground="green")

    def on_code_change(self, event):
        editor = event.widget
        editor.edit_modified(False)
        self.apply_syntax_highlighting(editor)

    def focused_editor_event(self, sequence):
        focused_widget = self.focus_get()
        if isinstance(focused_widget, tk.Text) or isinstance(focused_widget, ScrolledText):
            focused_widget.event_generate(sequence)

    def show_code_editor_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="撤回", command=lambda: self.focused_editor_event("<<Undo>>"))
        menu.add_command(label="恢复", command=lambda: self.focused_editor_event("<<Redo>>"))
        menu.add_separator()
        menu.add_command(label="剪切", command=lambda: self.focused_editor_event("<<Cut>>"))
        menu.add_command(label="复制", command=lambda: self.focused_editor_event("<<Copy>>"))
        menu.add_command(label="粘贴", command=lambda: self.focused_editor_event("<<Paste>>"))
        menu.post(event.x_root, event.y_root)

if __name__ == "__main__":
    app = NonsusIDE()
    app.mainloop()
