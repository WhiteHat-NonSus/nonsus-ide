import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
from tkinter import ttk
import re

def set_dpi_awareness():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"Error setting DPI awareness: {e}")

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

        self.file_explorer = tk.Listbox(self.file_explorer_frame, bg='white', highlightthickness=0, selectbackground='lightgray', selectforeground='black')
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
        supported_extensions = ['.txt', '.py', '.java', '.cpp', '.c', '.html', '.css', '.js', '.vbs', '.bat', '.cmd', '.sh', '.php', '.pyw']  # 支持的文件类型列表
        file_extension = os.path.splitext(filepath)[1]
    
        if file_extension.lower() in supported_extensions:
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
        else:
            unsupported_file_message = "不受支持的文件类型"
            editor = tk.Text(self.editor_notebook)
            editor.insert(tk.END, unsupported_file_message)
            editor.pack(fill=tk.BOTH, expand=1)
            self.editor_notebook.add(editor, text=os.path.basename(filepath))
            self.editor_notebook.select(editor)
            self.add_close_button(editor)
    

    def on_file_explorer_double_click(self, event):
        index = self.file_explorer.curselection()
        if index:
            selected_item = self.file_explorer.get(index)
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
        close_button = tk.Button(tab, text="✕  关闭标签页", command=lambda: self.close_current_tab())
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
                self.terminal.see(tk.END)  # Scroll to the end

            threading.Thread(target=run_command).start()

    def show_file_explorer_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="新建文件", command=self.new_file)
        menu.add_command(label="新建文件夹", command=self.new_folder)
        menu.add_command(label="删除", command=self.delete_item)
        menu.add_command(label="重命名", command=self.rename_item)
        menu.post(event.x_root, event.y_root)

    def new_file(self):
        new_filename = simpledialog.askstring("新建文件", "输入文件名:")
        if new_filename:
            new_file_path = os.path.join(self.current_directory, new_filename)
            open(new_file_path, 'a').close()
            self.refresh_file_explorer()

    def new_folder(self):
        new_foldername = simpledialog.askstring("新建文件夹", "输入文件夹名:")
        if new_foldername:
            new_folder_path = os.path.join(self.current_directory, new_foldername)
            os.makedirs(new_folder_path, exist_ok=True)
            self.refresh_file_explorer()

    def delete_item(self):
        index = self.file_explorer.curselection()
        if index:
            selected_item = self.file_explorer.get(index).strip()
            full_path = os.path.join(self.current_directory, selected_item)
            if os.path.isdir(full_path):
                os.rmdir(full_path)
            elif os.path.isfile(full_path):
                os.remove(full_path)
            self.refresh_file_explorer()

    def rename_item(self):
        index = self.file_explorer.curselection()
        if index:
            selected_item = self.file_explorer.get(index).strip()
            new_name = simpledialog.askstring("重命名", "输入新的名称:", initialvalue=selected_item)
            if new_name:
                full_path = os.path.join(self.current_directory, selected_item)
                new_path = os.path.join(self.current_directory, new_name)
                os.rename(full_path, new_path)
                self.refresh_file_explorer()

    def refresh_file_explorer(self):
        self.file_explorer.delete(0, tk.END)
        if self.current_directory:
            self.file_explorer.insert(tk.END, "..")
            self.file_explorer.itemconfig(tk.END, {'fg': 'purple', 'selectbackground': '', 'selectforeground': ''})
            for item in os.listdir(self.current_directory):
                self.file_explorer.insert(tk.END, item)
                full_path = os.path.join(self.current_directory, item)
                if os.path.isdir(full_path):
                    self.file_explorer.itemconfig(tk.END, {'fg': 'purple', 'selectbackground': '', 'selectforeground': ''})
                elif full_path.endswith('.exe') or full_path.endswith('.sh'):
                    self.file_explorer.itemconfig(tk.END, {'fg': 'green', 'selectbackground': '', 'selectforeground': ''})


    def apply_syntax_highlighting(self, editor):
        content = editor.get(1.0, tk.END)
        self.highlight_pattern(editor, r'\b(class|def|return|if|else|elif|for|while|try|except|with|as|import|from|None|True|False)\b', 'keyword')
        self.highlight_pattern(editor, r'".*?"|\'.*?\'', 'string')
        self.highlight_pattern(editor, r'#.*', 'comment')

    def highlight_pattern(self, editor, pattern, tag):
        start = 1.0
        end = tk.END
        editor.mark_set("matchStart", start)
        editor.mark_set("matchEnd", start)
        editor.mark_set("searchLimit", end)

        count = tk.IntVar()
        while True:
            index = editor.search(pattern, "matchEnd", "searchLimit", count=count, regexp=True)
            if index == "": break
            editor.mark_set("matchStart", index)
            editor.mark_set("matchEnd", f"{index}+{count.get()}c")
            editor.tag_add(tag, "matchStart", "matchEnd")
            editor.tag_config('keyword', foreground='blue')
            editor.tag_config('string', foreground='green')
            editor.tag_config('comment', foreground='gray')

    def on_code_change(self, event):
        editor = event.widget
        editor.edit_modified(False)
        self.apply_syntax_highlighting(editor)

    def show_code_editor_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="撤回", command=lambda: self.focused_editor_event("<<Undo>>"))
        menu.add_command(label="恢复", command=lambda: self.focused_editor_event("<<Redo>>"))
        menu.add_separator()
        menu.add_command(label="剪切", command=lambda: self.focused_editor_event("<<Cut>>"))
        menu.add_command(label="复制", command=lambda: self.focused_editor_event("<<Copy>>"))
        menu.add_command(label="粘贴", command=lambda: self.focused_editor_event("<<Paste>>"))
        menu.post(event.x_root, event.y_root)

    def focused_editor_event(self, event):
        editor = self.editor_notebook.nametowidget(self.editor_notebook.select())
        if editor:
            editor.event_generate(event)

    def show_about(self):
        messagebox.showinfo("关于", "Nonsus IDE 2024\n版本 1.0\n作者: 你的名字")

def main():
    set_dpi_awareness()
    app = NonsusIDE()
    app.mainloop()

if __name__ == "__main__":
    main()
