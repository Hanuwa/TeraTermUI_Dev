import asyncio
import customtkinter as ctk
import queue
import random
import threading
import tkinter as tk
import uuid
import websockets
import winsound
from CTkMessagebox import CTkMessagebox
from datetime import datetime
from tkinter import ttk


class ChatRoom(ctk.CTkToplevel):
    def __init__(self, master=None, lang=None, chat_button=None, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Chat")
        width = 525
        height = 325
        scaling_factor = self.tk.call("tk", "scaling")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width * scaling_factor) / 2
        y = (screen_height - height * scaling_factor) / 2
        self.geometry(f"{width}x{height}+{int(x + 150)}+{int(y + 20)}")
        self.after(256, lambda: self.iconbitmap("images/tera-term.ico"))

        self.translations = lang
        self.chat_room = chat_button

        self.chat_display = tk.Text(self)
        self.chat_display.configure(background="#d1d1d1", font=("Helvetica", 12), state=tk.DISABLED, wrap=tk.WORD,
                                    bd=0, highlightthickness=0, padx=10, pady=10, fg="#333333")
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=(20, 0), pady=20)

        # Create a frame for the entry and button
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", padx=20)

        self.msg_entry = ctk.CTkTextbox(self.bottom_frame, width=300, height=55, wrap="word")
        self.msg_entry.grid(row=0, column=0, sticky="nsew")

        self.send_btn = CustomButton(self.bottom_frame, text="Send", command=self.send_msg)
        self.send_btn.grid(row=0, column=1, sticky="nsew")
        self.exit_btn = CustomButton(self.bottom_frame, text="Exit", fg_color="#c30101", hover_color="darkred",
                                     command=self.disconnect_and_close)
        self.exit_btn.grid(row=1, column=0, columnspan=2, pady=(15, 0), sticky="nsew")
        self.user_count_label = tk.Label(self, text="Users connected: 0", bg="lightgray", font=("Helvetica", 10))
        self.user_count_label.grid(row=2, column=0, sticky="e", padx=(0, 75), pady=(15, 0))

        self.username = f"User{random.randint(1000, 9999)}"
        self.sent_message_ids = set()

        self.username_label = tk.Label(self, text=f"User: {self.username}", bg="lightgray", font=("Helvetica", 10))
        self.username_label.grid(row=2, column=0, sticky="w", padx=(100, 0), pady=(15, 0))

        style = ttk.Style()
        style.configure("TScrollbar", background="gray", troughcolor="white", gripcount=0,
                        darkcolor="gray", lightcolor="gray", bordercolor="gray")

        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, style="TScrollbar", command=self.chat_display.yview)
        self.chat_display["yscrollcommand"] = self.scrollbar.set
        self.scrollbar.grid(row=0, column=1, sticky="ns", pady=20)

        # Configure the grid columns and rows
        self.grid_rowconfigure(0, weight=1)  # chat_display should expand vertically
        self.grid_columnconfigure(0, weight=1)  # Both widgets should expand horizontally

        self.bottom_frame.grid_columnconfigure(0, weight=3)  # msg_entry should take up more space
        self.bottom_frame.grid_columnconfigure(1, weight=1)  # send_btn takes up less space

        self.connected = True
        self.after_id = None
        self.websocket = None

        self.message_queue = queue.Queue()
        self.after(100, self.check_for_messages)

        # Start websocket client in a new thread
        threading.Thread(target=self.start_websocket_client, daemon=True).start()

        self.msg_entry.bind("<Return>", self.send_msg)
        self.bind("<Escape>", self.disconnect_and_close)
        self.protocol("WM_DELETE_WINDOW", self.disconnect_and_close)
        self.chat_display.bind("<MouseWheel>", self.smooth_scroll)  # for Windows
        self.chat_display.bind("<Button-4>", self.smooth_scroll)  # for Linux scroll up
        self.chat_display.bind("<Button-5>", self.smooth_scroll)  # for Linux scroll down

    def change_language(self):
        self.send_btn.configure(text=self.translations["chat_send"])
        self.exit_btn.configure(text=self.translations["exit"])
        self.username_label.configure(text=self.translations["chat_user"] + self.username)

    def send_msg(self, event=None):
        # Generate a unique ID for the message
        msg_id = str(uuid.uuid4())

        # Add this ID to the set of sent message IDs
        self.sent_message_ids.add(msg_id)

        # Retrieve the message from the entry widget
        msg_content = self.msg_entry.get("1.0", tk.END).strip()
        word_count = len(msg_content.split())
        if not msg_content:
            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
            CTkMessagebox(title="Error", message=self.translations["chat_empty"], icon="cancel",
                          button_width=380)
            return
        if word_count >= 1000:
            winsound.PlaySound("sounds/error.wav", winsound.SND_ASYNC)
            CTkMessagebox(title="Error", message=self.translations["chat_max"], icon="cancel",
                          button_width=380)
            return

        # Construct the message with ID, username, and content
        msg = f"{msg_id}|{self.username}|{msg_content}"

        # Send the message via WebSocket
        asyncio.run(self.websocket.send(msg))

        # Add to local display
        self.append_msg(msg_content, self.username, msg_id)

        # Clear the message entry
        self.msg_entry.delete("1.0", tk.END)

    def check_for_messages(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                msg, user, message_id = self.message_queue.get_nowait()
                self.append_msg(msg, user, message_id)
        except queue.Empty:
            pass
        self.after_id = self.after(100, self.check_for_messages)

    def update_user_count_label(self, count):
        self.user_count_label.configure(text=self.translations["chat_count"] + count)

    def append_msg(self, message, user, message_id):
        self.chat_display.configure(state=tk.NORMAL)

        # Handle System messages
        if user == "System":
            self.chat_display.insert(tk.END, f"{message}\n", "system_msg")
            self.chat_display.tag_configure("system_msg", foreground="gray", justify="center")
            self.chat_display.configure(state=tk.DISABLED)
            return

        # Get current time and format it for timestamps
        current_time = datetime.now().strftime("%H:%M:%S")

        # Check if the message is from the current user or someone else
        if user == self.username:
            # Add the user's name and message, aligning to the right
            self.chat_display.insert(tk.END, f"{current_time} ", "right_time")
            self.chat_display.insert(tk.END, f"{user}: ", "right_name")
            self.chat_display.insert(tk.END, f"{message}\n\n", f"msg_{message_id}")
        else:
            # Add the other user's name and message, aligning to the left
            self.chat_display.insert(tk.END, f"{current_time} ", "left_time")
            self.chat_display.insert(tk.END, f"{user}: ", "left_name")
            self.chat_display.insert(tk.END, f"{message}\n\n", f"msg_{message_id}")

        # Configure tags
        self.chat_display.tag_configure("left_name", foreground="darkgreen", justify="left")
        self.chat_display.tag_configure("right_name", foreground="darkblue", justify="right")
        if user != self.username:
            self.chat_display.tag_configure(f"msg_{message_id}", foreground="black", justify="left")
        else:
            self.chat_display.tag_configure(f"msg_{message_id}", foreground="black", justify="right")
        self.chat_display.tag_configure("left_time", foreground="gray", justify="left")
        self.chat_display.tag_configure("right_time", foreground="gray", justify="right")
        self.chat_display.yview(tk.END)

        self.chat_display.configure(state=tk.DISABLED)

    def smooth_scroll(self, event):
        if event.delta:
            move = -1 * (event.delta / 120)
        else:
            if event.num == 5:
                move = 1
            else:
                move = -1
        self.chat_display.yview_scroll(int(move), "units")

    async def websocket_client(self):
        self.websocket = None
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            self.websocket = websocket

            # Notify all users that a new user has joined
            join_msg = f"|System|{self.username} has joined the chat."
            await websocket.send(join_msg)

            # Continuous loop to listen for messages
            while self.connected:
                message = await websocket.recv()
                parts = message.split("|")

                # Check for user count updates
                if len(parts) == 2 and parts[0] == "USERS_COUNT":
                    user_count = parts[1]
                    self.after(0, self.update_user_count_label, user_count)
                    continue  # Skip the rest and wait for the next message

                # Check for regular chat messages
                elif len(parts) == 3:
                    message_id, user, msg = parts

                    if message_id in self.sent_message_ids:
                        # This message was sent by this client, so ignore it
                        self.sent_message_ids.remove(message_id)  # Clean up the ID from the set
                    else:
                        # This message was sent by another client, so display it
                        self.message_queue.put((msg, user, message_id))

    def disconnect_and_close(self, event=None):
        msg = CTkMessagebox(master=self, title=self.translations["exit"],
                            message=self.translations["chat_exit"],
                            icon="images/submit.png",
                            option_1=self.translations["option_1"], option_2=self.translations["option_2"],
                            option_3=self.translations["option_3"],
                            icon_size=(65, 65), button_color=("#c30101", "#145DA0", "#145DA0"),
                            hover_color=("darkred", "darkblue", "darkblue"))
        response = msg.get()
        if response[0] == "Yes" or response[0] == "Sí":
            if self.after_id:
                self.after_cancel(self.after_id)
            asyncio.run(self._disconnect_from_server())
            asyncio.run(self.websocket.send("disconnecting"))
            self.destroy()

    async def _disconnect_from_server(self):
        if self.websocket and not self.websocket.closed:
            # Notify all users that the user has left using the existing WebSocket connection
            try:
                leave_msg = f"|System|{self.username} has left the chat."
                await self.websocket.send(leave_msg)
            except Exception:
                print("Failed to notify the server about the disconnection.")
        self.connected = False
        if hasattr(self, "chat_room") and self.chat_room is not None:
            self.chat_room.configure(state="normal")

    def start_websocket_client(self):
        asyncio.run(self.websocket_client())


class CustomButton(ctk.CTkButton):
    def __init__(self, master=None, command=None, **kwargs):
        super().__init__(master, cursor="hand2", **kwargs)
        self.is_pressed = False
        self.click_command = command
        self.bind("<ButtonPress-1>", self.on_button_down)
        self.bind("<ButtonRelease-1>", self.on_button_up)

    def on_button_down(self, event):
        if self.cget("state") == "disabled":
            return
        self.is_pressed = True

    def on_button_up(self, event):
        if self.cget("state") == "disabled":
            return
        width = self.winfo_width()
        height = self.winfo_height()
        if self.is_pressed and 0 <= event.x <= width and 0 <= event.y <= height:
            if self.click_command:
                self.click_command()
        self.is_pressed = False


if __name__ == "__main__":
    app = ChatRoom()
    app.mainloop()
